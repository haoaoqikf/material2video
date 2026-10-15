"""文章混合媒体：图库检索、导入留证与素材一致性。"""
from __future__ import annotations

import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.core.errors import M2VError
from m2v.engine.gallery import HttpTransport, build
from m2v.types.article import adapter, media_assets
from test_article_explainer import board, fake_tts, project

ROOT = Path(__file__).resolve().parents[1]
PEXELS_VIDEO = {
    "id": 77, "width": 1080, "height": 1920, "duration": 6, "url": "https://www.pexels.com/video/77/",
    "alt": "竖屏空镜", "user": {"name": "示例作者"},
    "video_files": [
        {"file_type": "video/mp4", "link": "https://cdn.example/77-sd.mp4", "width": 720, "height": 1280},
        {"file_type": "video/mp4", "link": "https://cdn.example/77-hd.mp4", "width": 1080, "height": 1920},
    ],
}
PEXELS_PHOTO = {
    "id": 88, "width": 1080, "height": 1920, "url": "https://www.pexels.com/photo/88/", "alt": "竖屏照片",
    "photographer": "示例摄影师",
    "src": {"large2x": "https://cdn.example/88.jpg", "portrait": "https://cdn.example/88-cropped.jpg"},
}


def make_image(path: Path, size: str = "864x700") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"color=c=0x334455:s={size}", "-frames:v", "1", str(path)], check=True)
    return path


def make_video(path: Path, seconds: int = 4, size: str = "1080x1920") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"color=c=0x223344:s={size}:r=30:d={seconds}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def importer(root: Path, entries, base: Path | None = None, **kwargs):
    return media_assets.import_assets(root, {"schemaVersion": 1, "assets": entries},
                                     base=base or root, **kwargs)


def entry(identity, kind, **extra):
    return {"id": identity, "kind": kind, **extra}


class FakeGallery:
    """本机假图库：检索与下载都不出网。"""

    def __init__(self, videos=None, photos=None, blob=b"media-bytes"):
        self.videos, self.photos, self.blob = videos or [], photos or [], blob
        self.urls: list[str] = []

    def get_json(self, url, headers, timeout_s):
        self.urls.append(url)
        return {"videos": self.videos} if "/videos/search" in url else {"photos": self.photos}

    def download(self, url, destination, headers, timeout_s):
        destination.write_bytes(self.blob)
        return len(self.blob)


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "video"
    (root / "assets").mkdir(parents=True)
    return root


def test_import_copies_local_media_and_records_provenance(workspace):
    make_image(workspace / "assets/wide.png")
    make_video(workspace / "assets/clip.mp4")
    record = importer(workspace, [
        entry("wide", "image", localPath="assets/wide.png", sourceUrl="https://example.com/a", author="作者甲", license="CC0"),
        entry("clip", "video", localPath="assets/clip.mp4"),
    ])
    image, video = record["assets"]
    assert record["schemaVersion"] == 1
    assert image["path"].startswith("assets/media/") and image["path"].endswith(".png")
    assert (image["width"], image["height"]) == (864, 700) and image["durationSeconds"] is None
    assert video["durationSeconds"] == pytest.approx(4, abs=.1) and (video["width"], video["height"]) == (1080, 1920)
    # 来源页、作者与许可缺失时如实记为「未知」，不猜测。
    assert video["sourceUrl"] == "未知" and video["mediaUrl"] == "未知"
    assert (video["author"], video["license"]) == ("未知", "未知")
    assert image["sourceUrl"] == "https://example.com/a" and image["author"] == "作者甲"
    for item in record["assets"]:
        file = workspace / item["path"]
        assert file.is_file() and media_assets.asset_digest(file) == item["sha256"]
        assert file.name.startswith(item["sha256"])
    # 记录可重复读取，且不因再次导入同一批素材而重复。
    again = importer(workspace, [entry("wide", "image", localPath="assets/wide.png")])
    assert [item["id"] for item in again["assets"]] == ["clip", "wide"]


