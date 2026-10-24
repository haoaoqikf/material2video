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
from m2v.types.general import adapter, media_assets
from _helpers import board, fake_record, fake_tts, project, scene_root

ROOT = Path(__file__).resolve().parents[1]
PIXABAY_VIDEO = {
    "id": 77, "duration": 6, "pageURL": "https://pixabay.com/videos/77/",
    "tags": "竖屏空镜", "user": "示例作者",
    "videos": {
        "small": {"url": "https://cdn.example/77-sd.mp4", "width": 720, "height": 1280},
        "large": {"url": "https://cdn.example/77-hd.mp4", "width": 1080, "height": 1920},
    },
}
PIXABAY_PHOTO = {
    "id": 88, "imageWidth": 1080, "imageHeight": 1920,
    "pageURL": "https://pixabay.com/photos/88/", "tags": "竖屏照片",
    "user": "示例摄影师", "largeImageURL": "https://cdn.example/88.jpg",
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


def test_import_preserves_2d_role_and_target(tmp_path):
    make_image(tmp_path / "archive.png")
    result = importer(tmp_path, [{"id": "archive", "kind": "image", "localPath": "archive.png",
                                 "role": "other", "target": "flight", "license": "Public domain"}])
    assert result["assets"][0]["role"] == "other"
    assert result["assets"][0]["target"] == "flight"
    with pytest.raises(M2VError, match="role"):
        importer(tmp_path, [{"id": "bad", "kind": "image", "localPath": "archive.png", "role": "typo"}])


def test_resolve_rejects_tampered_role_and_target(tmp_path):
    """手改或旧工具写入的非法 role/target 不能绕过审计与准备。"""
    make_image(tmp_path / "archive.png")
    importer(tmp_path, [{"id": "archive", "kind": "image", "localPath": "archive.png",
                         "role": "other", "license": "CC0"}])
    record = tmp_path / "assets/media-sources.json"
    original = json.loads(record.read_text(encoding="utf-8"))
    for mutate, message in ((lambda item: item.update(role="photo"), "role"),
                            (lambda item: item.update(target="bad target!"), "target")):
        data = json.loads(json.dumps(original))
        mutate(data["assets"][0])
        record.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with pytest.raises(M2VError, match=message):
            media_assets.resolve(tmp_path)


def entry(identity, kind, **extra):
    return {"id": identity, "kind": kind, **extra}


def board_with_keywords():
    """主题式检索需要逐幕关键词；图库用例统一走竖屏画幅。"""
    data = board(width=1080, height=1920)
    data["scenes"][0]["keywords"] = ["反馈"]
    return data


class FakeGallery:
    """本机假图库：检索与下载都不出网。"""

    def __init__(self, videos=None, photos=None, blob=b"media-bytes"):
        self.videos, self.photos, self.blob = videos or [], photos or [], blob
        self.urls: list[str] = []

    def get_json(self, url, headers, timeout_s):
        self.urls.append(url)
        return {"hits": self.videos if "/videos/" in url else self.photos}

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
    """登记项要同时对上文件摘要与实测尺寸；替换文件即失败。"""
    make_image(workspace / "assets/wide.png")
    record = importer(workspace, [entry("wide", "image", localPath="assets/wide.png", license="CC0")])
    file = workspace / record["assets"][0]["path"]
    resolved = media_assets.resolve(workspace)
    assert resolved["media"]["wide"] == {"src": "/media/" + file.name, "kind": "image",
                                        "width": 864, "height": 700, "durationSeconds": None,
                                        "colorSpace": "srgb", "alpha": False, "license": "CC0"}
    make_image(file, "1080x1920")
    with pytest.raises(M2VError, match="与来源记录不符"):
        media_assets.resolve(workspace)


def test_resolve_reports_missing_file_and_escaped_path(workspace):
    make_image(workspace / "assets/wide.png")
    record = importer(workspace, [entry("wide", "image", localPath="assets/wide.png", license="CC0")])
    (workspace / record["assets"][0]["path"]).unlink()
    with pytest.raises(M2VError, match="已导入文件"):
        media_assets.resolve(workspace)
    # 记录被改成指向 assets/media 之外：解析必须拒绝，而不是把作品里的任意文件挂成媒体。
    (workspace / "article.md").write_text("x", encoding="utf-8")
    (workspace / "assets/media-sources.json").write_text(json.dumps({"schemaVersion": 1, "assets": [
        {"id": "wide", "kind": "image", "path": "article.md", "sha256": "x", "width": 1, "height": 1,
         "durationSeconds": None, "license": "CC0"}]}), encoding="utf-8")
    with pytest.raises(M2VError, match="已导入文件"):
        media_assets.resolve(workspace)


def test_unknown_license_blocks_every_registered_media(workspace):
    """统一契约：任何登记媒体的许可未知都阻断，而不只是 hero 资产。"""
    make_image(workspace / "assets/wide.png")
    importer(workspace, [entry("wide", "image", localPath="assets/wide.png", license="未知")])
    with pytest.raises(M2VError, match="许可未知"):
        media_assets.resolve(workspace)


def test_media_ratio_is_not_constrained(workspace):
    """素材比例不受画幅限制：横图、方图与横视频都进同一个只读映射。"""
    make_image(workspace / "assets/wide.png", "864x700")
    make_video(workspace / "assets/clip.mp4", seconds=2, size="1920x1080")
    importer(workspace, [entry("wide", "image", localPath="assets/wide.png", license="CC0"),
                         entry("clip", "video", localPath="assets/clip.mp4", license="CC0")])
    resolved = media_assets.resolve(workspace)["media"]
    assert set(resolved) == {"wide", "clip"}
    assert resolved["wide"]["kind"] == "image" and resolved["wide"]["durationSeconds"] is None
    assert resolved["clip"]["kind"] == "video"
    assert resolved["clip"]["width"] == 1920 and resolved["clip"]["height"] == 1080
    assert resolved["clip"]["durationSeconds"] == pytest.approx(2, abs=.1)
    assert resolved["clip"]["src"].startswith("/media/") and resolved["clip"]["src"].endswith(".mp4")


def test_unregistered_media_never_enters_the_mapping(tmp_path, monkeypatch):
    """assets/media 下的散文件不算素材：没有留证就没有 ID 可用。"""
    root, manifest = project(tmp_path)
    (root / "assets/media").mkdir(parents=True)
    make_image(root / "assets/media/orphan.png", "1080x1920")
    assert media_assets.resolve(root)["media"] == {}
    fake_tts(monkeypatch); fake_record(monkeypatch)
    adapter.prepare(root, manifest)
    prepared = json.loads((root / "outputs/prepared.json").read_text(encoding="utf-8"))
    assert prepared["inputs"]["codeMedia"] == media_assets.resolve(root)["digest"]


def test_media_change_invalidates_preparation(tmp_path, monkeypatch):
    from m2v.core.project import load_current_prepared
    root, manifest = project(tmp_path)
    make_image(root / "assets/wide.png")
    importer(root, [entry("wide", "image", localPath="assets/wide.png", license="CC0")])
    fake_tts(monkeypatch); fake_record(monkeypatch)
    adapter.prepare(root, manifest)
    next((root / "assets/media").glob("*.png")).write_bytes(b"changed")
    with pytest.raises(M2VError, match="已变化"):
        load_current_prepared(root, manifest)


def test_gallery_search_uses_scene_keywords(tmp_path, monkeypatch):
    root, manifest = project(tmp_path, board_with_keywords())
    monkeypatch.setenv("M2V_PIXABAY_API_KEY", "test-key")
    gallery = FakeGallery(videos=[PIXABAY_VIDEO], photos=[PIXABAY_PHOTO])
    result = media_assets.search(root, manifest, transport=gallery)
    assert result["provider"] == "pixabay" and result["kind"] == "both" and result["schemaVersion"] == 1
    query = result["queries"][0]
    assert query["sceneId"] == "a" and query["query"] == "反馈"
    kinds = {item["kind"] for item in query["candidates"]}
    assert kinds == {"video", "photo"}
    video = next(item for item in query["candidates"] if item["kind"] == "video")
    # 竖屏画幅按方向与目标高度挑变体：选中 1080×1920，而不是 720×1280。
    assert video["width"] == 1080 and video["height"] == 1920 and video["durationSeconds"] == 6
    assert video["license"].startswith("Pixabay Content License")
    assert all("download_url" not in item for item in query["candidates"])
    # 检索结果只是候选，不写作品文件。
    assert not (root / "assets").exists()


def test_gallery_search_without_candidates_is_not_a_failure(tmp_path, monkeypatch):
    root, manifest = project(tmp_path, board_with_keywords())
    monkeypatch.setenv("M2V_PIXABAY_API_KEY", "test-key")
    result = media_assets.search(root, manifest, transport=FakeGallery(), kind="photo")
    assert result["queries"][0]["candidates"] == []


def test_gallery_search_argument_errors(tmp_path, monkeypatch):
    root, manifest = project(tmp_path, board_with_keywords())
    monkeypatch.setenv("M2V_PIXABAY_API_KEY", "test-key")
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
    monkeypatch.delenv("M2V_PIXABAY_API_KEY")
    with pytest.raises(M2VError, match="M2V_PIXABAY_API_KEY"):
        media_assets.search(root, manifest, transport=gallery)


def test_gallery_config_follows_the_frame_orientation():
    portrait = media_assets.gallery_config("pixabay", (1080, 1920))
    landscape = media_assets.gallery_config("pixabay", (1920, 1080))
    # 比例不再约束候选：裁切与摆位由作品代码决定。
    assert portrait["orientation"] == "portrait" and portrait["aspectRatio"] == "any"
    assert landscape["orientation"] == "landscape" and landscape["aspectRatio"] == "any"
    assert media_assets.gallery_config("pixabay", (1920, 1080), per_page=None)["name"] == "pixabay"
    with pytest.raises(M2VError, match="未知图库"):
        media_assets.gallery_config("unsplash", (1920, 1080))
    with pytest.raises(M2VError, match="未知图库"):
        build({"name": "unsplash"})


def test_cli_import_and_search(tmp_path, capsys, monkeypatch):
    root = tmp_path / "video"
    (root / "assets").mkdir(parents=True)
    make_image(root / "assets/wide.png")
    (root / "project.json").write_text(json.dumps(
        {"schemaVersion": 1, "id": "demo", "type": "general",
         "materials": {"storyboard": "storyboard.json"},
         "output": {"width": 1920, "height": 1080, "fps": 60, "audio": "optional"}}), encoding="utf-8")
    (root / "storyboard.json").write_text(json.dumps(board_with_keywords(), ensure_ascii=False), encoding="utf-8")
    scene_root(root)
    manifest = tmp_path / "import.json"
    manifest.write_text(json.dumps({"schemaVersion": 1, "assets": [
        entry("wide", "image", localPath="assets/wide.png", author="作者", license="CC0")]}), encoding="utf-8")
    assert media_assets.main(["import", "--project", str(root), "--manifest", str(manifest)]) == 0
    assert "已导入素材 1 项" in capsys.readouterr().out
    monkeypatch.setenv("M2V_PIXABAY_API_KEY", "test-key")
    monkeypatch.setattr(media_assets, "build_gallery",
                        lambda config, transport=None, **kw: build(config, FakeGallery(videos=[PIXABAY_VIDEO])))
    assert media_assets.main(["search", "--project", str(root), "--kind", "video"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["kind"] == "video" and printed["provider"] == "pixabay"
    assert media_assets.main(["search", "--project", str(root), "--provider", "pexels"]) == 1
    assert "Pexels 已停用" in capsys.readouterr().err
    assert printed["queries"][0]["candidates"][0]["description"] == "竖屏空镜"
    assert media_assets.main(["search", "--project", str(root), "--provider", "unsplash"]) == 1
    assert "未知图库" in capsys.readouterr().err
    assert media_assets.main(["import", "--project", str(root)]) == 1
    assert "--manifest" in capsys.readouterr().err


@pytest.mark.parametrize("has_key", [False, True])
def test_pexels_stays_disabled(tmp_path, monkeypatch, has_key):
    root, manifest = project(tmp_path, board_with_keywords())
    if has_key:
        monkeypatch.setenv("M2V_PEXELS_API_KEY", "unused-test-key")
    else:
        monkeypatch.delenv("M2V_PEXELS_API_KEY", raising=False)
    gallery = FakeGallery()
    with pytest.raises(M2VError, match="Pexels 已停用.*Pixabay"):
        media_assets.search(root, manifest, provider_name="pexels", transport=gallery)
    assert gallery.urls == []
    assert not (root / "outputs/gallery-cache").exists()


def test_explicit_pixabay_search(tmp_path, monkeypatch):
    root, manifest = project(tmp_path, board_with_keywords())
    monkeypatch.setenv("M2V_PIXABAY_API_KEY", "test-key")
    gallery = FakeGallery(videos=[PIXABAY_VIDEO])
    result = media_assets.search(root, manifest, provider_name="pixabay", kind="video", transport=gallery)
    assert result["provider"] == "pixabay"
    assert result["queries"][0]["candidates"]
    assert all(url.startswith("https://pixabay.com/api/") for url in gallery.urls)
