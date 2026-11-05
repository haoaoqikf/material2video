"""本地静态文件服务器。

契约页需要按查询参数读到工作区根下的分镜 JSON，还要加载仓库 `web/` 里的
前端工程资源。Chromium 在 file:// 协议下会因同源策略拒绝这些请求，
因此渲染、体检与预览统一走本地 HTTP。

服务器只绑定 127.0.0.1 的随机端口，随渲染进程生命周期创建与销毁。

**挂载**（`mounts`）：文章落在仓库之外时，契约页仍要能引用仓库里的前端工程
资产。把「URL 前缀 → 目录」交给服务器，页面就能用稳定别名
（`/__m2v_web__/dist/contract/contract.html`）引用它们，不必知道内容根与仓库的
相对位置；服务器也不会因此扩大静态根，只有声明过的前缀会被映射，
越界的请求照旧 404。
"""

from __future__ import annotations

import logging
import posixpath
import re
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from m2v.core.errors import M2VError

#: Chromium 明确拒绝访问的端口（`ERR_UNSAFE_PORT`）。操作系统分配的空闲端口偶尔会落进来，
#: 实测命中过 1719；这里收录常用的一段，命中就重摇端口。
_CHROMIUM_BLOCKED_PORTS = frozenset({
    1, 7, 9, 11, 13, 15, 17, 19, 20, 21, 22, 23, 25, 37, 42, 43, 53, 69, 77, 79, 87, 95, 101,
    102, 103, 104, 109, 110, 111, 113, 115, 117, 119, 123, 135, 137, 139, 143, 161, 179, 389,
    427, 465, 512, 513, 514, 515, 526, 530, 531, 532, 540, 548, 554, 556, 563, 587, 601, 636,
    989, 990, 993, 995, 1719, 1720, 1723, 2049, 3659, 4045, 5060, 5061, 6000, 6566, 6665, 6666,
    6667, 6668, 6669, 6697, 10080,
})

logger = logging.getLogger(__name__)

#: 别名下请求目录时返回的占位路径：它不存在，于是照常 404，不列目录
_NO_DIRECTORY_LISTING = "__m2v_directory_listing__"


def _normalize_mounts(mounts: dict[str, str | Path] | None) -> dict[str, Path]:
    """校验并归一化挂载表：前缀一律以 `/` 开头，目录必须存在。

    目录不存在时直接报错，而不是让资产安静地 404——后者在成片里只剩
    「画面没有样式」，很难从结果反推原因。
    """
    normalized: dict[str, Path] = {}
    for prefix, directory in (mounts or {}).items():
        if not prefix.startswith("/"):
            raise ValueError(f"挂载前缀必须以 / 开头: {prefix!r}")
        target = Path(directory).resolve()
        if not target.is_dir():
            raise NotADirectoryError(f"挂载目录不存在: {target}")
        normalized[prefix.rstrip("/")] = target
    return normalized


def _normalize_files(files: dict[str, str | Path] | None, root: Path) -> dict[str, Path]:
    """校验并归一化白名单文件表：地址一律以 `/` 开头且不指回静态根。

    指回静态根的项会被拒绝而不是静默忽略——那等于白名单被绕过，而绕过本身
    不会报错，只会让「只暴露登记素材」这句注释变成假的。
    """
    normalized: dict[str, Path] = {}
    for address, file in (files or {}).items():
        if not address.startswith("/") or posixpath.normpath(address) != address:
            raise ValueError(f"白名单地址必须是归一化后的绝对路径: {address!r}")
        target = Path(file).resolve()
        if not target.is_file():
            raise FileNotFoundError(f"白名单文件不存在: {target}")
        if target.is_relative_to(root):
            raise ValueError(f"白名单文件不得位于静态根内: {target}")
        normalized[address] = target
    return normalized


class _QuietHandler(SimpleHTTPRequestHandler):
    """屏蔽逐请求日志；渲染上千帧时逐帧输出会淹没进度信息。"""

    def __init__(self, *args, mounts: dict[str, Path] | None = None, files: dict[str, Path] | None = None,
                 **kwargs) -> None:
        self.mounts = mounts or {}
        self.files = files or {}
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 (沿用基类签名)
        logger.debug("%s - %s", self.address_string(), format % args)

    def translate_path(self, path: str) -> str:
        """把 URL 路径翻译成本地文件；先查白名单文件，再命中挂载前缀。

        先按 URL 规则归一化（`/__m2v_web__/../x` 会先变成 `/x`），因此别名下的
        `..` 不可能逃出挂载目录；归一化后再做一次解析校验，挡住目录符号链接
        指向挂载目录之外的情况。别名只提供文件，不提供目录列表：挂载的是
        前端工程资产，列出目录既没有用处又多一层暴露。

        `files` 是逐文件的精确白名单（作品媒体走它）：只有登记过的地址可取，
        目录结构本身不可枚举，`/media/../x` 归一化后也不再命中任何一项。
        """
        clean = posixpath.normpath(unquote(path.split("?", 1)[0].split("#", 1)[0]))
        if clean in self.files:
            return str(self.files[clean])
        for prefix, base in self.mounts.items():
            if clean != prefix and not clean.startswith(prefix + "/"):
                continue
            relative = clean[len(prefix) :].lstrip("/")
            target = (base / relative).resolve()
            if target != base and base not in target.parents:
                break  # 越界：交给基类处理，最终 404
            if target.is_dir():
                return str(base / _NO_DIRECTORY_LISTING)
            return str(target)
        return super().translate_path(path)