def test_import_is_all_or_nothing(workspace):
    make_image(workspace / "assets/wide.png")
    with pytest.raises(M2VError, match="导入失败"):
        importer(workspace, [entry("wide", "image", localPath="assets/wide.png"),
                             entry("missing", "image", localPath="assets/none.png")])
    assert not (workspace / "assets/media-sources.json").exists()
    assert list((workspace / "assets/media").iterdir()) == []


@pytest.mark.parametrize("bad,match", [
    (entry("x", "image", localPath="assets/wide.png", mediaUrl="https://example.com/a.png"), "二选一"),
    (entry("x", "audio", localPath="assets/wide.png"), "kind 必须为"),
    (entry("x", "image", localPath="assets/wide.png", sourceUrl="ftp://example.com/a"), "公开网页地址"),
    (entry("x", "image", mediaUrl="file:///etc/passwd"), "HTTP\\(S\\) 媒体直链"),
    (entry("不合法 id", "image", localPath="assets/wide.png"), "id 无效"),
    (entry("x", "image"), "二选一"),
])
def test_import_rejects_invalid_entries(workspace, bad, match):
    make_image(workspace / "assets/wide.png")
    with pytest.raises(M2VError, match=match):
        importer(workspace, [bad])


def test_import_rejects_type_mismatch(workspace):
    make_image(workspace / "assets/wide.png")
    with pytest.raises(M2VError, match="媒体类型不符"):
        importer(workspace, [entry("x", "video", localPath="assets/wide.png")])


def test_import_validates_manifest_shape(workspace):
    with pytest.raises(M2VError, match="schemaVersion"):
        media_assets.import_assets(workspace, {"schemaVersion": 2, "assets": []}, base=workspace)
    with pytest.raises(M2VError, match="1～300"):
        media_assets.import_assets(workspace, {"schemaVersion": 1, "assets": []}, base=workspace)
    with pytest.raises(M2VError, match="timeoutSeconds"):
        importer(workspace, [entry("x", "image", localPath="a.png")], timeout_s=0)


class _Handler(BaseHTTPRequestHandler):
    blob = b""
    status = 200

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler 的接口名
        if self.status != 200:
            self.send_error(self.status)
            return
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", str(len(self.blob)))
        self.end_headers()
        self.wfile.write(self.blob)

    def log_message(self, *_):  # 保持测试输出干净
        pass


@pytest.fixture
def local_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def test_import_downloads_over_http(workspace, local_server):
    clip = make_video(workspace / "assets/clip.mp4")
    _Handler.blob = clip.read_bytes()
    url = f"http://127.0.0.1:{local_server.server_port}/clip.mp4"
    record = importer(workspace, [entry("clip", "video", mediaUrl=url, author="作者乙", license="Pexels License")],
                      transport=HttpTransport())
    item = record["assets"][0]
    assert item["mediaUrl"] == url and item["kind"] == "video"
    assert (workspace / item["path"]).read_bytes() == clip.read_bytes()


def test_download_failure_leaves_no_record(workspace, local_server):
    _Handler.status = 404
    try:
        with pytest.raises(M2VError, match="导入失败"):
            importer(workspace, [entry("clip", "video", mediaUrl=f"http://127.0.0.1:{local_server.server_port}/x.mp4")],
                     transport=HttpTransport())
    finally:
        _Handler.status = 200
    assert not (workspace / "assets/media-sources.json").exists()


def test_import_can_reuse_one_file_for_two_ids(workspace):
    make_image(workspace / "assets/wide.png")
    record = importer(workspace, [entry("a", "image", localPath="assets/wide.png"),
                                  entry("b", "image", localPath="assets/wide.png")])
    assert record["assets"][0]["path"] == record["assets"][1]["path"]


def test_record_and_file_must_agree(workspace):
    make_image(workspace / "assets/wide.png")
    record = importer(workspace, [entry("wide", "image", localPath="assets/wide.png")])
    file = workspace / record["assets"][0]["path"]
    scene = {"id": "s", "template": "image", "aspectRatio": "any",
             "content": {"title": "图", "src": record["assets"][0]["path"]}}
    assert media_assets.validate_scene(workspace, scene)["width"] == 864
    make_image(file, "1080x1920")
    with pytest.raises(M2VError, match="与来源记录不符"):
        media_assets.validate_scene(workspace, scene)
    (workspace / "assets/media-sources.json").unlink()
    with pytest.raises(M2VError, match="没有导入记录"):
        media_assets.validate_scene(workspace, scene)


