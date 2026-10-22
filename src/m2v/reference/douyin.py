"""抖音参考素材：浏览器取详情、直链下载、写来源与摘要留证。

不实现 ``a_bogus`` 等签名参数：页面自己完成签名与请求，这里只读取页面已经取得的
详情。图文页不请求详情接口，因此保留从页面内嵌 RSC 载荷解析的兜底路径。

参考素材落在 ``refs/douyin/<awemeId>/``：媒体默认用于制作前分析，不进入成片，也不进入
版本控制。目录里的 ``recipe.json`` 是唯一留证来源，``ref verify`` 按它复核。用户明确
要求复用单条参考音频时，由 ``m2v.reference.audio`` 提取到作品目录并留证，渲染链路仍
不直接读取 ``refs/``。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from m2v.core.errors import M2VError
from m2v.core.workspace import bundle_repo_root, content_root
from m2v.engine.media_probe import probe_dimensions

DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
REFERER = "https://www.douyin.com/"
DETAIL_PATH = "/aweme/v1/web/aweme/detail/"
DOUYIN_HOSTS = ("douyin.com", "iesdouyin.com")
SHARE_URL = re.compile(r"https?://[^\s<>\"'，。！？、）)]+")
AWEME_PATH = re.compile(r"/(?:share/)?(?:video|note)/(\d{5,})")
_PACE_PUSH = re.compile(r"self\.__pace_f\.push\((\[.*?\])\)\s*</script>", re.S)
_RSC_PREFIX = re.compile(r"^\d+:")
_IMAGE_SUFFIXES = {".webp", ".jpg", ".jpeg", ".png", ".gif", ".avif"}


@dataclass(frozen=True)
class FetchResult:
    """一次引用的结果：目录、规范化元数据、是否复用、逐文件摘要。"""

    directory: Path
    item: dict
    reused: bool
    files: list[dict]


def workspace_root() -> Path:
    """参考素材默认所在的根：内容根优先，其次是仓库根，最后是当前目录。"""
    return content_root() or bundle_repo_root() or Path.cwd()


def reference_root(explicit: str | Path | None = None) -> Path:
    """``--output`` 指定参考素材根目录；省略时是 ``<工作区>/refs/douyin``。"""
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    return workspace_root() / "refs" / "douyin"


def profile_dir() -> Path:
    """浏览器 profile 可能含登录 cookie，放在被忽略的缓存目录里。"""
    return workspace_root() / ".cache" / "douyin-profile"


def extract_share_url(text: str) -> str:
    """从分享文本中取出第一个抖音链接，忽略前后的说明文字与日期。"""
    for match in SHARE_URL.finditer(text.strip()):
        candidate = match.group(0).rstrip(".,;:!?)]}'\"")
        host = (urllib.parse.urlsplit(candidate).hostname or "").lower()
        if any(host == item or host.endswith("." + item) for item in DOUYIN_HOSTS):
            return candidate
    raise M2VError(
        "没有找到抖音分享链接；请粘贴形如 https://v.douyin.com/xxxx/ 的分享文本"
    )


def aweme_id_from_url(url: str) -> str | None:
    """从视频页/图文页 URL 取作品 ID；短链没有 ID，返回 ``None``。"""
    match = AWEME_PATH.search(urllib.parse.urlsplit(url).path)
    return match.group(1) if match else None


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _urls(value) -> list[str]:
    if not isinstance(value, dict):
        return []
    items = value.get("url_list") or value.get("urlList") or []
    return [item for item in items if isinstance(item, str) and item]


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def video_urls(video: dict) -> list[str]:
    """按 h264 码率从高到低排列直链，再补默认与 h265 兜底。"""
    ranked: list[tuple[int, list[str]]] = []
    for entry in video.get("bit_rate") or video.get("bitRateList") or []:
        if not isinstance(entry, dict) or entry.get("is_h265") or entry.get("isH265"):
            continue
        urls = _urls(entry.get("play_addr") or entry.get("playAddr"))
        if urls:
            ranked.append((_int(entry.get("bit_rate") or entry.get("bitRate")), urls))
    ranked.sort(key=lambda item: item[0], reverse=True)
    ordered = [url for _, urls in ranked for url in urls]
    for key in (
        "play_addr_h264", "playAddrH264", "play_addr", "playAddr",
        "play_addr_265", "playAddrH265",
    ):
        ordered.extend(_urls(video.get(key)))
    return _dedupe(ordered)


def image_entries(images) -> list[dict]:
    """图文图片：``url_list`` 是无水印地址，``download_url_list`` 带水印，只作兜底。"""
    entries: list[dict] = []
    for item in images or []:
        if not isinstance(item, dict):
            continue
        urls = _dedupe(
            _urls({"urlList": item.get("url_list") or item.get("urlList")})
            + _urls({"urlList": item.get("download_url_list") or item.get("downloadUrlList")})
        )
        if not urls:
            continue
        entries.append({
            "urls": urls,
            "width": _int(item.get("width")),
            "height": _int(item.get("height")),
            "uri": item.get("uri") or "",
        })
    return entries


def normalize_detail(
    detail: dict,
    *,
    aweme_id: str | None = None,
    source_url: str = "",
    final_url: str = "",
) -> dict:
    """把详情接口（snake_case）与页面 RSC（camelCase）统一成一份元数据。"""
    video = detail.get("video") or {}
    images = image_entries(detail.get("images"))
    author = detail.get("author") or detail.get("authorInfo") or {}
    cover_urls = _dedupe(
        _urls(video.get("cover"))
        + _urls({"urlList": video.get("coverUrlList")})
        + _urls({"urlList": video.get("originCoverUrlList")})
    )
    return {
        "schemaVersion": 1,
        "awemeId": str(detail.get("aweme_id") or detail.get("awemeId") or aweme_id or ""),
        "kind": "note" if images else "video",
        "desc": detail.get("desc") or "",
        "author": {
            "uid": str(author.get("uid") or ""),
            "secUid": author.get("sec_uid") or author.get("secUid") or "",
            "nickname": author.get("nickname") or "",
        },
        "createTime": _int(detail.get("create_time") or detail.get("createTime")),
        "durationMs": _int(video.get("duration")),
        "declaredWidth": _int(video.get("width")),
        "declaredHeight": _int(video.get("height")),
        "coverUrl": cover_urls[0] if cover_urls else "",
        "videoUrls": video_urls(video),
        "images": images,
        "sourceUrl": source_url,
        "finalUrl": final_url,
    }


def _walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def pace_texts(html: str):
    """逐个产出 ``self.__pace_f.push([...])`` 里的字符串载荷。"""
    for match in _PACE_PUSH.finditer(html):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(value, list) and len(value) > 1 and isinstance(value[1], str):
            yield value[1]


def detail_from_html(html: str, aweme_id: str | None = None) -> dict | None:
    """从页面内嵌 RSC 载荷里找作品详情；图文页没有详情接口，靠这条路径。"""
    for text in pace_texts(html):
        try:
            data = json.loads(_RSC_PREFIX.sub("", text, count=1))
        except json.JSONDecodeError:
            continue
        for node in _walk(data):
            aweme = node.get("aweme")
            detail = aweme.get("detail") if isinstance(aweme, dict) else None
            if not isinstance(detail, dict) and isinstance(node.get("detail"), dict):
                detail = node["detail"]
            if not isinstance(detail, dict):
                continue
            found_id = str(detail.get("awemeId") or detail.get("aweme_id") or "")
            if aweme_id and found_id and found_id != aweme_id:
                continue
            if detail.get("images") or detail.get("video") or detail.get("desc"):
                return detail
    return None


def _detail_from_bodies(bodies: list[str], aweme_id: str | None) -> dict | None:
    for body in bodies:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            continue
        detail = payload.get("aweme_detail") if isinstance(payload, dict) else None
        if not isinstance(detail, dict):
            continue
        found_id = str(detail.get("aweme_id") or "")
        if aweme_id and found_id and found_id != aweme_id:
            continue
        if detail.get("video") or detail.get("images") or detail.get("desc"):
            return detail
    return None


def _read_page(url: str, *, headed: bool, timeout_s: float) -> tuple[list[str], str, str, str]:
    """打开页面，收集详情接口响应与最终 HTML；返回诊断需要的信息。"""
    from playwright.sync_api import sync_playwright

    profile = profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    bodies: list[str] = []
    with sync_playwright() as playwright:
        try:
            context = playwright.chromium.launch_persistent_context(
                str(profile),
                headless=not headed,
                user_agent=DESKTOP_UA,
                locale="zh-CN",
                viewport={"width": 1440, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception as exc:  # noqa: BLE001 - 浏览器启动失败统一转成可读错误
            raise M2VError(f"无法启动浏览器（profile：{profile}）：{exc}") from exc
        try:
            page = context.pages[0] if context.pages else context.new_page()

            def remember(response):
                if DETAIL_PATH not in response.url:
                    return
                try:
                    body = response.text()
                except Exception:  # noqa: BLE001 - 导航打断读取时不值得中断整体流程
                    return
                if body:
                    bodies.append(body)

            page.on("response", remember)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=int(timeout_s * 1000))
            except Exception as exc:  # noqa: BLE001
                raise M2VError(f"打开抖音页面失败：{exc}") from exc
            deadline = time.monotonic() + timeout_s
            html = ""
            while time.monotonic() < deadline:
                if bodies:
                    break
                page.wait_for_timeout(1000)
                try:
                    html = page.content()
                except Exception:  # noqa: BLE001 - 页面正在跳转时稍后重试
                    continue
                if detail_from_html(html):
                    break
            if not html:
                try:
                    html = page.content()
                except Exception:  # noqa: BLE001
                    html = ""
            final_url = page.url
            title = page.title()
        finally:
            context.close()
    return bodies, html, final_url, title


def _short(url: str, limit: int = 100) -> str:
    return url if len(url) <= limit else url[:limit] + "…"


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": DESKTOP_UA, "Referer": REFERER, "Accept": "*/*"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise M2VError(f"HTTP {status}")
        with destination.open("wb") as sink:
            shutil.copyfileobj(response, sink, length=1 << 20)


def _media_signature(path: Path, kind: str) -> bool:
    with path.open("rb") as stream:
        head = stream.read(32)
    if kind == "video":
        return b"ftyp" in head[:16] or head.startswith(b"\x1aE\xdf\xa3")
    return (
        head.startswith(b"\xff\xd8")  # JPEG
        or head.startswith(b"\x89PNG")
        or head.startswith(b"GIF8")
        or (head.startswith(b"RIFF") and head[8:12] == b"WEBP")
        or (head[4:8] == b"ftyp" and head[8:12] in {b"avif", b"avis"})
    )


def _download_first(urls: list[str], destination: Path, kind: str) -> dict:
    errors: list[str] = []
    for url in urls:
        try:
            _download(url, destination)
            if destination.stat().st_size == 0:
                raise M2VError("响应为空")
            if not _media_signature(destination, kind):
                raise M2VError("返回内容不是可识别的媒体（可能是登录或风控页面）")
            return {
                "sha256": _digest(destination),
                "bytes": destination.stat().st_size,
            }
        except (OSError, M2VError) as exc:
            errors.append(f"{_short(url)}：{exc}")
            destination.unlink(missing_ok=True)
    label = "视频" if kind == "video" else "图片"
    raise M2VError(f"{label}下载失败；" + "；".join(errors))


def _guess_ext(url: str, kind: str) -> str:
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    if kind == "video":
        return ".mp4"
    if suffix in _IMAGE_SUFFIXES:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".webp"


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _measure(path: Path) -> dict:
    try:
        width, height = probe_dimensions(path)
    except M2VError:
        return {}
    return {"width": width, "height": height}


def _download_item(item: dict, directory: Path) -> list[dict]:
    records: list[dict] = []
    if item["kind"] == "note":
        if not item["images"]:
            raise M2VError("图文作品没有可下载的图片地址")
        image_dir = directory / "images"
        image_dir.mkdir()
        for index, image in enumerate(item["images"], 1):
            destination = image_dir / f"{index:03d}{_guess_ext(image['urls'][0], 'image')}"
            record = _download_first(image["urls"], destination, "image")
            record["path"] = f"images/{destination.name}"
            record.update(_measure(destination))
            records.append(record)
    else:
        if not item["videoUrls"]:
            raise M2VError("详情没有可用的视频直链")
        destination = directory / "video.mp4"
        record = _download_first(item["videoUrls"], destination, "video")
        record["path"] = "video.mp4"
        record.update(_measure(destination))
        records.append(record)
    return records


def _metadata(item: dict, *, captured_at: str, final_url: str) -> dict:
    return {
        "schemaVersion": 1,
        "awemeId": item["awemeId"],
        "kind": item["kind"],
        "desc": item["desc"],
        "author": item["author"],
        "createTime": item["createTime"],
        "durationMs": item["durationMs"],
        "declaredWidth": item["declaredWidth"],
        "declaredHeight": item["declaredHeight"],
        "coverUrl": item["coverUrl"],
        "sourceUrl": item["sourceUrl"],
        "finalUrl": final_url,
        "capturedAt": captured_at,
        "images": [
            {"width": image["width"], "height": image["height"], "uri": image["uri"]}
            for image in item["images"]
        ],
    }


def fetch(
    target: str,
    *,
    output: str | Path | None = None,
    headed: bool = False,
    force: bool = False,
    timeout_s: float = 45,
) -> FetchResult:
    """下载一条抖音参考素材；已存在时先校验，校验失败必须 ``force`` 才替换。"""
    url = extract_share_url(target)
    expected_id = aweme_id_from_url(url)
    bodies, html, final_url, title = _read_page(url, headed=headed, timeout_s=timeout_s)
    # 短链本身没有作品 ID；跳转后的规范 URL 可以补上，避免从推荐内容里选错详情。
    expected_id = expected_id or aweme_id_from_url(final_url)
    detail = _detail_from_bodies(bodies, expected_id)
    if detail is None and html:
        detail = detail_from_html(html, expected_id)
    if detail is None:
        hint = (
            "；请确认链接可访问且未被风控"
            if headed
            else "；可加 --headed 打开可见浏览器完成登录或验证后重试"
        )
        raise M2VError(f"未能读取抖音作品详情（{final_url}｜{title[:60]}）{hint}")
    item = normalize_detail(
        detail,
        aweme_id=expected_id,
        source_url=url,
        final_url=final_url,
    )
    if not item["awemeId"]:
        raise M2VError("详情缺少作品 ID，无法确定保存目录")

    root = reference_root(output)
    destination = root / item["awemeId"]
    if destination.exists():
        if not force:
            try:
                files = verify_directory(destination, quiet=True)
            except M2VError as exc:
                raise M2VError(
                    f"参考素材已存在但校验失败：{destination}（{exc}）；确认后使用 --force 替换"
                ) from exc
            return FetchResult(destination, item, True, files)

    root.mkdir(parents=True, exist_ok=True)
    staging = root / f".{item['awemeId']}.partial-{os.getpid()}"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    try:
        files = _download_item(item, staging)
        captured_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        metadata = _metadata(item, captured_at=captured_at, final_url=final_url)
        recipe = {
            "schemaVersion": 1,
            "awemeId": item["awemeId"],
            "kind": item["kind"],
            "sourceUrl": url,
            "finalUrl": final_url,
            "capturedAt": captured_at,
            "files": files,
        }
        (staging / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "recipe.json").write_text(
            json.dumps(recipe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if destination.exists():
            previous = root / f".{item['awemeId']}.old-{os.getpid()}"
            shutil.rmtree(previous, ignore_errors=True)
            destination.replace(previous)
            try:
                staging.replace(destination)
            except Exception:
                previous.replace(destination)
                raise
            shutil.rmtree(previous, ignore_errors=True)
        else:
            staging.replace(destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return FetchResult(destination, item, False, files)


def verify_directory(directory: Path, *, quiet: bool = False) -> list[dict]:
    """按 ``recipe.json`` 复核每个文件；任何缺失、字节数或摘要变化都失败。"""
    directory = directory.expanduser().resolve()
    recipe_path = directory / "recipe.json"
    metadata_path = directory / "metadata.json"
    if not recipe_path.is_file():
        raise M2VError(f"缺少 recipe.json：{directory}")
    if not metadata_path.is_file():
        raise M2VError(f"缺少 metadata.json：{directory}")
    try:
        recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise M2VError(f"recipe.json 不是合法 JSON：{exc}") from exc
    if recipe.get("schemaVersion") != 1:
        raise M2VError(f"不支持的 recipe.json 版本：{recipe.get('schemaVersion')!r}")
    entries = recipe.get("files") or []
    if not entries:
        raise M2VError("recipe.json 没有登记任何文件")

    records: list[dict] = []
    problems: list[str] = []
    for entry in entries:
        relative = entry.get("path")
        if not isinstance(relative, str) or not relative:
            problems.append("登记项缺少 path")
            continue
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            problems.append(f"非法路径：{relative}")
            continue
        target = directory / path
        if not target.is_file():
            problems.append(f"缺少文件：{relative}")
            continue
        actual_bytes = target.stat().st_size
        actual_digest = _digest(target)
        if actual_bytes != entry.get("bytes") or actual_digest != entry.get("sha256"):
            problems.append(f"摘要或字节数不符：{relative}")
            continue
        records.append({
            "path": relative,
            "sha256": actual_digest,
            "bytes": actual_bytes,
            "width": entry.get("width"),
            "height": entry.get("height"),
        })
        if not quiet:
            print(f"通过：{relative}（{actual_bytes} 字节）")
    if problems:
        raise M2VError("；".join(problems))
    return records
