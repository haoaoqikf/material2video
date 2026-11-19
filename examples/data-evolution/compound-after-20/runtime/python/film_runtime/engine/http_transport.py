"""已采用的标准库HTTP传输；不携带图库检索或供应商包装。"""
from __future__ import annotations
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from film_runtime.core.errors import VideoError
MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024

def _safe_url(url: str) -> str:
    """错误信息仅保留端点，避免查询参数中的凭据进入 CLI 日志。"""
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))

class HttpTransport:
    """标准库 HTTP 传输：不引入新的 Python 依赖。"""

    def get_json(self, url: str, headers: dict[str, str], timeout_s: float) -> dict[str, Any]:
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            raise VideoError(f"图库接口返回 {exc.code}：{_safe_url(url)}；请检查凭据、请求参数或额度") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise VideoError(f"无法访问图库接口：{_safe_url(url)}（{type(exc).__name__}）") from None
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            raise VideoError(f"图库接口没有返回合法 JSON：{_safe_url(url)}") from None
        if not isinstance(data, dict):
            raise VideoError(f"图库接口返回的不是对象：{_safe_url(url)}")
        return data

    def download(self, url: str, destination: Path, headers: dict[str, str], timeout_s: float) -> int:
        request = urllib.request.Request(url, headers=headers)
        destination.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response, destination.open("wb") as sink:
                while block := response.read(1024 * 1024):
                    written += len(block)
                    if written > MAX_DOWNLOAD_BYTES:
                        raise VideoError(f"素材文件超过 {MAX_DOWNLOAD_BYTES // (1024 * 1024)}MB 上限：{_safe_url(url)}")
                    sink.write(block)
        except urllib.error.HTTPError as exc:
            destination.unlink(missing_ok=True)
            raise VideoError(f"下载素材失败（{exc.code}）：{_safe_url(url)}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            destination.unlink(missing_ok=True)
            raise VideoError(f"下载素材失败：{_safe_url(url)}（{exc}）") from exc
        if not written:
            destination.unlink(missing_ok=True)
            raise VideoError(f"下载的素材为空：{_safe_url(url)}")
        return written