def test_invalid_record_is_reported(workspace):
    make_image(workspace / "assets/wide.png")
    importer(workspace, [entry("wide", "image", localPath="assets/wide.png")])
    (workspace / "assets/media-sources.json").write_text("{", encoding="utf-8")
    with pytest.raises(M2VError, match="来源记录无效"):
        media_assets.load_record(workspace)


def test_aspect_ratio_contract_and_trim_bounds(workspace):
    make_image(workspace / "assets/wide.png")
    make_video(workspace / "assets/clip.mp4", seconds=2)
    record = importer(workspace, [entry("wide", "image", localPath="assets/wide.png"),
                                  entry("clip", "video", localPath="assets/clip.mp4")])
    paths = {item["id"]: item["path"] for item in record["assets"]}
    image = {"id": "s", "template": "image", "content": {"title": "图", "src": paths["wide"]}}
    with pytest.raises(M2VError, match="素材比例不符"):
        media_assets.validate_scene(workspace, image)
    image["aspectRatio"] = "any"
    media_assets.validate_scene(workspace, image)
    image["aspectRatio"] = "wide"
    with pytest.raises(M2VError, match="aspectRatio 必须为 canvas/any"):
        media_assets.validate_scene(workspace, image)
    image["aspectRatio"] = "any"; image["content"]["photoZoom"] = 1.5
    with pytest.raises(M2VError, match="photoZoom"):
        media_assets.validate_scene(workspace, image)
    video = {"id": "v", "template": "video", "content": {"title": "片", "src": paths["clip"], "trimStartSeconds": 3}}
    with pytest.raises(M2VError, match="trimStartSeconds"):
        media_assets.validate_scene(workspace, video)


def test_scene_without_record_blocks_validate_and_prepare(tmp_path, monkeypatch):
    data = board()
    data["scenes"].append({"id": "shot", "template": "image", "narrationSegments": [],
                           "content": {"title": "空镜", "src": "assets/media/orphan.png"}})
    root, manifest = project(tmp_path, data)
    (root / "assets/media").mkdir(parents=True)
    make_image(root / "assets/media/orphan.png", "1080x1920")
    from m2v.types.article import explainer
    with pytest.raises(M2VError, match="没有导入记录"):
        explainer.validate(data, root)
    fake_tts(monkeypatch)
    with pytest.raises(M2VError, match="没有导入记录"):
        adapter.prepare(root, manifest)


