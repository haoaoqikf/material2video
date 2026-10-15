"""在线图库适配器：把「关键词 → 候选素材」与「候选 → 本地文件」两件事收敛到一处。

支持 Pexels 和 Pixabay。适配器按 ``provider.name`` 选择，未知名称直接失败并列出
可用名称，不做静默降级。

网络访问全部走可注入的 :class:`Transport`：生产用标准库 ``urllib``（不新增依赖），
测试用本机假图库服务，因此检索与下载这条链路可以完全离线验证。

凭据只从环境变量读取，绝不出现在作品材料、导入记录或日志里。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from m2v.core.errors import M2VError
from m2v.engine.gallery import aspect
from m2v.engine.gallery.pixabay import PixabayProvider

#: 单个素材文件的下载上限：图库返回异常大文件时直接失败，而不是把磁盘写满。
MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024

#: 允许落盘的素材扩展名：画面只解码这几种，其他一律按不可用处理。
VIDEO_SUFFIXES = (".mp4", ".mov", ".m4v", ".webm")
PHOTO_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")

DEFAULT_TIMEOUT_SECONDS = 30.0

PEXELS_LICENSE = "Pexels License (https://www.pexels.com/license/)"

PROVIDER_DEFAULTS = {
    "pexels": {"apiBase": "https://api.pexels.com", "apiKeyEnv": "M2V_PEXELS_API_KEY"},
    "pixabay": {"apiBase": "https://pixabay.com/api", "apiKeyEnv": "M2V_PIXABAY_API_KEY"},
}


def _safe_url(url: str) -> str:
    """错误信息仅保留端点，避免查询参数中的凭据进入 CLI 日志。"""
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


@dataclass(frozen=True)
class Candidate:
    """一个可下载的候选素材：检索阶段唯一需要留下的东西。"""

    id: str
    kind: str  # "video" 或 "photo"
    width: int
    height: int
    duration_seconds: float | None
    source_url: str
    author: str
    license: str
    download_url: str
    description: str
    suffix: str

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "width": self.width, "height": self.height,
                "durationSeconds": self.duration_seconds, "sourceUrl": self.source_url,
                "author": self.author, "license": self.license, "description": self.description}


class Transport(Protocol):
    """网络访问接口。生产实现是标准库，测试实现是本地假服务。"""

    def get_json(self, url: str, headers: dict[str, str], timeout_s: float) -> dict[str, Any]: ...

    def download(self, url: str, destination: Path, headers: dict[str, str], timeout_s: float) -> int: ...


class HttpTransport:
    """标准库 HTTP 传输：不引入新的 Python 依赖。"""

    def get_json(self, url: str, headers: dict[str, str], timeout_s: float) -> dict[str, Any]:
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            raise M2VError(f"图库接口返回 {exc.code}：{_safe_url(url)}；请检查凭据、请求参数或额度") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise M2VError(f"无法访问图库接口：{_safe_url(url)}（{type(exc).__name__}）") from None
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            raise M2VError(f"图库接口没有返回合法 JSON：{_safe_url(url)}") from None
        if not isinstance(data, dict):
            raise M2VError(f"图库接口返回的不是对象：{_safe_url(url)}")
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
                        raise M2VError(f"素材文件超过 {MAX_DOWNLOAD_BYTES // (1024 * 1024)}MB 上限：{_safe_url(url)}")
                    sink.write(block)
        except urllib.error.HTTPError as exc:
            destination.unlink(missing_ok=True)
            raise M2VError(f"下载素材失败（{exc.code}）：{_safe_url(url)}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            destination.unlink(missing_ok=True)
            raise M2VError(f"下载素材失败：{_safe_url(url)}（{exc}）") from exc
        if not written:
            destination.unlink(missing_ok=True)
            raise M2VError(f"下载的素材为空：{_safe_url(url)}")
        return written


def _suffix_of(url: str, allowed: tuple[str, ...], fallback: str) -> str:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return suffix if suffix in allowed else fallback


def _target_height(config: dict[str, Any]) -> int:
    return 1920 if config.get("orientation") in {"portrait", "square"} else 1080


def _variant_ratio(item: Any) -> float:
    """变体自身的宽高比；尺寸缺失或非法时返回 0（排序时必然落选）。"""
    if not isinstance(item, dict):
        return 0.0
    width, height = int(item.get("width") or 0), int(item.get("height") or 0)
    return width / height if width > 0 and height > 0 else 0.0


def pick_variant(files: list[dict], config: dict[str, Any], link_key: str) -> dict:
    """选下载变体：声明画布比例时按比例最接近（其次面积最大）选，否则按目标高度选。

    只看高度会让 ``orientation: "any"`` 的作品偏向横屏版本（目标高度退化成 1080），
    于是竖屏画布拿到横屏素材；因此比例契约生效时以比例为首要依据。
    """
    ratio = aspect.target_ratio(config)
    if ratio is not None:
        def key(item: dict) -> tuple:
            own = _variant_ratio(item)
            distance = abs(own - ratio) if own else float("inf")
            width, height = int(item.get("width") or 0), int(item.get("height") or 0)
            return (distance, -(width * height), str(item[link_key]))
        return min(files, key=key)
    target = _target_height(config)
    return min(files, key=lambda item: (abs(int(item.get("height") or 0) - target), str(item[link_key])))


class PexelsProvider:
    """Pexels 图库适配器（图片 + 视频）。"""

    name = "pexels"

    def __init__(self, config: dict[str, Any], transport: Transport | None = None) -> None:
        self.config = config
        self.base = str(config["apiBase"]).rstrip("/")
        self.orientation = str(config["orientation"])
        self.transport = transport or HttpTransport()

    def headers(self) -> dict[str, str]:
        """读取凭据；缺失时给出环境变量名与获取方式，不发起请求。"""
        key = os.environ.get(str(self.config["apiKeyEnv"]), "").strip()
        if not key:
            raise M2VError(
                f"缺少图库凭据：请设置环境变量 {self.config['apiKeyEnv']}"
                f"（在 {self.config['apiBase']} 申请免费 API key）；凭据只从环境变量读取，不写入作品"
            )
        return {"Authorization": key, "User-Agent": "material2video/0.1", "Accept": "application/json"}

    def search(self, query: str, kind: str, per_page: int, timeout_s: float) -> list[Candidate]:
        if kind == "video":
            url = f"{self.base}/videos/search?" + urllib.parse.urlencode(
                {"query": query, "orientation": self.orientation, "per_page": per_page, "page": 1})
            payload = self.transport.get_json(url, self.headers(), timeout_s)
            return [item for raw in payload.get("videos") or [] if (item := self._video(raw))]
        if kind == "photo":
            url = f"{self.base}/v1/search?" + urllib.parse.urlencode(
                {"query": query, "orientation": self.orientation, "per_page": per_page, "page": 1})
            payload = self.transport.get_json(url, self.headers(), timeout_s)
            return [item for raw in payload.get("photos") or [] if (item := self._photo(raw))]
        raise M2VError(f"图库不支持媒体类型：{kind}")

    def download(self, candidate: Candidate, destination: Path, timeout_s: float) -> int:
        return self.transport.download(candidate.download_url, destination, self.headers(), timeout_s)

    def _video(self, raw: Any) -> Candidate | None:
        """从视频条目里选一个可用的 MP4 文件；作者或许可缺失时不采用。"""
        if not isinstance(raw, dict):
            return None
        author = ((raw.get("user") or {}) if isinstance(raw.get("user"), dict) else {}).get("name")
        files = [item for item in raw.get("video_files") or []
                 if isinstance(item, dict) and str(item.get("file_type", "")).startswith("video/mp4")
                 and isinstance(item.get("link"), str) and item["link"]]
        if not files or not isinstance(author, str) or not author.strip():
            return None
        chosen = pick_variant(files, self.config, "link")
        duration = raw.get("duration")
        return Candidate(
            id=str(raw.get("id")), kind="video",
            width=int(chosen.get("width") or raw.get("width") or 0),
            height=int(chosen.get("height") or raw.get("height") or 0),
            duration_seconds=float(duration) if isinstance(duration, (int, float)) and not isinstance(duration, bool) else None,
            source_url=str(raw.get("url") or ""), author=author.strip(), license=PEXELS_LICENSE,
            download_url=str(chosen["link"]), description=str(raw.get("alt") or raw.get("url") or ""),
            suffix=_suffix_of(str(chosen["link"]), VIDEO_SUFFIXES, ".mp4"))

    def _photo(self, raw: Any) -> Candidate | None:
        if not isinstance(raw, dict):
            return None
        author = raw.get("photographer")
        sources = raw.get("src") if isinstance(raw.get("src"), dict) else {}
        # 声明画布比例时只取保持原始比例的缩略图：Pexels 的 `portrait` 是平台裁切过的
        # 版本，它的实际比例与候选记录的原始尺寸不一致，会让「记录尺寸 = 实测尺寸」失守。
        if aspect.target_ratio(self.config) is not None:
            preferred = ("large2x", "original", "large", "medium")
        elif self.orientation in {"portrait", "square"}:
            preferred = ("portrait", "large", "large2x", "original")
        else:
            preferred = ("large", "original", "large2x", "portrait")
        link = next((sources[key] for key in preferred if isinstance(sources.get(key), str) and sources[key]), None)
        if not link or not isinstance(author, str) or not author.strip():
            return None
        return Candidate(
            id=str(raw.get("id")), kind="photo",
            width=int(raw.get("width") or 0), height=int(raw.get("height") or 0),
            duration_seconds=None, source_url=str(raw.get("url") or ""), author=author.strip(),
            license=PEXELS_LICENSE, download_url=str(link),
            description=str(raw.get("alt") or raw.get("url") or ""),
            suffix=_suffix_of(str(link), PHOTO_SUFFIXES, ".jpg"))


PROVIDERS: dict[str, type] = {"pexels": PexelsProvider, "pixabay": PixabayProvider}


def build(config: dict[str, Any], transport: Transport | None = None, *,
          cache_dir: Path | None = None) -> PexelsProvider | PixabayProvider:
    """按 ``provider.name`` 构造适配器；未知名称直接失败并列出可用名称。"""
    factory = PROVIDERS.get(str(config["name"]))
    if factory is None:
        raise M2VError(
            f"未知图库：{config['name']}；当前可用：{'、'.join(sorted(PROVIDERS))}")
    if factory is PixabayProvider:
        return factory(config, transport, cache_dir=cache_dir)
    return factory(config, transport)
