"""本地静态文件服务器。

动画网页需要 fetch 同目录的分镜 JSON、样式和字体。Chromium 在 file://
协议下会因同源策略拒绝这些请求，因此渲染与预览统一走本地 HTTP。

服务器只绑定 127.0.0.1 的随机端口，随渲染进程生命周期创建与销毁。
"""

from __future__ import annotations

import logging
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logger = logging.getLogger(__name__)


class _QuietHandler(SimpleHTTPRequestHandler):
    """屏蔽逐请求日志；渲染上千帧时逐帧输出会淹没进度信息。"""

    def log_message(self, format: str, *args) -> None:  # noqa: A002 (沿用基类签名)
        logger.debug("%s - %s", self.address_string(), format % args)


class LocalServer:
    """把某个目录以 HTTP 暴露在 127.0.0.1 的随机端口上。"""

    def __init__(self, root: str | Path, port: int = 0) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise NotADirectoryError(f"静态根目录不存在: {self.root}")
        # 端口 0 表示由操作系统分配空闲端口，渲染时用默认值即可避免冲突。
        self.port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._base_url: str | None = None

    @property
    def base_url(self) -> str:
        """服务的基础 URL，未启动时抛错以免拼出无效地址。"""
        if self._base_url is None:
            raise RuntimeError("静态服务器尚未启动")
        return self._base_url

    def start(self) -> str:
        """启动服务并返回基础 URL，例如 http://127.0.0.1:52341。"""
        handler = partial(_QuietHandler, directory=str(self.root))
        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="a2v-static-server", daemon=True
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