def test_video_scene_beyond_media_duration_blocks_prepare(tmp_path, monkeypatch):
    root, manifest = project(tmp_path)
    make_video(root / "assets/clip.mp4", seconds=4)
    record = importer(root, [entry("clip", "video", localPath="assets/clip.mp4")])
    data = board()
    data["scenes"].append({"id": "shot", "template": "video", "narrationSegments": [],
                           "content": {"title": "空镜", "src": record["assets"][0]["path"],
                                       "trimStartSeconds": 3},
                           "durationFrames": 90})
    (root / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    fake_tts(monkeypatch)
    with pytest.raises(M2VError, match="剩余时长不足"):
        adapter.prepare(root, manifest)


def test_gallery_search_uses_scene_keywords(tmp_path, monkeypatch):
    root, manifest = project(tmp_path)
    monkeypatch.setenv("M2V_PEXELS_API_KEY", "test-key")
    gallery = FakeGallery(videos=[PEXELS_VIDEO], photos=[PEXELS_PHOTO])
    result = media_assets.search(root, manifest, transport=gallery)
    assert result["provider"] == "pexels" and result["kind"] == "both" and result["schemaVersion"] == 1
    query = result["queries"][0]
    assert query["sceneId"] == "a" and query["query"] == "反馈"
    kinds = {item["kind"] for item in query["candidates"]}
    assert kinds == {"video", "photo"}
    video = next(item for item in query["candidates"] if item["kind"] == "video")
    # 画布比例优先：选中 1080×1920 变体，而不是更高的 720×1280。
    assert video["width"] == 1080 and video["height"] == 1920 and video["durationSeconds"] == 6
    assert video["license"].startswith("Pexels License")
    assert all("download_url" not in item for item in query["candidates"])
    # 检索结果只是候选，不写作品文件。
    assert not (root / "assets").exists()


def test_gallery_search_without_candidates_is_not_a_failure(tmp_path, monkeypatch):
    root, manifest = project(tmp_path)
    monkeypatch.setenv("M2V_PEXELS_API_KEY", "test-key")
    result = media_assets.search(root, manifest, transport=FakeGallery(), kind="photo")
    assert result["queries"][0]["candidates"] == []


def test_gallery_search_argument_errors(tmp_path, monkeypatch):
    root, manifest = project(tmp_path)
    monkeypatch.setenv("M2V_PEXELS_API_KEY", "test-key")
    gallery = FakeGallery()
    with pytest.raises(M2VError, match="kind 必须为"):
        media_assets.search(root, manifest, kind="audio", transport=gallery)
    with pytest.raises(M2VError, match="perPage"):
        media_assets.search(root, manifest, per_page=0, transport=gallery)
    with pytest.raises(M2VError, match="不一致"):
        media_assets.search(root, manifest, queries=["一", "二"], transport=gallery)
    with pytest.raises(M2VError, match="非空文本"):
        media_assets.search(root, manifest, queries=["  "], transport=gallery)
    with pytest.raises(M2VError, match="未知图库"):
        media_assets.search(root, manifest, provider_name="unsplash", transport=gallery)
    # 缺少凭据时给出环境变量名，而不是静默退回匿名请求。
    monkeypatch.delenv("M2V_PEXELS_API_KEY")
    with pytest.raises(M2VError, match="M2V_PEXELS_API_KEY"):
        media_assets.search(root, manifest, transport=gallery)


def test_gallery_config_defaults_to_portrait_canvas():
    config = media_assets.gallery_config("pexels")
    assert config["orientation"] == "portrait" and config["aspectRatio"] == "canvas"
    assert config["aspectRatioTolerance"] == media_assets.DEFAULT_TOLERANCE
    assert media_assets.gallery_config("pexels", per_page=None)["name"] == "pexels"
    with pytest.raises(M2VError, match="未知图库"):
        media_assets.gallery_config("unsplash")
    with pytest.raises(M2VError, match="未知图库"):
        build({"name": "unsplash"})


def test_cli_import_and_search(tmp_path, capsys, monkeypatch):
    root = tmp_path / "video"
    (root / "assets").mkdir(parents=True)
    make_image(root / "assets/wide.png")
    (root / "project.json").write_text(json.dumps(
        {"schemaVersion": 1, "id": "demo", "type": "article-narrative",
         "materials": {"storyboard": "storyboard.json"},
         "output": {"width": 1080, "height": 1920, "fps": 30, "audio": "optional"}}), encoding="utf-8")
    (root / "storyboard.json").write_text(json.dumps(board(), ensure_ascii=False), encoding="utf-8")
    manifest = tmp_path / "import.json"
    manifest.write_text(json.dumps({"schemaVersion": 1, "assets": [
        entry("wide", "image", localPath="assets/wide.png", author="作者", license="CC0")]}), encoding="utf-8")
    assert media_assets.main(["import", "--project", str(root), "--manifest", str(manifest)]) == 0
    assert "已导入素材 1 项" in capsys.readouterr().out
    monkeypatch.setenv("M2V_PEXELS_API_KEY", "test-key")
    monkeypatch.setattr(media_assets, "build_gallery",
                        lambda config, transport=None, **kw: build(config, FakeGallery(videos=[PEXELS_VIDEO])))
    assert media_assets.main(["search", "--project", str(root), "--kind", "video"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["kind"] == "video"
    assert printed["queries"][0]["candidates"][0]["description"] == "竖屏空镜"
    assert media_assets.main(["search", "--project", str(root), "--provider", "unsplash"]) == 1
    assert "未知图库" in capsys.readouterr().err
    assert media_assets.main(["import", "--project", str(root)]) == 1
    assert "--manifest" in capsys.readouterr().err
