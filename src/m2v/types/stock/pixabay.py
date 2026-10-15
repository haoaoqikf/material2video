"""Pixabay 图片、视频检索与作品内的 24 小时响应缓存。"""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Any, TYPE_CHECKING

from m2v.core.errors import M2VError

if TYPE_CHECKING:
    from m2v.types.stock.provider import Candidate, Transport

CACHE_SECONDS = 24 * 60 * 60
PIXABAY_LICENSE = "Pixabay Content License (https://pixabay.com/service/license-summary/)"


class PixabayProvider:
    """保持图库差异在适配器内；CDN 下载无需 API 凭据。"""

    name = "pixabay"

    def __init__(self, config: dict[str, Any], transport: Transport | None = None, *,
                 cache_dir: Path | None = None) -> None:
        from m2v.types.stock.provider import HttpTransport

        self.config = config
        self.base = str(config["apiBase"]).rstrip("/")
        self.transport = transport or HttpTransport()
        self.cache_dir = cache_dir

    def _key(self) -> str:
        key = os.environ.get(str(self.config["apiKeyEnv"]), "").strip()
        if not key:
            raise M2VError(f"缺少图库凭据：请设置环境变量 {self.config['apiKeyEnv']}"
                           "（登录 https://pixabay.com/api/docs/ 查看 API Key）；凭据不写入作品")
        return key

    def headers(self) -> dict[str, str]:
        self._key()  # 统一检索入口在写盘前调用，缺凭据时提前失败。
        return {"User-Agent": "material2video/0.1", "Accept": "application/json"}

    def search(self, query: str, kind: str, per_page: int, timeout_s: float) -> list[Candidate]:
        if kind not in {"video", "photo"}:
            raise M2VError(f"图库不支持媒体类型：{kind}")
        if len(query) > 100:
            raise M2VError("Pixabay 关键词拼接后不能超过 100 个字符；请缩短逐幕关键词")
        params = {"q": query, "per_page": max(3, per_page), "page": 1, "safesearch": "true"}
        if kind == "photo":
            params["image_type"] = "photo"
            direction = {"portrait": "vertical", "landscape": "horizontal"}.get(self.config["orientation"])
            if direction:
                params["orientation"] = direction
        endpoint = self.base + ("/videos/" if kind == "video" else "/")
        key = self._key()
        public_url = endpoint + "?" + urllib.parse.urlencode(params)
        cache_id = hashlib.sha256((public_url + "\0" + key).encode()).hexdigest()
        cached = self._read_cache(cache_id)
        if cached is None:
            url = public_url + "&" + urllib.parse.urlencode({"key": key})
            try:
                cached = self.transport.get_json(url, self.headers(), timeout_s)
            except M2VError as exc:
                # 自定义传输同样不能把 URL 或响应体中的 Key 传给上层。
                raise M2VError(str(exc).replace(key, "[REDACTED]")
                               .replace(urllib.parse.quote_plus(key), "[REDACTED]")) from None
            if not isinstance(cached.get("hits"), list):
                raise M2VError("Pixabay 检索响应缺少有效 hits 数组")
            self._write_cache(cache_id, cached)
        result = [item for raw in cached["hits"] if (item := self._candidate(raw, kind))]
        return result[:per_page]

    def _read_cache(self, cache_id: str) -> dict | None:
        if self.cache_dir is None:
            return None
        try:
            entry = json.loads((self.cache_dir / f"{cache_id}.json").read_text(encoding="utf-8"))
            age = time.time() - entry["createdAt"]
            payload = entry["payload"]
            if 0 <= age < CACHE_SECONDS and isinstance(payload, dict) and isinstance(payload.get("hits"), list):
                return payload
        except (OSError, ValueError, TypeError, KeyError):
            pass  # 缓存不可信或过期时重取，不能让损坏缓存阻断检索。
        return None

    def _write_cache(self, cache_id: str, payload: dict) -> None:
        if self.cache_dir is None:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # 只落标准媒体字段，远端意外回显的请求参数或凭据不会写入缓存。
        fields = {"id", "user", "pageURL", "tags", "duration", "videos", "largeImageURL",
                  "imageWidth", "imageHeight"}
        clean = {"hits": [{key: value for key, value in raw.items() if key in fields}
                           for raw in payload["hits"] if isinstance(raw, dict)]}
        content = json.dumps({"createdAt": time.time(), "payload": clean}, ensure_ascii=False)
        key = self._key()
        if key in content or urllib.parse.quote_plus(key) in content:
            raise M2VError("Pixabay 响应意外包含凭据，拒绝写入缓存")
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.cache_dir,
                                         suffix=".tmp", delete=False) as temporary:
            staged = Path(temporary.name)
            temporary.write(content)
        try:
            staged.replace(self.cache_dir / f"{cache_id}.json")
        finally:
            staged.unlink(missing_ok=True)

    def _candidate(self, raw: Any, kind: str) -> Candidate | None:
        from m2v.types.stock.provider import (Candidate, PHOTO_SUFFIXES, VIDEO_SUFFIXES, _suffix_of,
                                              pick_variant)

        if not isinstance(raw, dict) or not raw.get("id"):
            return None
        author, source = raw.get("user"), raw.get("pageURL")
        if not isinstance(author, str) or not author.strip() or not isinstance(source, str) or not source:
            return None
        try:
            if kind == "video":
                variants = raw.get("videos")
                if not isinstance(variants, dict):
                    return None
                files = [item for item in variants.values() if isinstance(item, dict)
                         and isinstance(item.get("url"), str) and item["url"]]
                if not files:
                    return None
                chosen = pick_variant(files, self.config, "url")
                link = chosen["url"]
                width, height = int(chosen.get("width") or 0), int(chosen.get("height") or 0)
                duration = float(raw.get("duration") or 0)
                if not math.isfinite(duration) or duration <= 0:
                    return None
            else:
                link = raw.get("largeImageURL")
                width, height = int(raw.get("imageWidth") or 0), int(raw.get("imageHeight") or 0)
                if width <= 0 or height <= 0:
                    return None
                scale = min(1.0, 1280 / max(width, height))
                width, height = round(width * scale), round(height * scale)
                duration = None
            if not isinstance(link, str) or not link or width <= 0 or height <= 0:
                return None
            orientation = self.config["orientation"]
            if ((orientation == "portrait" and height <= width)
                    or (orientation == "landscape" and width <= height)
                    or (orientation == "square" and width != height)):
                return None
            if self._key() in link or self._key() in source:
                raise M2VError("Pixabay 响应意外包含凭据，拒绝采用素材")
            return Candidate(str(raw["id"]), kind, width, height, duration, source, author.strip(),
                             PIXABAY_LICENSE, link, str(raw.get("tags") or ""),
                             _suffix_of(link, VIDEO_SUFFIXES if kind == "video" else PHOTO_SUFFIXES,
                                        ".mp4" if kind == "video" else ".jpg"))
        except (ValueError, TypeError, OverflowError):
            return None

    def download(self, candidate: Candidate, destination: Path, timeout_s: float) -> int:
        return self.transport.download(candidate.download_url, destination,
                                       {"User-Agent": "material2video/0.1"}, timeout_s)
