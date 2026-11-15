"""固定版本 yt-dlp 的隔离 worker 与父进程 JSON 接口。

网络仅经过唯一 PublicOnlyUrllibRH；该 handler 故意不使用上游默认 opener，
因为 urllib 内部重定向不会重新进入 RH._send。下载分轨以独立文件返回，合并与
精裁由父工作层对本地文件执行。worker 禁止启动外部程序，包括 FFmpeg 回退。
"""
from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import asdict
import itertools
import json
import math
import os
from pathlib import Path
import re
import signal
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

from .errors import MaterialError
from .paths import no_links
from .network import NetworkBudget, SafeHTTP, public_ip, public_url, redact_text, validate_url

YTDLP_VERSION = "2026.10.26"
_MAX_MESSAGE = 16 * 1024 * 1024
_REQUEST_KEYS = {"schemaVersion", "mode", "url", "directory", "format_id", "cookies", "budget",
                 "max_items", "subtitles", "subtitle_languages", "provider", "query"}
_HOSTS = ("youtube.com", "youtu.be", "bilibili.com", "b23.tv", "douyin.com", "iesdouyin.com",
          "xiaohongshu.com", "xhslink.com", "weibo.com", "weibo.cn", "ixigua.com")
_FORMAT_PROTOCOLS = {"http", "https", "m3u8", "m3u8_native", "http_dash_segments"}


def _error(code, message, *, retryable=False):
    return MaterialError(code, message, stage="ytdlp", retryable=retryable)


