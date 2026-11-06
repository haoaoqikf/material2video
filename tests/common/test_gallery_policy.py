"""图库方向偏好与缓存：不联网、不依赖真实媒体。"""
from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from m2v.core.errors import M2VError
from m2v.engine.gallery import build
from m2v.types.scene_film.media_assets import gallery_config


class Transport:
    def __init__(self):
        self.urls = []

    def get_json(self, url, headers, timeout_s):
        self.urls.append(url)
        hits = [{"id": identity, "user": "作者", "pageURL": f"https://example.com/{identity}",
                          "imageWidth": width, "imageHeight": height,
                          "largeImageURL": f"https://example.com/{identity}.jpg", "duration": 4,
                          "videos": {"large": {"url": f"https://example.com/{identity}.mp4",
                                               "width": width, "height": height}}}
                for identity, width, height in [(1, 1920, 1080), (2, 1080, 1920), (3, 800, 800)]]
        return {"hits": hits}


@pytest.mark.parametrize("kind", ["photo", "video"])
def test_orientation_prefers_without_dropping_and_reuses_cache(tmp_path, monkeypatch, kind):
    monkeypatch.setenv("M2V_PIXABAY_API_KEY", "private-test-key")
    transport = Transport()
    portrait = build(gallery_config("pixabay", (1080, 1920)), transport, cache_dir=tmp_path)
    candidates = portrait.search("factory", kind, 15, 30)
    assert [item.id for item in candidates] == ["2", "1", "3"]
    assert "orientation" not in parse_qs(urlsplit(transport.urls[0]).query)
    landscape = build(gallery_config("pixabay", (1920, 1080)), transport, cache_dir=tmp_path)
    assert [item.id for item in landscape.search("factory", kind, 15, 30)] == ["1", "2", "3"]
    assert len(transport.urls) == 1
    item = candidates[0].to_json()
    suffix = "jpg" if kind == "photo" else "mp4"
    assert item["mediaUrl"].endswith(f"/2.{suffix}") and item["sourceType"] == "stock"
    assert item["usage"] == {"status": "not-checked"}
    assert "private-test-key" not in json.dumps(item)
    assert all("private-test-key" not in file.read_text(encoding="utf-8") for file in tmp_path.glob("*.json"))
    monkeypatch.delenv("M2V_PIXABAY_API_KEY")
    with pytest.raises(M2VError, match="M2V_PIXABAY_API_KEY"):
        portrait.search("factory", kind, 15, 30)