class _MediaHandler(_QuietHandler):
    def __init__(self, *args, cors: bool = False, **kwargs):
        self.cors = cors
        super().__init__(*args, **kwargs)

    def send_head(self):
        # Chromium 依赖 Range 请求进行音频跳转；仅返回完整文件会使 currentTime 回到 0。
        self._remaining = None
        requested = self.headers.get("Range")
        if not requested:
            return super().send_head()
        path = Path(self.translate_path(self.path))
        if not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested)
        if not match or not any(match.groups()):
            self.send_error(416, "Unsupported range")
            return None
        first, last = match.groups()
        start = int(first) if first else max(0, size - int(last))
        end = min(int(last), size - 1) if first and last else size - 1
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        try:
            stream = path.open("rb")
        except OSError:
            self.send_error(404, "File not found")
            return None
        stream.seek(start)
        self._remaining = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Length", str(self._remaining))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        return stream

    def copyfile(self, source, outputfile):
        try:
            if self._remaining is None:
                return super().copyfile(source, outputfile)
            while self._remaining:
                block = source.read(min(65536, self._remaining))
                if not block:
                    break
                outputfile.write(block)
                self._remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # 帧时钟 seek / 页面退出会取消旧媒体请求；只结束已断开的传输。
            # 不吞掉一般 OSError，磁盘与权限错误仍需暴露。
            self.close_connection = True
            logger.debug("本地媒体请求已由客户端断开：%s", self.path)

    def end_headers(self) -> None:
        # 媒体目录可位于仓库外；单独绑定回环端口，不扩大网页静态根目录。
        if self.cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()


class LocalServer:
    """把某个目录以 HTTP 暴露在 127.0.0.1 的随机端口上。

    `mounts` 可选：给出「URL 前缀 → 目录」，让静态根之外的共享资产也能被
    页面按稳定别名取到（例如仓库里的 skill 资产，配仓库外的内容根）。
    """

    def __init__(
        self,
        root: str | Path,
        port: int = 0,
        cors: bool = False,
        mounts: dict[str, str | Path] | None = None,
        files: dict[str, str | Path] | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise NotADirectoryError(f"静态根目录不存在: {self.root}")
        # 端口 0 表示由操作系统分配空闲端口，渲染时用默认值即可避免冲突。
        self.port = port
        self.cors = cors
        self.mounts = _normalize_mounts(mounts)
        self.files = _normalize_files(files, self.root)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._base_url: str | None = None

    @property
    def base_url(self) -> str:
        """服务的基础 URL，未启动时抛错以免拼出无效地址。"""
        if self._base_url is None:
            raise RuntimeError("静态服务器尚未启动")
        return self._base_url

    def url_for(self, path: str | Path) -> str:
        """某个本地文件在本服务上的 URL。

        文件可以在静态根内（内容根里的文章页面），也可以在挂载目录内
        （仓库里的共享页面配内容根里的文章）；两种都支持，因此「页面」与
        「被引用的资产」不必同处一棵树。
        """
        base = self.base_url
        target = Path(path).resolve()
        try:
            return f"{base}/{target.relative_to(self.root).as_posix()}"
        except ValueError:
            pass
        for prefix, directory in self.mounts.items():
            try:
                relative = target.relative_to(directory)
            except ValueError:
                continue
            return f"{base}{prefix}/{relative.as_posix()}"
        raise M2VError(
            f"{target} 既不在静态根 {self.root} 内，也不在挂载目录 "
            f"{'、'.join(str(d) for d in self.mounts.values()) or '（无）'} 内"
        )

    def start(self) -> str:
        """启动服务并返回基础 URL，例如 http://127.0.0.1:52341。

        端口 0 由操作系统分配，偶尔会落到 Chromium 的**受限端口**上（实测 1719），
        页面加载会直接失败成 `ERR_UNSAFE_PORT`。这类端口一律重摇，最多试十次。
        """
        handler = partial(
            _MediaHandler,
            cors=self.cors,
            directory=str(self.root),
            mounts=self.mounts,
            files=self.files,
        )
        for _attempt in range(10):
            server = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
            port = server.server_address[1]
            if self.port or port not in _CHROMIUM_BLOCKED_PORTS:
                self._server = server
                break
            server.server_close()
        else:  # pragma: no cover - 十次都撞上受限端口几乎不可能
            raise M2VError("无法在 Chromium 可访问的端口上启动静态服务器")
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="m2v-static-server", daemon=True
        )
        self._thread.start()
        host, port = self._server.server_address[:2]
        self._base_url = f"http://{host}:{port}"
        logger.info("静态服务器已启动: %s -> %s", self._base_url, self.root)
        return self._base_url

    def close(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self._base_url = None

    def __enter__(self) -> "LocalServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