def validate_request(value: dict) -> dict:
    if (not isinstance(value, dict) or set(value) - _REQUEST_KEYS
            or type(value.get("schemaVersion")) is not int or value["schemaVersion"] != 1):
        raise _error("invalid-request", "worker 仅接受 schemaVersion 1 白名单请求")
    result = dict(value)
    if value.get("mode") not in {"probe", "download", "search"}:
        raise _error("invalid-request", "worker mode 必须为 probe/download/search")
    if type(value.get("max_items", 10)) is not int or not 1 <= value.get("max_items", 10) <= 50:
        raise _error("invalid-request", "worker max_items 必须在 1..50")
    result["max_items"] = value.get("max_items", 10)
    budget = value.get("budget", {})
    if not isinstance(budget, dict) or set(budget) - set(NetworkBudget.__dataclass_fields__):
        raise _error("invalid-request", "worker 网络预算含未知字段")
    result["budget"] = asdict(NetworkBudget(**budget))
    if value["mode"] == "search":
        query = value.get("query")
        if value.get("provider") not in {"youtube", "bilibili"} or not isinstance(query, str) or not 0 < len(query.strip()) <= 256:
            raise _error("invalid-request", "search 需要 youtube/bilibili 和有界查询")
        if any(ord(x) < 32 for x in query) or "url" in value or "directory" in value:
            raise _error("invalid-request", "search 查询或参数无效")
    else:
        target = validate_url(value.get("url"))
        if not any(target.host == host or target.host.endswith("." + host) for host in _HOSTS):
            raise _error("unsupported-source", "worker 只处理已声明的平台入口；公开文件请使用受控 HTTP 获取")
        if "query" in value or "provider" in value:
            raise _error("invalid-request", "非 search 模式不能指定查询")
    format_id = value.get("format_id", "best")
    if not isinstance(format_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", format_id):
        raise _error("invalid-request", "format_id 只允许单个格式 ID 或 best/bestvideo/bestaudio")
    result["format_id"] = format_id
    if type(value.get("subtitles", False)) is not bool:
        raise _error("invalid-request", "subtitles 必须为布尔值")
    languages = value.get("subtitle_languages", ["zh-Hans", "zh-CN", "zh", "en"])
    if (not isinstance(languages, list) or len(languages) > 8
            or any(not isinstance(x, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,24}", x) for x in languages)):
        raise _error("invalid-request", "字幕语言必须是至多八项明确语言代码")
    result["subtitle_languages"] = languages
    if value["mode"] == "download":
        directory = value.get("directory")
        if not isinstance(directory, str) or not directory or not Path(directory).is_absolute():
            raise _error("invalid-request", "download 需要显式绝对暂存目录")
        _check_local_path(Path(directory))
    elif "directory" in value:
        raise _error("invalid-request", "仅 download 接受输出目录")
    if value.get("cookies") is not None:
        path = value["cookies"]
        if not isinstance(path, str) or not Path(path).is_absolute():
            raise _error("invalid-request", "cookies 仅接受显式绝对文件路径")
        _check_local_path(Path(path))
        if not Path(path).is_file() or Path(path).stat().st_size > 4 * 1024 * 1024:
            raise _error("invalid-request", "显式 cookie 文件不存在或超过限额")
    return result


def _check_local_path(path: Path):
    return no_links(path, stage='ytdlp')


class _QuietLogger:
    """提取器的异常可能含 cookie/签名 URL，绝不把原始文本写到 stdout/stderr。"""
    def __init__(self):
        self.messages = []

    def debug(self, message, **_):
        pass

    def warning(self, message, **_):
        if len(self.messages) < 20:
            # 仅按已知类别保留提示，而不是尝试证明任意原始日志都可安全发布。
            text = str(message).lower()
            if "javascript" in text or "runtime" in text or "challenge" in text:
                category = "外部 JS/挑战处理未启用，部分平台格式可能不可用"
            elif "cookie" in text or "login" in text or "sign in" in text:
                category = "平台可能需要显式会话文件"
            elif "format" in text:
                category = "平台部分格式不可用，请检查已返回格式和诊断"
            else:
                category = "平台提取产生受限提示；未回显可能包含凭据的原始内容"
            if category not in self.messages:
                self.messages.append(category)

    def error(self, message, **_):
        self.warning(message)

    stdout = debug


@contextmanager
def socket_guard():
    """仅用于隔离进程：解析全体结果验证 + 数值 connect/connect_ex 纵深防护。

    不是 OS 网络沙箱；原生 curl/浏览器/外部 JS 不受此 Python 层可靠约束，
    所以真正 worker 还以审计钩子禁止所有外部进程，并且不注册这些网络后端。
    """
    original_resolve = socket.getaddrinfo
    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
    approved = set()

    def resolve(host, port, *args, **kwargs):
        if port not in {80, 443, "80", "443", "http", "https"}:
            raise _error("security-blocked", "worker 拒绝非 HTTP(S) 端口")
        entries = original_resolve(host, port, *args, **kwargs)
        checked = []
        for family, kind, proto, name, address in entries:
            if family not in {socket.AF_INET, socket.AF_INET6}:
                raise _error("security-blocked", "worker DNS 地址族不受支持")
            ip = public_ip(address[0])
            if address[1] not in {80, 443} or (family == socket.AF_INET6 and len(address) > 3 and address[3]):
                raise _error("security-blocked", "worker DNS 端口或 scope 不受支持")
            checked.append((ip, address[1]))
        approved.update(checked)
        return entries

    def check(sock, address):
        if sock.family not in {socket.AF_INET, socket.AF_INET6} or not isinstance(address, tuple) or len(address) < 2:
            raise _error("security-blocked", "worker 拒绝非公开网络连接")
        ip = public_ip(address[0])  # 主机名在此必然失败，杜绝 C 层二次解析。
        if (ip, address[1]) not in approved:
            raise _error("security-blocked", "worker 连接地址未绑定已校验 DNS 结果")

    def connect(sock, address):
        check(sock, address)
        return original_connect(sock, address)

    def connect_ex(sock, address):
        check(sock, address)
        return original_connect_ex(sock, address)

    with patch.object(socket, "getaddrinfo", resolve), patch.object(socket.socket, "connect", connect), patch.object(socket.socket, "connect_ex", connect_ex):
        yield


def _install_process_guard():
    def audit(event, args):
        if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.fork', 'os.spawn',
                     'os.exec', 'os.startfile', 'os.startfile/2'}:
            raise _error("security-blocked", "worker 禁止外部下载器、JS、shell 和 FFmpeg 子进程")
    sys.addaudithook(audit)


def build_ytdlp(http: SafeHTTP, request: dict):
    """返回单一请求后端的 YoutubeDL 实例；不装饰/注册任何全局新 RH。"""
    import yt_dlp
    from yt_dlp.globals import plugin_dirs
    from yt_dlp.networking._urllib import UrllibRH
    from yt_dlp.networking.common import RequestDirector, Response
    from yt_dlp.networking.exceptions import HTTPError, RequestError
    from yt_dlp.downloader.external import FFmpegFD
    from yt_dlp.version import __version__

    if __version__ != YTDLP_VERSION:
        raise _error("dependency-missing", f"受控 worker 要求 yt-dlp {YTDLP_VERSION}，请按项目锁定依赖恢复")
    plugin_dirs.value = []
    logger = _QuietLogger()

    class PolicyRequestError(RequestError):
        def __init__(self, cause):
            self.material_error = cause
            super().__init__("素材请求被受控传输拒绝")

    class PublicOnlyUrllibRH(UrllibRH):
        _SUPPORTED_URL_SCHEMES = ("http", "https")
        _SUPPORTED_PROXY_SCHEMES = ()
        _SUPPORTED_FEATURES = ()

        def _validate(self, req):
            # 不调用上游代理检查，否则未知代理可能被当成Unsupported并尝试后端兜底。
            if req.proxies or set(req.extensions) - {"cookiejar", "timeout"}:
                raise PolicyRequestError(_error("security-blocked", "不允许请求级代理或额外网络扩展"))
            try:
                validate_url(req.url)
            except MaterialError as exc:
                raise PolicyRequestError(exc) from None

        def _send(self, req):
            try:
                headers = dict(self.headers)
                headers.update(dict(req.headers))
                raw = http.open(req.url, method=req.method, headers=headers, data=req.data,
                                cookiejar=self._get_cookiejar(req),
                                timeout_s=req.extensions.get("timeout"), allow_http_errors=True)
                response = Response(fp=raw, headers=raw.headers, url=raw.url,
                                    status=raw.status, reason=raw.reason)
                if not 200 <= raw.status < 300:
                    raise HTTPError(response)
                return response
            except MaterialError as exc:
                raise PolicyRequestError(exc) from None

    class PublicOnlyYoutubeDL(yt_dlp.YoutubeDL):
        def build_request_director(self, handlers=None, preferences=None):
            director = RequestDirector(logger=logger)
            director.add_handler(PublicOnlyUrllibRH(logger=logger, headers=self.params["http_headers"],
                                                  cookiejar=self.cookiejar, proxies={},
                                                  timeout=http.budget.timeout_s))
            return director

        def process_info(self, info):
            _check_media(info, http.budget)
            return super().process_info(info)

        def dl(self, name, info, **kwargs):
            _check_media(info, http.budget)
            protocol = info.get("protocol") or ("https" if str(info.get("url", "")).startswith("https:") else "http")
            if protocol not in _FORMAT_PROTOCOLS or info.get("section_start") is not None or info.get("section_end") is not None:
                raise _error("security-blocked", "只允许受控 native 文件/HLS/DASH；远程区间请完整获取后本地精裁")
            return super().dl(name, info, **kwargs)

        def save_cookies(self):
            # 显式会话文件仅作为输入，不把刷新后的敏感会话写回用户文件。
            pass

        def run_pp(self, pp, info):
            # MoveFilesAfterDownloadPP 只在明确暂存根内移动已下载文件，无进程执行。
            if pp.__class__.__name__ != "MoveFilesAfterDownloadPP":
                raise _error("security-blocked", "worker 不执行媒体后处理，分轨合并及精裁请在父层本地完成")
            return super().run_pp(pp, info)

    def deny_ffmpeg(*args, **kwargs):
        raise _error("security-blocked", "拒绝联网 FFmpeg 回退；请完整 native 获取或改用本地文件")

    # 在独立 worker 中保持到退出；即使 HLS 内部直接构造 FFmpegFD 也不能联网。
    FFmpegFD.real_download = deny_ffmpeg
    def progress(state):
        downloaded = state.get('downloaded_bytes')
        if type(downloaded) in {int, float} and downloaded > http.budget.max_bytes:
            raise _error('resource-limit', '平台单个输出超过字节预算，停止分片追加')
        http.check()

    options = {
        'progress_hooks': [progress],
        "quiet": True, "no_warnings": True, "noprogress": True, "logger": logger,
        "proxy": "", "geo_verification_proxy": "", "js_runtimes": {}, "remote_components": [],
        "cachedir": False, "usenetrc": False, "netrc_location": None, "cookiesfrombrowser": None,
        "enable_file_urls": False, "legacyserverconnect": False, "nocheckcertificate": False,
        "external_downloader": "native", "hls_prefer_native": True, "hls_use_mpegts": True,
        "concurrent_fragment_downloads": 1, "skip_unavailable_fragments": False,
        "retries": 0, "fragment_retries": 0, "extractor_retries": 0, "file_access_retries": 0,
        "socket_timeout": http.budget.timeout_s, "max_filesize": http.budget.max_bytes,
        "noplaylist": request["mode"] != "search", "playlistend": request["max_items"],
        "lazy_playlist": True, "extract_flat": "in_playlist" if request["mode"] == "search" else False,
        "format": request["format_id"], "fixup": "never", "postprocessors": [], "exec_cmd": None,
        "writeinfojson": False, "writethumbnail": False, "overwrites": False,
        "continuedl": False, "nopart": False, "keep_fragments": False,
        "writesubtitles": request.get("subtitles", False),
        "writeautomaticsub": request.get("subtitles", False),
        "subtitleslangs": request["subtitle_languages"], "subtitlesformat": "vtt/srt/best",
        "restrictfilenames": True, "windowsfilenames": True,
        "allowed_extractors": [r"(?i)(?:youtube.*|bilibili.*|bili.*|douyin.*|xiaohongshu.*|weibo.*|xi(?:gua|Gua).*|generic)$"],
    }
    if request.get("cookies"):
        options["cookiefile"] = request["cookies"]
    if request["mode"] == "download":
        options.update(paths={"home": request["directory"], "temp": request["directory"]},
                       outtmpl={"default": "media-%(autonumber)06d.%(ext)s"})
    result = PublicOnlyYoutubeDL(options)
    result.material_logger = logger
    return result


def _check_download_resources(directory: Path, budget: NetworkBudget):
    _check_local_path(directory)
    if shutil.disk_usage(directory).free < budget.min_free_bytes:
        raise _error('resource-limit', '磁盘剩余空间不足，停止平台获取')
    total, count = 0, 0
    for entry in directory.iterdir():
        count += 1
        if count > budget.max_requests + 32:
            raise _error('resource-limit', '平台暂存文件数量超过预算')
        _check_local_path(entry)
        info = entry.lstat()
        if not entry.is_file() or info.st_nlink != 1:
            raise _error('security-blocked', '平台暂存只能包含独立普通文件')
        total += info.st_size
        if info.st_size > budget.max_bytes or total > budget.total_bytes:
            raise _error('resource-limit', '平台暂存字节超过预算')


def _check_media(info, budget):
    if info.get("is_live") or info.get("live_status") in {"is_live", "is_upcoming", "post_live"}:
        raise _error("unsupported-source", "直播和尚未完成的直播不在自动获取范围")
    if info.get("has_drm"):
        raise _error("unsupported-source", "DRM 媒体不在自动获取范围")
    if info.get("requested_formats"):
        raise _error("invalid-request", "worker 每次只取一个格式，分轨请分别获取后在父层本地合并")
    if info.get("section_start") is not None or info.get("section_end") is not None:
        raise _error("security-blocked", "worker 不执行远程区间下载")
    fragments = info.get("fragments")
    if fragments is not None and (not isinstance(fragments, list) or len(fragments) > budget.max_requests):
        raise _error("resource-limit", "分片数量超过本次请求预算")


def _number(value):
    return value if type(value) in {int, float} and math.isfinite(value) else None


def _metadata(info: dict) -> dict:
    result = {}
    for key in ("id", "title", "description", "uploader", "uploader_id", "channel", "upload_date", "timestamp",
                "duration", "width", "height", "fps", "ext", "extractor", "extractor_key", "live_status"):
        value = info.get(key)
        if isinstance(value, str):
            result[key] = redact_text(value)[:20000 if key == "description" else 500]
        elif type(value) in {int, float} and math.isfinite(value):
            result[key] = value
    locator = info.get('webpage_url')
    if not locator and info.get('_type') in {'url', 'url_transparent'}:
        # flat 搜索条目的 url 是来源页，不是 formats 中的临时媒体地址；只保留已知页形状。
        candidate = str(info.get('url', ''))
        try:
            target = validate_url(candidate)
            if (((target.host == 'bilibili.com' or target.host.endswith('.bilibili.com')) and re.match(r'^/video/(?:BV[0-9A-Za-z]+|av[0-9]+)', target.path))
                    or (target.host in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'}
                        and re.match(r'^/(?:watch\?|shorts/|[A-Za-z0-9_-]{11}(?:$|\?))', target.path))):
                locator = target.url
        except MaterialError:
            pass
    if isinstance(locator, str) and locator.startswith(('https://', 'http://')):
        result['sourceUrl'] = public_url(locator)
    result["has_drm"] = bool(info.get("has_drm"))
    formats = []
    for fmt in itertools.islice(info.get("formats") or [], 512):
        formats.append({key: (redact_text(fmt[key])[:200] if isinstance(fmt[key], str) else _number(fmt[key]))
                        for key in ("format_id", "ext", "width", "height", "fps", "tbr", "filesize", "filesize_approx", "protocol", "acodec", "vcodec", "language")
                        if fmt.get(key) is not None})
    result["formats"] = formats
    result["chapters"] = [{"startSeconds": _number(c.get("start_time")), "endSeconds": _number(c.get("end_time")),
                           "title": redact_text(c.get("title", ""))[:500]}
                          for c in itertools.islice(info.get("chapters") or [], 512)]
    result["subtitles"] = {"manual": list(itertools.islice((info.get("subtitles") or {}).keys(), 64)),
                           "automatic": list(itertools.islice((info.get("automatic_captions") or {}).keys(), 64))}
    return result


def _classify(exc: BaseException) -> MaterialError:
    if isinstance(exc, MaterialError):
        return exc
    # 提取器常把 RequestError 包装多次；优先保留原受控错误，且不回显异常正文。
    seen, current = set(), exc
    for _ in range(12):
        if id(current) in seen:
            break
        seen.add(id(current))
        if isinstance(getattr(current, "material_error", None), MaterialError):
            return current.material_error
        if isinstance(getattr(current, "cause", None), MaterialError):
            return current.cause
        current = getattr(current, "cause", None) or getattr(current, "__cause__", None) or getattr(current, "__context__", None)
        if current is None:
            break
    text = str(exc).lower()
    if "429" in text or "too many requests" in text:
        return _error("rate-limited", "平台限流，请稍后重试", retryable=True)
    if "captcha" in text or "challenge" in text or "javascript" in text:
        return _error("challenge-required", "平台需要未启用的挑战处理；可使用显式本地媒体")
    if "cookie" in text or "login" in text or "sign in" in text or "log in" in text:
        return _error("session-required", "平台要求会话；请显式提供专用 cookie 文件或改用本地媒体")
    if "403" in text:
        return _error("access-denied", "平台拒绝当前获取路径，请换公开来源或本地文件")
    if "404" in text or "not found" in text:
        return _error("not-found", "平台条目不存在或已移除")
    if "timed out" in text or "timeout" in text:
        return _error("network-timeout", "平台请求超时", retryable=True)
    return _error("unsupported-source", "平台未返回可用媒体；请检查 doctor 或改用公开直链/本地文件")


def execute(request: dict) -> dict:
    """worker 内部入口；父层使用 run_ytdlp，不在主进程安装全局 socket 守卫。"""
    request = validate_request(request)
    directory = Path(request["directory"]) if request["mode"] == "download" else None
    if directory:
        directory.mkdir(parents=True, exist_ok=True)
        if next(directory.iterdir(), None) is not None:
            raise _error("conflict", "worker 下载暂存目录必须为空，避免覆盖或复用未验证文件")
    budget = NetworkBudget(**request['budget'])
    if directory:
        _check_download_resources(directory, budget)
    http = SafeHTTP(budget, resource_check=(lambda: _check_download_resources(directory, budget)) if directory else None)
    locator = request.get("url")
    if request["mode"] == "search":
        prefix = "ytsearch" if request["provider"] == "youtube" else "bilisearch"
        locator = f"{prefix}{request['max_items']}:{request['query']}"
    before_env = {name: value for name, value in os.environ.items() if name.lower().endswith("_proxy")}
    for name in before_env:
        os.environ.pop(name, None)
    os.environ["YTDLP_NO_PLUGINS"] = "1"
    try:
        with socket_guard(), build_ytdlp(http, request) as ydl:
            info = ydl.extract_info(locator, download=request["mode"] == "download")
            if not isinstance(info, dict):
                raise _error("not-found", "平台没有返回条目")
            if request["mode"] != "search":
                _check_media(info, http.budget)
            entries = []
            if info.get("entries") is not None:
                for entry in itertools.islice(info["entries"], request["max_items"]):
                    if isinstance(entry, dict):
                        entries.append(_metadata(entry))
            files = []
            if directory:
                _check_download_resources(directory, budget)
                total = 0
                for path in directory.iterdir():
                    _check_local_path(path)
                    if not path.is_file() or path.suffix in {".part", ".ytdl", ".temp"}:
                        raise _error("media-invalid", "平台下载未完成，保留暂存以供诊断，不发布素材")
                    total += path.stat().st_size
                    if total > http.budget.total_bytes:
                        raise _error("resource-limit", "平台下载文件合计超过预算")
                    files.append({"path": path.name, "bytes": path.stat().st_size,
                                  "kind": "subtitle" if path.suffix.lower() in {".srt", ".vtt", ".ass", ".ttml", ".json3"} else "media"})
                if not any(item["kind"] == "media" and item["bytes"] > 0 for item in files):
                    raise _error("media-invalid", "平台未生成非空媒体文件")
            return {"mode": request["mode"], "metadata": _metadata(info), "entries": entries,
                    "files": files, "warnings": ydl.material_logger.messages, "stats": http.stats,
                    "toolchain": {"yt-dlp": YTDLP_VERSION, "networkPolicy": "public-only-v1", "externalProcesses": False}}
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise _classify(exc) from None
    finally:
        os.environ.update(before_env)


def _kill_tree(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait()


def run_ytdlp(request: dict, *, timeout_s: float = 330.0, cancelled=None) -> dict:
    """通过标准输入/输出文件传递单个 JSON 消息，不把凭据写到命令行或日志。

    返回 execute 的白名单 data；失败统一抛 MaterialError。download 的 files.path
    相对请求 directory，父层须先探测、校验摘要并发布；没有持久化签名媒体 URL。
    """
    validated = validate_request(request)
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or timeout_s <= 0:
        raise _error("invalid-request", "worker 时限必须为正有限数")
    payload = json.dumps(validated, ensure_ascii=False).encode("utf-8")
    if len(payload) > _MAX_MESSAGE:
        raise _error("invalid-request", "worker 请求过大")
    environment = os.environ.copy()
    environment["YTDLP_NO_PLUGINS"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    for key in tuple(environment):
        if key.lower().endswith("_proxy"):
            environment.pop(key, None)
    # 普通文件而非 PIPE：兼容 Windows 受限环境，也避免未消费 stderr 管道死锁。
    with tempfile.TemporaryFile() as input_file, tempfile.TemporaryFile() as output_file, tempfile.TemporaryFile() as error_file:
        input_file.write(payload)
        input_file.seek(0)
        creation = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        process = subprocess.Popen([sys.executable, "-m", "m2v.materials.ytdlp_worker"],
                                   stdin=input_file, stdout=output_file, stderr=error_file,
                                   env=environment, **creation)
        started = time.monotonic()
        try:
            while True:
                if cancelled and cancelled():
                    raise _error("cancelled", "平台获取已取消")
                remaining = timeout_s - (time.monotonic() - started)
                if remaining <= 0:
                    raise _error("network-timeout", "平台 worker 超过总时限", retryable=True)
                try:
                    process.wait(timeout=min(0.2, remaining))
                    break
                except subprocess.TimeoutExpired:
                    pass
        except BaseException:
            _kill_tree(process)
            raise
        output_file.seek(0)
        output = output_file.read(_MAX_MESSAGE + 1)
        if len(output) > _MAX_MESSAGE:
            raise _error("resource-limit", "worker 响应超过上限")
        try:
            envelope = json.loads(output)
            if not isinstance(envelope, dict) or envelope.get("schemaVersion") != 1 or type(envelope.get("ok")) is not bool:
                raise ValueError("envelope")
            if not envelope["ok"]:
                error = envelope["error"]
                raise MaterialError(error["code"], error["message"], stage="ytdlp", retryable=bool(error.get("retryable")))
            if process.returncode != 0 or not isinstance(envelope.get("data"), dict):
                raise ValueError("return code")
            return envelope["data"]
        except (ValueError, KeyError, TypeError):
            raise _error("media-invalid", "worker 未返回有效的白名单 JSON 响应") from None


def main() -> int:
    try:
        payload = sys.stdin.buffer.read(_MAX_MESSAGE + 1)
        if len(payload) > _MAX_MESSAGE:
            raise _error("invalid-request", "worker 请求超过上限")
        request = json.loads(payload)
        # 在导入提取器前阻止插件；审计守卫比仅 monkeypatch Popen 更能防缓存别名旁路。
        os.environ["YTDLP_NO_PLUGINS"] = "1"
        _install_process_guard()
        with open(os.devnull, "w", encoding="utf-8") as sink, redirect_stdout(sink), redirect_stderr(sink):
            result = execute(request)
        envelope, code = {"schemaVersion": 1, "ok": True, "data": result}, 0
    except BaseException as exc:
        error = _classify(exc)
        envelope = {"schemaVersion": 1, "ok": False,
                    "error": {"code": error.code, "message": str(error), "retryable": error.retryable}}
        code = 2
    encoded = json.dumps(envelope, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(encoded) > _MAX_MESSAGE:
        code = 2
        encoded = json.dumps({'schemaVersion': 1, 'ok': False, 'error': {
            'code': 'resource-limit', 'message': 'worker 响应超过上限', 'retryable': False}},
            ensure_ascii=False).encode('utf-8')
    sys.stdout.buffer.write(encoded)  # 不依赖 Windows 控制台/管道的默认 GBK 编码。
    return code


if __name__ == "__main__":
    raise SystemExit(main())
