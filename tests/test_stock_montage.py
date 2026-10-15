"""在线素材剪辑类型：检索留证、自动剪辑、音轨与门禁的离线用例。

检索这条链路在测试里走**本机假图库服务**：接口形状与 Pexels 一致，媒体文件由
本机 ffmpeg 生成，因此「检索 → 下载 → 留证 → 校验 → 准备」全部离线可复现，
不需要真实凭据，也不会因为外部服务波动而失败。
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import subprocess
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from conftest import create_typed_project
from m2v.core.errors import M2VError
from m2v.core.project import load_current_prepared, load_project
from m2v.types import registry
from m2v.types.stock import adapter, aspect, brief as brief_module, provider, search, timeline
from m2v.types.stock.pixabay import CACHE_SECONDS, PIXABAY_LICENSE

API_KEY_ENV = "M2V_TEST_PEXELS_KEY"
API_KEY = "test-key-123"


class PixabayTransport:
    """验证 API 参数、下载头和实际媒体留证，不依赖真实凭据。"""

    def __init__(self, media: Path | None = None) -> None:
        self.calls = []
        self.download_headers = []
        self.media = media

    def get_json(self, url, headers, timeout_s):
        self.calls.append(url)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert params["key"] == [API_KEY]
        assert int(params["per_page"][0]) >= 3
        assert "Authorization" not in headers
        common = {"id": 301, "user": "Pixabay 作者", "pageURL": "https://pixabay.com/photos/301/",
                  "tags": "城市 清晨 街景"}
        if parsed.path.endswith("/videos/"):
            return {"hits": [{**common, "duration": 4, "videos": {
                "small": {"url": "https://cdn.example/clip-long.mp4", "width": 540, "height": 960},
                "large": {"url": "https://cdn.example/clip-long.mp4", "width": 1080, "height": 1920}}}]}
        return {"hits": [{**common, "id": 302, "largeImageURL": "https://cdn.example/photo-a.jpg",
                          "imageWidth": 2160, "imageHeight": 3840}]}

    def download(self, url, destination, headers, timeout_s):
        self.download_headers.append(headers)
        assert API_KEY not in str(headers)
        assert "Authorization" not in headers
        data = (self.media / Path(urlparse(url).path).name).read_bytes() if self.media else b"media"
        destination.write_bytes(data)
        return len(data)


def test_pixabay_defaults_and_explicit_overrides():
    raw = _brief("https://custom.example/api", provider={"name": "pixabay"})
    raw["provider"].pop("apiBase")
    raw["provider"].pop("apiKeyEnv")
    normalized = brief_module.normalize(raw)
    assert normalized["provider"]["apiBase"] == "https://pixabay.com/api"
    assert normalized["provider"]["apiKeyEnv"] == "M2V_PIXABAY_API_KEY"
    raw["provider"].update(apiBase="https://custom.example/api", apiKeyEnv=API_KEY_ENV)
    assert brief_module.normalize(raw)["provider"]["apiKeyEnv"] == API_KEY_ENV
    assert brief_module.normalize(raw)["provider"]["apiBase"] == "https://custom.example/api"


def test_pixabay_candidates_cache_and_download(tmp_path, monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, API_KEY)
    config = brief_module.normalize(_brief("https://pixabay.com/api", provider={"name": "pixabay"}))["provider"]
    transport = PixabayTransport()
    library = provider.build(config, transport, cache_dir=tmp_path / "cache")
    for kind, dimensions in (("video", (1080, 1920)), ("photo", (720, 1280))):
        candidates = library.search("城市", kind, 1, 10)
        chosen = candidates[0]
        assert (chosen.width, chosen.height) == dimensions
        assert chosen.license == PIXABAY_LICENSE
        assert library.search("城市", kind, 1, 10) == candidates
        assert provider.build(config, transport, cache_dir=tmp_path / "cache").search("城市", kind, 1, 10) == candidates
        library.download(chosen, tmp_path / f"asset-{kind}", 10)
    assert len(transport.calls) == 2


def test_pixabay_cache_isolated_by_key_and_safe_errors(tmp_path, monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, API_KEY)
    config = brief_module.normalize(_brief("https://pixabay.com/api", provider={"name": "pixabay"}))["provider"]
    transport = PixabayTransport()
    library = provider.build(config, transport, cache_dir=tmp_path)
    library.search("城市", "photo", 3, 10)
    def unavailable(url, headers, timeout_s):
        raise M2VError(url)
    transport.get_json = unavailable
    monkeypatch.setenv(API_KEY_ENV, "rotated-key")
    with pytest.raises(M2VError) as caught:
        library.search("城市", "photo", 3, 10)
    assert "rotated-key" not in str(caught.value)
    assert "REDACTED" in str(caught.value)
    for path in tmp_path.glob("*.json"):
        assert API_KEY not in path.name + path.read_text(encoding="utf-8")


@pytest.mark.parametrize("corruption", ["expired", "broken", "shape"])
def test_pixabay_cache_refresh(tmp_path, monkeypatch, corruption):
    monkeypatch.setenv(API_KEY_ENV, API_KEY)
    config = brief_module.normalize(_brief("https://pixabay.com/api", provider={"name": "pixabay"}))["provider"]
    transport = PixabayTransport()
    library = provider.build(config, transport, cache_dir=tmp_path)
    library.search("城市", "video", 3, 10)
    path = next(tmp_path.glob("*.json"))
    entry = json.loads(path.read_text(encoding="utf-8"))
    if corruption == "expired":
        entry["createdAt"] -= CACHE_SECONDS + 1
    elif corruption == "shape":
        entry = []
    path.write_text("{" if corruption == "broken" else json.dumps(entry), encoding="utf-8")
    assert library.search("城市", "video", 3, 10)
    assert len(transport.calls) == 2


@pytest.mark.parametrize("failure", ["http", "network", "json"])
def test_pixabay_http_errors_do_not_leak_key(monkeypatch, failure):
    import io
    import urllib.error
    import urllib.request

    url = "https://pixabay.com/api/?key=" + API_KEY
    def fail(*args, **kwargs):
        if failure == "http":
            raise urllib.error.HTTPError(url, 429, API_KEY, {}, io.BytesIO(API_KEY.encode()))
        if failure == "network":
            raise urllib.error.URLError(url)
        return io.BytesIO(API_KEY.encode())
    monkeypatch.setattr(urllib.request, "urlopen", fail)
    with pytest.raises(M2VError) as caught:
        provider.HttpTransport().get_json(url, {}, 10)
    assert API_KEY not in str(caught.value)
    assert "pixabay.com/api/" in str(caught.value)


def test_pixabay_missing_key_and_filters(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    config = brief_module.normalize(_brief("https://pixabay.com/api", provider={"name": "pixabay"}))["provider"]
    transport = PixabayTransport()
    library = provider.build(config, transport)
    with pytest.raises(M2VError, match=API_KEY_ENV):
        library.headers()
    assert not transport.calls
    monkeypatch.setenv(API_KEY_ENV, API_KEY)
    with pytest.raises(M2VError, match="100"):
        library.search("x" * 101, "photo", 3, 10)
    assert library._candidate({"id": 1, "user": "a", "pageURL": "https://example.org",
                               "imageWidth": 1920, "imageHeight": 1080,
                               "largeImageURL": "https://example.org/a.jpg"}, "photo") is None
    assert library._candidate({"id": 1, "user": "", "pageURL": "https://example.org"}, "photo") is None


def test_pixabay_full_search_prepare_and_cache(tmp_path, media_dir, monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, API_KEY)
    root, project = _project(tmp_path, _brief("https://pixabay.com/api", provider={"name": "pixabay"},
                                            targetSeconds=6, scenes=[
        {"id": "video", "keywords": ["城市"], "media": "video"},
        {"id": "photo", "keywords": ["城市"], "media": "photo"}]))
    transport = PixabayTransport(media_dir)
    record = search.search(root, project, transport=transport)
    assert record["provider"]["name"] == "pixabay"
    assert API_KEY not in json.dumps(record)
    normalized = brief_module.load(root, project)
    assert search.load_record(root, project, normalized) == record
    adapter.validate(root, project)
    adapter.prepare(root, project)
    assert search.search(root, project, transport=transport) == record
    assert len(transport.calls) == 2


# --------------------------------------------------------------------------- 假图库


class _LibraryHandler(BaseHTTPRequestHandler):
    """按 Pexels 的接口形状回答检索请求，并记录是否带上凭据。"""

    def log_message(self, *args) -> None:  # noqa: A002 - 静默
        pass

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def _json(self, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 约定
        self.server.seen_auth.append(self.headers.get("Authorization"))  # type: ignore[attr-defined]
        parsed = urlparse(self.path)
        if parsed.path in {"/videos/search", "/v1/search"} and not self.headers.get("Authorization"):
            self.send_error(401, "missing key")
            return
        query = parse_qs(parsed.query).get("query", [""])[0]
        if parsed.path == "/videos/search":
            if query in self.server.empty_queries:  # type: ignore[attr-defined]
                self._json({"videos": []})
                return
            self._json({"videos": self._video_candidates(query)})
            return
        if parsed.path == "/v1/search":
            if query in self.server.empty_queries:  # type: ignore[attr-defined]
                self._json({"photos": []})
                return
            self._json({"photos": self._photo_candidates(query)})
            return
        if parsed.path.startswith("/media/"):
            target = self.server.media_dir / Path(parsed.path).name  # type: ignore[attr-defined]
            if not target.is_file():
                self.send_error(404, "no media")
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4" if target.suffix == ".mp4" else "image/jpeg")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404, "unknown")

    def _video(self, entry_id: int, alt: str, author: str, variants: list[tuple[int, int, str]]) -> dict:
        """按声明的变体清单拼一条视频条目；声明尺寸与真实文件可以故意不一致。"""
        return {"id": entry_id, "width": variants[0][0], "height": variants[0][1], "duration": 4,
                "url": f"{self.base}/video/{entry_id}/", "alt": alt, "user": {"name": author},
                "video_files": [
                    {"id": index, "quality": "hd", "file_type": "video/mp4", "width": width,
                     "height": height, "link": f"{self.base}/media/{name}"}
                    for index, (width, height, name) in enumerate(variants, start=1)]}

    def _video_candidates(self, query: str) -> list[dict]:
        """默认返回竖屏候选；特殊关键词返回横屏、变体或声明不实的条目。"""
        if query in self.server.wide_queries:  # type: ignore[attr-defined]
            return [self._video(103, f"{query} 横屏 街景", "作者丁", [(1920, 1080, "clip-wide.mp4")])]
        if query in self.server.mixed_queries:  # type: ignore[attr-defined]
            # 横屏候选的关键词命中更多：只靠排序会选中它，必须靠比例硬过滤淘汰。
            return [self._video(106, f"{query} 街景 城市", "作者壬", [(1920, 1080, "clip-wide.mp4")]),
                    self._video(107, "城市", "作者癸", [(1080, 1920, "clip-long.mp4")])]
        if query in self.server.near_queries:  # type: ignore[attr-defined]
            # 1080×1912 与 9:16 的偏差约 0.4%，用于验证容差边界。
            return [self._video(108, f"{query} 城市 街景", "作者子", [(1080, 1912, "clip-near.mp4")])]
        if query in self.server.variant_queries:  # type: ignore[attr-defined]
            # 旧实现按「最接近 1080 高度」选变体，在 orientation=any 时会选到横屏版本。
            return [self._video(105, f"{query} 城市 街景", "作者戊",
                                [(1920, 1080, "clip-wide.mp4"), (1080, 1920, "clip-long.mp4")])]
        if query in self.server.lying_queries:  # type: ignore[attr-defined]
            return [self._video(104, f"{query} 城市 清晨 街景", "作者己", [(1080, 1920, "clip-wide.mp4")])]
        return [
            self._video(101, "城市 清晨 街景", "作者甲",
                        [(540, 960, "clip-long.mp4"), (1080, 1920, "clip-long.mp4")]),
            self._video(102, "城市 夜景", "作者乙", [(1080, 1920, "clip-short.mp4")]),
        ]

    def _photo_candidates(self, query: str) -> list[dict]:
        if query in self.server.wide_queries:  # type: ignore[attr-defined]
            return [{"id": 202, "width": 1920, "height": 1080, "url": f"{self.base}/photo/202/",
                     "photographer": "作者庚", "alt": f"{query} 横屏 天际线",
                     "src": {"large": f"{self.base}/media/photo-wide.jpg"}}]
        if query in self.server.rendition_queries:  # type: ignore[attr-defined]
            # Pexels 的 portrait 是平台裁切过的版本：它的比例与候选声明的原始尺寸不符。
            return [{"id": 203, "width": 1080, "height": 1920, "url": f"{self.base}/photo/203/",
                     "photographer": "作者辛", "alt": f"{query} 天际线",
                     "src": {"portrait": f"{self.base}/media/photo-wide.jpg",
                             "large": f"{self.base}/media/photo-a.jpg"}}]
        return [{"id": 201, "width": 1080, "height": 1920, "url": f"{self.base}/photo/201/",
                 "photographer": "作者丙", "alt": "城市 清晨 天际线",
                 "src": {"portrait": f"{self.base}/media/photo-a.jpg",
                         "large": f"{self.base}/media/photo-a.jpg"}}]


class FakeLibrary:
    """只服务本机回环地址的假图库；退出时关闭，测试之间互不影响。"""

    def __init__(self, media_dir: Path, empty_queries: set[str] | None = None, *,
                 wide_queries: set[str] | None = None, variant_queries: set[str] | None = None,
                 lying_queries: set[str] | None = None, rendition_queries: set[str] | None = None,
                 mixed_queries: set[str] | None = None, near_queries: set[str] | None = None) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _LibraryHandler)
        self.server.media_dir = media_dir  # type: ignore[attr-defined]
        self.server.empty_queries = empty_queries or set()  # type: ignore[attr-defined]
        self.server.wide_queries = wide_queries or set()  # type: ignore[attr-defined]
        self.server.variant_queries = variant_queries or set()  # type: ignore[attr-defined]
        self.server.lying_queries = lying_queries or set()  # type: ignore[attr-defined]
        self.server.rendition_queries = rendition_queries or set()  # type: ignore[attr-defined]
        self.server.mixed_queries = mixed_queries or set()  # type: ignore[attr-defined]
        self.server.near_queries = near_queries or set()  # type: ignore[attr-defined]
        self.server.seen_auth = []  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self) -> "FakeLibrary":
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


# --------------------------------------------------------------------------- 素材与作品


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """本机生成的小素材：竖屏视频、横屏视频，以及竖屏与横屏图片各一张。"""
    directory = tmp_path_factory.mktemp("stock-media")
    ffmpeg = get_ffmpeg_exe()
    for name, seconds, size in (("clip-long.mp4", 4, "1080x1920"), ("clip-short.mp4", 3, "1080x1920"),
                                ("clip-wide.mp4", 4, "1920x1080"), ("clip-near.mp4", 4, "1080x1912")):
        subprocess.run([ffmpeg, "-y", "-v", "error", "-f", "lavfi",
                        "-i", f"testsrc=size={size}:rate=30:duration={seconds}",
                        "-pix_fmt", "yuv420p", str(directory / name)], check=True, timeout=300)
    for name, size in (("photo-a.jpg", "1080x1920"), ("photo-wide.jpg", "1920x1080")):
        subprocess.run([ffmpeg, "-y", "-v", "error", "-f", "lavfi",
                        "-i", f"color=c=steelblue:size={size}", "-frames:v", "1",
                        str(directory / name)], check=True, timeout=300)
    return directory


def _brief(api_base: str, *, scenes: list[dict] | None = None, **overrides) -> dict:
    payload = {
        "schemaVersion": 1,
        "topic": "城市清晨通勤",
        "targetSeconds": 12,
        "durationToleranceSeconds": 1,
        "provider": {"apiBase": api_base, "apiKeyEnv": API_KEY_ENV},
        "visual": {"theme": "dark", "attribution": "素材来源：测试图库"},
        "scenes": scenes or [
            {"id": "opening", "keywords": ["城市", "清晨"], "transition": {"type": "cut"}},
            {"id": "night", "keywords": ["夜景"], "media": "photo",
             "transition": {"type": "crossfade", "frames": 12}},
        ],
    }
    # provider/visual 按字段合并：用例只覆盖自己关心的那一项，其余保持默认。
    for section in ("provider", "visual"):
        if section in overrides:
            payload[section] = {**payload[section], **overrides.pop(section)}
    payload.update(overrides)
    return payload


def _project(tmp_path: Path, brief: dict) -> tuple[Path, dict]:
    root = tmp_path / "videos" / "stock-montage" / "city-morning"
    create_typed_project(root, "stock-montage")
    (root / brief_module.MATERIAL).write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    return load_project(root)


def _searched(tmp_path: Path, media_dir: Path, brief_fn=None, **library_kwargs) -> tuple[Path, dict, dict]:
    """建作品、跑检索，返回（作品根，作品契约，检索记录）。

    作品里的图库地址必须指向**正在运行**的假图库，因此这里用「基地址 → brief」
    的函数而不是一份写死地址的 brief。
    """
    with FakeLibrary(media_dir, **library_kwargs) as library:
        root, manifest = _project(tmp_path, (brief_fn or _brief)(library.base_url))
        os.environ[API_KEY_ENV] = API_KEY
        try:
            record = search.search(root, manifest)
        finally:
            os.environ.pop(API_KEY_ENV, None)
    return root, manifest, record


def _tone(path: Path, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        stream.writeframes(b"\0\0" * int(seconds * 24000))


def _patch_narration(monkeypatch, seconds: float, cues: list[dict]) -> None:
    """把口播准备替换成固定时长的假实现：用例只关心时间轴，不联网。"""
    from m2v.cli import _register_builtins

    _register_builtins()
    real = registry.get("article-narrative")

    def speak(text, cache, *, voice=None, rate=None, rhythm=None):
        cache.mkdir(parents=True, exist_ok=True)
        wav = cache / f"{hashlib.sha256(text.encode()).hexdigest()[:12]}.wav"
        _tone(wav, seconds)
        return wav, cues, [], seconds, False

    monkeypatch.setitem(registry._registry, "article-narrative",
                        dataclasses.replace(real, prepare_narration=speak))


# --------------------------------------------------------------------------- 材料校验


def test_brief_fills_documented_defaults_and_rejects_bad_fields() -> None:
    brief = brief_module.normalize(_brief("https://api.pexels.com"))
    assert brief["fps"] == 30 and brief["width"] == 1080 and brief["height"] == 1920
    assert brief["provider"]["name"] == "pexels"
    assert brief["provider"]["minClipSeconds"] == 2.5
    assert brief["motion"]["photoZoom"] == 1.12

    for mutation, message in (
        ({"topic": ""}, "topic"),
        ({"targetSeconds": 0}, "targetSeconds"),
        ({"fps": 25}, "fps"),
        ({"visual": {"theme": "dark"}}, "visual.attribution"),
        ({"provider": {"apiKeyEnv": "not an env"}}, "apiKeyEnv"),
        ({"scenes": []}, "scenes 必须是非空数组"),
        ({"scenes": [{"id": "a", "keywords": []}]}, "keywords"),
        ({"scenes": [{"id": "a", "keywords": ["甲"], "durationFrames": 0}]}, "durationFrames"),
        ({"scenes": [{"id": "a", "keywords": ["甲"], "transition": {"type": "fade"}}]}, "transition.type"),
        ({"scenes": [{"id": "a", "keywords": ["甲"], "transition": {"type": "crossfade", "frames": 12}}]},
         "首幕不能声明入场转场"),
        ({"scenes": [{"id": "a", "keywords": ["甲"]}]}, "达不到 targetSeconds"),
        ({"unknownField": 1}, "未知字段"),
    ):
        with pytest.raises(M2VError, match=message):
            brief_module.normalize({**_brief("https://api.pexels.com"), **mutation})


def test_init_template_is_a_valid_reachable_brief() -> None:
    """`m2v init` 写出的模板必须自己就能通过校验，否则新作品第一步就卡住。"""
    from m2v.types import catalog

    entry = catalog.catalog().get("stock-montage")
    template = next(material.template for material in entry.materials if material.file == "brief.json")
    brief = brief_module.normalize(template)
    assert len(brief["scenes"]) >= 4
    assert brief["scenes"][0].get("transition", {}).get("type", "cut") == "cut"


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(M2VError, match="未知图库"):
        provider.build({"name": "nope", "apiBase": "https://example.org", "apiKeyEnv": API_KEY_ENV,
                        "orientation": "portrait", "perPage": 5, "media": ["video"],
                        "minClipSeconds": 2, "maxClipSeconds": 8, "allowReuse": False})


# --------------------------------------------------------------------------- 检索


def test_search_downloads_records_and_repeats_identically(tmp_path: Path, media_dir: Path) -> None:
    with FakeLibrary(media_dir) as library:
        root, manifest = _project(tmp_path, _brief(library.base_url))
        os.environ[API_KEY_ENV] = API_KEY
        try:
            record = search.search(root, manifest)
            again = search.search(root, manifest)
        finally:
            os.environ.pop(API_KEY_ENV, None)
    assert [entry["id"] for entry in record["scenes"]] == ["opening", "night"]
    for entry in record["scenes"]:
        asset = entry["asset"]
        assert asset["author"] and asset["license"] and asset["sourceUrl"]
        assert asset["sha256"] == hashlib.sha256((root / asset["path"]).read_bytes()).hexdigest()
        assert (root / asset["path"]).is_file()
        assert asset["path"].startswith("assets/stock/pexels-")
    assert record["scenes"][0]["asset"]["kind"] == "video"
    assert record["scenes"][1]["asset"]["kind"] == "photo"
    assert record["provider"]["apiBase"].startswith("http://127.0.0.1")

    first = {entry["asset"]["path"]: entry["asset"]["sha256"] for entry in record["scenes"]}
    second = {entry["asset"]["path"]: entry["asset"]["sha256"] for entry in again["scenes"]}
    assert first == second


def test_search_requires_credentials(tmp_path: Path, media_dir: Path) -> None:
    os.environ.pop(API_KEY_ENV, None)
    with FakeLibrary(media_dir) as library:
        root, manifest = _project(tmp_path, _brief(library.base_url))
        with pytest.raises(M2VError, match=API_KEY_ENV):
            search.search(root, manifest)
        assert not search.record_path(root).exists()


def test_search_fails_when_a_scene_has_no_candidate(tmp_path: Path, media_dir: Path) -> None:
    with FakeLibrary(media_dir, empty_queries={"夜景"}) as library:
        root, manifest = _project(tmp_path, _brief(library.base_url))
        os.environ[API_KEY_ENV] = API_KEY
        try:
            with pytest.raises(M2VError, match="night"):
                search.search(root, manifest)
        finally:
            os.environ.pop(API_KEY_ENV, None)
        # 部分成功不落盘：记录文件必须不存在。
        assert not search.record_path(root).exists()


def test_search_never_writes_credentials_into_the_record(tmp_path: Path, media_dir: Path) -> None:
    root, _manifest, _record = _searched(tmp_path, media_dir)
    text = search.record_path(root).read_text(encoding="utf-8")
    assert API_KEY not in text
    assert API_KEY_ENV not in text


# --------------------------------------------------------------------------- 留证复核


def test_validate_rejects_tampered_or_missing_evidence(tmp_path: Path, media_dir: Path) -> None:
    root, manifest, _record = _searched(tmp_path, media_dir)
    adapter.validate(root, manifest)

    record_file = search.record_path(root)
    original = json.loads(record_file.read_text(encoding="utf-8"))

    asset_path = root / original["scenes"][0]["asset"]["path"]
    asset_path.write_bytes(asset_path.read_bytes() + b"tampered")
    with pytest.raises(M2VError, match="素材文件与检索记录不一致"):
        adapter.validate(root, manifest)
    asset_path.write_bytes(asset_path.read_bytes()[: -len(b"tampered")])

    for mutate, message in (
        (lambda data: data["scenes"][0]["asset"].update({"license": ""}), "license"),
        (lambda data: data["scenes"][0]["asset"].update({"path": "../../escape.mp4"}), "越出作品目录"),
        (lambda data: data["scenes"][0]["asset"].update({"author": "  "}), "author"),
    ):
        broken = json.loads(json.dumps(original))
        mutate(broken)
        record_file.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(M2VError, match=message):
            adapter.validate(root, manifest)
    record_file.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
    adapter.validate(root, manifest)


def test_brief_change_expires_the_search_record(tmp_path: Path, media_dir: Path) -> None:
    root, manifest, _record = _searched(tmp_path, media_dir)
    brief = json.loads((root / brief_module.MATERIAL).read_text(encoding="utf-8"))
    brief["scenes"][0]["keywords"] = ["完全不同的关键词"]
    (root / brief_module.MATERIAL).write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="检索记录与当前 brief.json 不一致"):
        adapter.validate(root, manifest)


# --------------------------------------------------------------------------- 自动剪辑


def test_prepare_allocates_frames_and_binds_assets(tmp_path: Path, media_dir: Path) -> None:
    root, manifest, record = _searched(tmp_path, media_dir)
    prepared = adapter.prepare(root, manifest)
    fps = prepared["fps"]
    assert abs(prepared["durationInFrames"] / fps - 12) <= 1
    scenes = prepared["props"]["compiledScenes"]
    assert [scene["startFrame"] for scene in scenes] == [0, scenes[0]["durationInFrames"] - 12]
    assert scenes[0]["asset"]["kind"] == "video"
    assert scenes[0]["motion"] is None
    assert scenes[0]["asset"]["trimStartFrames"] == 0
    assert scenes[1]["asset"]["kind"] == "photo"
    assert scenes[1]["motion"]["zoomFrom"] == pytest.approx(1.12)
    assert scenes[1]["motion"]["zoomTo"] == pytest.approx(1.0)
    assert prepared["props"]["attribution"] == "素材来源：测试图库"
    assert prepared["props"]["mediaBase"] == ""
    for entry in record["scenes"]:
        assert prepared["inputs"]["file:" + entry["asset"]["path"]] == entry["asset"]["sha256"]
    assert load_current_prepared(root, manifest)["preparedFingerprint"] == prepared["preparedFingerprint"]

    (root / brief_module.MATERIAL).write_text('{"schemaVersion":1}', encoding="utf-8")
    with pytest.raises(M2VError, match="材料已变化"):
        load_current_prepared(root, manifest)


def test_prepare_rejects_material_shorter_than_the_minimum(tmp_path: Path, media_dir: Path) -> None:
    # 4 秒的素材低于声明的最小时长 8 秒：分配阶段必须失败，而不是把画面拉长。
    root, manifest, _record = _searched(tmp_path, media_dir, lambda base: _brief(
        base, targetSeconds=30, durationToleranceSeconds=20,
        provider={"minClipSeconds": 8, "maxClipSeconds": 10},
        scenes=[{"id": "opening", "keywords": ["城市"], "media": "video",
                 "transition": {"type": "cut"}}]))
    with pytest.raises(M2VError, match="低于 provider.minClipSeconds"):
        adapter.prepare(root, manifest)


def test_compile_rejects_overlaps_that_swallow_scenes() -> None:
    brief = brief_module.normalize(_brief("https://api.pexels.com", targetSeconds=2,
                                          durationToleranceSeconds=1, scenes=[
        {"id": "a", "keywords": ["甲"], "durationFrames": 30},
        {"id": "b", "keywords": ["乙"], "durationFrames": 30, "transition": {"type": "crossfade", "frames": 30}},
    ]))
    with pytest.raises(M2VError, match="不小于该幕时长"):
        timeline.compile_scenes(brief, [30, 30])


def test_allocate_hits_the_target_within_tolerance() -> None:
    brief = brief_module.normalize(_brief("https://api.pexels.com", targetSeconds=16,
                                          durationToleranceSeconds=0.5, scenes=[
        {"id": "a", "keywords": ["甲"]},
        {"id": "b", "keywords": ["乙"]},
        {"id": "c", "keywords": ["丙"], "durationFrames": 90},
    ]))
    assets = [{"kind": "photo", "path": "p.jpg", "durationSeconds": None},
              {"kind": "video", "path": "v.mp4", "durationSeconds": 6.0},
              {"kind": "photo", "path": "q.jpg", "durationSeconds": None}]
    frames = timeline.allocate(brief, assets, [0, 0, 0], [None, None, 90])
    assert frames[2] == 90
    assert frames[1] <= 6 * brief["fps"]
    assert sum(frames) == 16 * brief["fps"]


# --------------------------------------------------------------------------- 口播与音床


def test_prepare_uses_real_narration_duration_and_subtitles(monkeypatch, tmp_path: Path,
                                                             media_dir: Path) -> None:
    _patch_narration(monkeypatch, 3.0, [{"text": "第一句。", "start": 0.0, "end": 1.4}])
    root, manifest, _record = _searched(tmp_path, media_dir, lambda base: _brief(
        base, targetSeconds=16, durationToleranceSeconds=6, scenes=[
            {"id": "opening", "keywords": ["城市", "清晨"], "narration": "第一句。",
             "transition": {"type": "cut"}},
            {"id": "night", "keywords": ["夜景"], "media": "photo", "transition": {"type": "cut"}},
        ]))
    prepared = adapter.prepare(root, manifest)
    scenes = prepared["props"]["compiledScenes"]
    assert scenes[0]["durationInFrames"] == 3 * prepared["fps"] + brief_module.READING_TAIL_FRAMES
    assert prepared["subtitles"] == [{"startFrame": 0, "endFrame": round(1.4 * prepared["fps"]),
                                      "text": "第一句。"}]
    assert [segment["sceneId"] for segment in prepared["audio"]["segments"]] == ["master"]
    assert prepared["audio"]["segments"][0]["path"] == "outputs/audio.wav"
    assert prepared["inputs"]["file:outputs/audio.wav"]


def test_prepare_rejects_narration_beyond_fixed_capacity(monkeypatch, tmp_path: Path,
                                                         media_dir: Path) -> None:
    _patch_narration(monkeypatch, 5.0, [])
    root, manifest, _record = _searched(tmp_path, media_dir, lambda base: _brief(
        base, targetSeconds=5, durationToleranceSeconds=5, scenes=[
            {"id": "opening", "keywords": ["城市"], "narration": "很长的口播。",
             "durationFrames": 60, "transition": {"type": "cut"}},
        ]))
    with pytest.raises(M2VError, match="超出固定帧数可容纳的"):
        adapter.prepare(root, manifest)


def test_prepare_with_sound_bed_writes_one_master_track(tmp_path: Path, media_dir: Path) -> None:
    root, manifest, _record = _searched(tmp_path, media_dir)
    _tone(root / "assets" / "bed.wav", 12)
    brief = json.loads((root / brief_module.MATERIAL).read_text(encoding="utf-8"))
    brief["soundtrack"] = {"music": {"sourceRef": "assets/bed.wav", "gainDb": -20,
                                     "loop": True, "fadeInMs": 500, "fadeOutMs": 800}}
    (root / brief_module.MATERIAL).write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    prepared = adapter.prepare(root, manifest)
    segments = prepared["audio"]["segments"]
    assert len(segments) == 1 and segments[0]["startFrame"] == 0
    assert segments[0]["durationInFrames"] == prepared["durationInFrames"]
    assert "soundtrack" in json.loads(prepared["inputs"]["sound"])

    brief["soundtrack"]["music"]["sourceRef"] = "../outside.wav"
    (root / brief_module.MATERIAL).write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="本地相对路径"):
        adapter.prepare(root, manifest)


# --------------------------------------------------------------------------- 长宽比契约


def test_aspect_ratio_defaults_and_validation() -> None:
    brief = brief_module.normalize(_brief("https://api.pexels.com"))
    assert brief["provider"]["aspectRatio"] == "canvas"
    assert brief["provider"]["aspectRatioTolerance"] == 0.02

    for mutation, message in (
        ({"provider": {"aspectRatio": "16:9"}}, "provider.aspectRatio"),
        ({"provider": {"aspectRatioTolerance": 0.5}}, "aspectRatioTolerance"),
        ({"provider": {"aspectRatioTolerance": -0.1}}, "aspectRatioTolerance"),
        ({"provider": {"orientation": "landscape"}}, "provider.orientation"),
        ({"provider": {"orientation": "square"}}, "provider.orientation"),
        ({"scenes": [{"id": "a", "keywords": ["甲"], "aspectRatio": "wide"}]}, "aspectRatio"),
    ):
        with pytest.raises(M2VError, match=message):
            brief_module.normalize({**_brief("https://api.pexels.com"), **mutation})


def test_aspect_ratio_any_keeps_the_previous_behaviour() -> None:
    brief = brief_module.normalize({**_brief("https://api.pexels.com"),
                                    "provider": {"aspectRatio": "any", "orientation": "landscape"}})
    assert brief["provider"]["aspectRatio"] == "any"
    assert aspect.target_ratio(brief["provider"]) is None


def test_ratio_matches_tolerance_boundary() -> None:
    ratio = aspect.canvas_ratio()
    assert aspect.ratio_matches(1080, 1920, ratio, 0.0)
    assert aspect.ratio_matches(1080, 1912, ratio, 0.02)      # 偏差约 0.4%
    assert not aspect.ratio_matches(1080, 1830, ratio, 0.02)  # 偏差约 5%
    assert aspect.ratio_matches(1080, 1830, ratio, 0.06)
    assert not aspect.ratio_matches(0, 1920, ratio, 0.02)
    assert not aspect.ratio_matches(1080, 1920.0, ratio, 0.02)


def test_search_drops_mismatched_candidates_even_when_keywords_hit_more(tmp_path: Path,
                                                                       media_dir: Path) -> None:
    """横屏候选的关键词命中更多，也必须被比例契约淘汰。"""
    scenes = [{"id": "mixed", "keywords": ["城市横屏"], "media": "video",
               "transition": {"type": "cut"}}]
    root, _manifest, record = _searched(
        tmp_path, media_dir,
        lambda base: _brief(base, scenes=scenes, targetSeconds=6, durationToleranceSeconds=1,
                            provider={"orientation": "any"}),
        mixed_queries={"城市横屏"})
    asset = record["scenes"][0]["asset"]
    # 实测尺寸就是所下载文件的尺寸：只有竖屏候选的字节会得到 1080×1920。
    assert (asset["width"], asset["height"]) == (1080, 1920)
    assert [item["id"] for item in record["scenes"][0]["candidates"]] == ["107"]
    assert (root / asset["path"]).is_file()


def test_variant_selection_prefers_the_canvas_ratio(tmp_path: Path, media_dir: Path) -> None:
    """orientation=any 时不再偏向「最接近 1080 高度」的横屏变体。"""
    scenes = [{"id": "clip", "keywords": ["比例变体"], "media": "video",
               "transition": {"type": "cut"}}]
    _root, _manifest, record = _searched(
        tmp_path, media_dir,
        lambda base: _brief(base, scenes=scenes, targetSeconds=6, durationToleranceSeconds=1,
                            provider={"orientation": "any"}),
        variant_queries={"比例变体"})
    asset = record["scenes"][0]["asset"]
    # 横屏变体是 1920×1080、竖屏变体是 1080×1920：实测尺寸能区分实际下载了哪个变体。
    assert (asset["width"], asset["height"]) == (1080, 1920)


def test_tolerance_is_applied_to_the_downloaded_file(tmp_path: Path, media_dir: Path) -> None:
    """1080×1912 在默认 2% 容差内可用，收紧容差后同一候选被拒。"""
    scenes = [{"id": "near", "keywords": ["容差边界"], "media": "video",
               "transition": {"type": "cut"}}]
    _root, _manifest, record = _searched(
        tmp_path, media_dir,
        lambda base: _brief(base, scenes=scenes, targetSeconds=6, durationToleranceSeconds=1),
        near_queries={"容差边界"})
    assert (record["scenes"][0]["asset"]["width"], record["scenes"][0]["asset"]["height"]) == (1080, 1912)

    strict = tmp_path / "strict"
    strict.mkdir()
    with FakeLibrary(media_dir, near_queries={"容差边界"}) as library:
        root, manifest = _project(strict, _brief(library.base_url, scenes=scenes, targetSeconds=6,
                                                 durationToleranceSeconds=1,
                                                 provider={"aspectRatioTolerance": 0.001}))
        os.environ[API_KEY_ENV] = API_KEY
        try:
            with pytest.raises(M2VError, match="长宽比"):
                search.search(root, manifest)
        finally:
            os.environ.pop(API_KEY_ENV, None)
        assert not search.record_path(root).exists()


def test_search_fails_loudly_when_only_mismatched_candidates_exist(tmp_path: Path,
                                                                  media_dir: Path) -> None:
    scenes = [{"id": "wide", "keywords": ["城市横屏"], "media": "video",
               "transition": {"type": "cut"}}]
    with FakeLibrary(media_dir, wide_queries={"城市横屏"}) as library:
        root, manifest = _project(tmp_path, _brief(library.base_url, scenes=scenes, targetSeconds=6,
                                                   durationToleranceSeconds=1))
        os.environ[API_KEY_ENV] = API_KEY
        try:
            with pytest.raises(M2VError, match="长宽比") as error:
                search.search(root, manifest)
        finally:
            os.environ.pop(API_KEY_ENV, None)
    message = str(error.value)
    assert "wide" in message and "9:16" in message and "aspectRatio" in message
    assert not search.record_path(root).exists()
    assert not list((root / brief_module.ASSET_DIR).glob("*"))


def test_scene_level_any_allows_another_ratio(tmp_path: Path, media_dir: Path) -> None:
    scenes = [{"id": "wide", "keywords": ["城市横屏"], "media": "video", "aspectRatio": "any",
               "transition": {"type": "cut"}}]
    _root, _manifest, record = _searched(
        tmp_path, media_dir,
        lambda base: _brief(base, scenes=scenes, targetSeconds=6, durationToleranceSeconds=1),
        wide_queries={"城市横屏"})
    assert record["scenes"][0]["aspectRatio"] == "any"
    assert (record["scenes"][0]["asset"]["width"], record["scenes"][0]["asset"]["height"]) == (1920, 1080)


def test_search_rejects_a_declared_size_the_file_does_not_have(tmp_path: Path,
                                                              media_dir: Path) -> None:
    """图库声明 9:16、实际下载到横屏文件时必须失败，且不留无引用素材。"""
    scenes = [{"id": "clip", "keywords": ["声明不实"], "media": "video",
               "transition": {"type": "cut"}}]
    with FakeLibrary(media_dir, lying_queries={"声明不实"}) as library:
        root, manifest = _project(tmp_path, _brief(library.base_url, scenes=scenes, targetSeconds=6,
                                                   durationToleranceSeconds=1))
        os.environ[API_KEY_ENV] = API_KEY
        try:
            with pytest.raises(M2VError, match="实测") as error:
                search.search(root, manifest)
        finally:
            os.environ.pop(API_KEY_ENV, None)
    assert "1920×1080" in str(error.value)
    assert not search.record_path(root).exists()
    assert not list((root / brief_module.ASSET_DIR).glob("*"))


def test_photo_uses_a_ratio_preserving_rendition(tmp_path: Path, media_dir: Path) -> None:
    """Pexels 的 portrait 缩略图是平台裁切版本，比例匹配时应改取原始比例的版本。"""
    scenes = [{"id": "sky", "keywords": ["天际线"], "media": "photo",
               "transition": {"type": "cut"}}]
    _root, _manifest, record = _searched(
        tmp_path, media_dir,
        lambda base: _brief(base, scenes=scenes, targetSeconds=6, durationToleranceSeconds=1),
        rendition_queries={"天际线"})
    asset = record["scenes"][0]["asset"]
    # portrait 缩略图是 1920×1080，原始比例的 large 是 1080×1920：实测尺寸说明取了哪一个。
    assert (asset["width"], asset["height"]) == (1080, 1920)


def test_record_expires_when_the_ratio_declaration_changes(tmp_path: Path, media_dir: Path) -> None:
    root, manifest, _record = _searched(tmp_path, media_dir)
    path = root / brief_module.MATERIAL
    payload = json.loads(path.read_text(encoding="utf-8"))
    # 幕级覆盖进入检索指纹：改声明后旧记录立即过期，必须重新检索。
    payload["scenes"][0]["aspectRatio"] = "any"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="检索记录与当前 brief.json 不一致"):
        adapter.validate(root, manifest)

    other = tmp_path / "second"
    other.mkdir()
    root2, manifest2, _record2 = _searched(other, media_dir)
    # 记录里的图库参数块被改动时同样必须失败，而不是继续用旧参数渲染。
    record2 = search.record_path(root2)
    payload2 = json.loads(record2.read_text(encoding="utf-8"))
    payload2["provider"]["perPage"] = 99
    record2.write_text(json.dumps(payload2, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="图库参数"):
        adapter.validate(root2, manifest2)


def test_validate_rejects_a_recorded_size_that_misses_the_canvas(tmp_path: Path,
                                                                media_dir: Path) -> None:
    root, manifest, _record = _searched(tmp_path, media_dir)
    path = search.record_path(root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["scenes"][0]["asset"]["width"], payload["scenes"][0]["asset"]["height"] = 1920, 1080
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="长宽比"):
        adapter.validate(root, manifest)


def test_reference_documents_the_ratio_contract() -> None:
    text = (Path(__file__).resolve().parents[1] / ".agents/skills/material2video/references"
            / "stock-montage-video.md").read_text(encoding="utf-8")
    assert "长宽比" in text and "aspectRatioTolerance" in text and "实测尺寸" in text


# --------------------------------------------------------------------------- 统一入口


def test_cli_search_command_reports_each_scene(tmp_path: Path, media_dir: Path, capsys) -> None:
    from m2v import cli

    with FakeLibrary(media_dir) as library:
        root, _manifest = _project(tmp_path, _brief(library.base_url))
        os.environ[API_KEY_ENV] = API_KEY
        try:
            code = cli.main(["stock", "search", "--project", str(root)])
        finally:
            os.environ.pop(API_KEY_ENV, None)
    assert code == 0
    out = capsys.readouterr().out
    assert "已检索 2 幕素材" in out and "opening" in out
    # 逐幕输出实测尺寸，交付时可直接核对素材与画布的长宽比。
    assert "1080×1920" in out
    assert search.record_path(root).is_file()


# --------------------------------------------------------------------------- 真实渲染


@pytest.mark.slow
def test_preview_renders_local_media_with_a_master_track(tmp_path: Path, media_dir: Path) -> None:
    """端到端：本机素材经回环 HTTP 进画面，成片帧数、尺寸、帧率与音轨全部验收。"""
    from m2v.engine import output_validation

    root, manifest, _record = _searched(tmp_path, media_dir, lambda base: _brief(
        base, targetSeconds=2.4, durationToleranceSeconds=0.2,
        provider={"minClipSeconds": 0.5, "maxClipSeconds": 2.0},
        scenes=[{"id": "opening", "keywords": ["城市"], "media": "video",
                 "transition": {"type": "cut"}},
                {"id": "night", "keywords": ["夜景"], "media": "photo",
                 "transition": {"type": "crossfade", "frames": 6}}]))
    _tone(root / "assets" / "bed.wav", 3)
    brief = json.loads((root / brief_module.MATERIAL).read_text(encoding="utf-8"))
    brief["soundtrack"] = {"music": {"sourceRef": "assets/bed.wav", "gainDb": -20, "loop": True}}
    (root / brief_module.MATERIAL).write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    prepared = adapter.prepare(root, manifest)
    output = adapter.preview(root, manifest)
    assert output.is_file() and output.stat().st_size > 0
    assert output.parent.name == "previews"
    output_validation.verify_output(output, prepared["durationInFrames"], prepared["width"],
                                    prepared["height"], prepared["fps"], expect_audio=True)
    assert not (root / "outputs" / "video.mp4").exists()
