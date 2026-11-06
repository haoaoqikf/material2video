"""交付文件的访问权限：临时目录产物落地后必须能被标准权限应用打开。

背景（Windows 实测）：``tempfile.TemporaryDirectory`` 带一份收紧的 ACL，产物 ``replace``
到最终位置会把这份 ACL 一起带走。当前账号仍能读写，但以标准权限运行的打包应用打不开，
用户双击成片时媒体播放器报 ``0x80070005 你没有访问该文件的权限``。修复的落点是
``security.deliver``：搬运与权限修复必须成对出现。这里既验证这个原语本身，也验证各交付
路径确实走了它。

注意 ``tmp_path`` 本身来自临时目录、其 ACL 也是收紧的，因此「继承所在目录权限」这件事
只能在正常目录下验证：需要真实 ACL 的用例统一用 ``normal_root``。
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from m2v.core import security
from m2v.types.scene_film import adapter, code_scenes, explainer_render, media_assets
from helpers.scene_film import fake_record, fake_tts, project
from helpers.media import entry, importer, make_image

pytestmark = pytest.mark.media

ROOT = Path(__file__).resolve().parents[2]
WINDOWS_ONLY = pytest.mark.skipif(os.name != "nt", reason="收紧 ACL 是 Windows 临时目录的行为")


@pytest.fixture
def normal_root():
    """正常目录下的作品根：父目录带常规继承权限，交付文件才可能「继承」出可用权限。"""
    base = Path.cwd() / ".cache" / f"delivery-access-{uuid4().hex}"
    base.mkdir(parents=True)
    try:
        yield base
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _fake_icacls(calls: list[tuple[str, ...]]):
    def run(*args: str):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")
    return run


def test_deliver_moves_then_resets_access_on_the_final_path(tmp_path, monkeypatch):
    """复位的是最终路径：在收紧的临时目录里复位只会再套一遍那份 ACL。"""
    staged = tmp_path / "staged.mp4"
    staged.write_bytes(b"fixture")
    destination = tmp_path / "outputs" / "video.mp4"
    destination.parent.mkdir()
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(security, "_icacls", _fake_icacls(calls))
    monkeypatch.setattr(security, "has_usable_access", lambda path: True)

    assert security.deliver(staged, destination) == destination
    assert destination.read_bytes() == b"fixture" and not staged.exists()
    assert calls == ([(str(destination), "/reset")] if os.name == "nt" else [])


def test_deliver_names_the_parent_when_access_is_still_missing(tmp_path, monkeypatch, caplog):
    """父目录本身是收紧的（例如整体搬来的临时目录）时，必须把根因直接指出来。"""
    staged = tmp_path / "staged.mp4"
    staged.write_bytes(b"fixture")
    destination = tmp_path / "outputs" / "video.mp4"
    destination.parent.mkdir()
    monkeypatch.setattr(security, "_icacls", _fake_icacls([]))
    monkeypatch.setattr(security, "has_usable_access", lambda path: False)

    with caplog.at_level(logging.WARNING, logger="m2v.core.security"):
        security.deliver(staged, destination)
    assert str(destination.parent) in caplog.text
    assert "0x80070005" in caplog.text


@WINDOWS_ONLY
def test_deliver_restores_access_for_standard_processes(normal_root):
    """真实复现：临时目录产物只 ``replace`` 落地时不是标准进程可读的，交付后必须是。"""
    with tempfile.TemporaryDirectory(dir=normal_root) as temporary:
        staged = Path(temporary) / "video.mp4"
        staged.write_bytes(b"fixture")
        assert not security.has_usable_access(staged)
        destination = normal_root / "outputs" / "video.mp4"
        destination.parent.mkdir()
        security.deliver(staged, destination)
    assert security.has_usable_access(destination)


@WINDOWS_ONLY
def test_deliver_directory_restores_nested_cache_access(normal_root):
    """整体发布缓存必须复位子目录与文件，不能只修复缓存根目录。"""
    staged = Path(tempfile.mkdtemp(dir=normal_root))
    destination = normal_root / "published-cache"
    try:
        nested = staged / "nested"
        nested.mkdir()
        (nested / "bundle.js").write_bytes(b"fixture")
        assert not security.has_usable_access(nested / "bundle.js")
        assert security.deliver_directory(staged, destination) == destination
        for path in (destination, destination / "nested", destination / "nested/bundle.js"):
            assert security.has_usable_access(path)
        assert not staged.exists()
    finally:
        shutil.rmtree(staged, ignore_errors=True)


def test_prepare_delivers_the_master_audio_with_inherited_access(normal_root, monkeypatch):
    """主音轨在临时目录里混音，落到 ``outputs/media`` 时必须交回继承权限。"""
    root, manifest = project(normal_root)
    fake_tts(monkeypatch); fake_record(monkeypatch)
    prepared = adapter.prepare(root, manifest)
    master = root / prepared["audio"]["segments"][0]["path"]
    assert master.is_file() and master.parent.name == "media"
    assert security.has_usable_access(master)


def test_render_delivers_the_video_and_provenance_with_inherited_access(normal_root, monkeypatch):
    """成片与溯源文件都从渲染临时目录搬出，两者都必须能被标准权限应用打开。"""
    root, manifest = project(normal_root)
    fake_tts(monkeypatch); fake_record(monkeypatch)
    prepared = adapter.prepare(root, manifest)

    class FakeServer:
        base_url = "http://127.0.0.1:1/"

        def __init__(self, _root, cors=False):
            self.cors = cors

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_session(**kwargs):
        render = kwargs["on_metadata"](SimpleNamespace(
            fps=60, width=1920, height=1080, duration_in_frames=prepared["durationInFrames"]))
        Path(render["out"]).write_bytes(b"silent")
        return {"readySeconds": 0.01}

    monkeypatch.setattr(explainer_render, "LocalServer", FakeServer)
    monkeypatch.setattr(explainer_render, "layout_check", lambda _root, _prepared: {"status": "pass"})
    monkeypatch.setattr(explainer_render.remotion, "web_dir", lambda: normal_root)
    monkeypatch.setattr(explainer_render.remotion, "progress_handler", lambda frames: None)
    monkeypatch.setattr(explainer_render.remotion, "bundle", lambda **kwargs: SimpleNamespace(
        path=normal_root / "bundle", build_seconds=0.0, cache_seconds=0.0,
        cache_status="hit", cache_key="test", cache_detail="test"))
    monkeypatch.setattr(explainer_render.remotion, "render_session", fake_session)
    monkeypatch.setattr(explainer_render.audio, "mux",
                        lambda silent, master, final, seconds, **kwargs: Path(final).write_bytes(b"final"))
    monkeypatch.setattr(explainer_render.output_validation, "verify_output", lambda *args, **kwargs: None)

    output = adapter.render(root, manifest)
    provenance = output.with_suffix(".provenance.json")
    assert output.is_file() and provenance.is_file()
    assert json.loads(provenance.read_text(encoding="utf-8"))["type"] == "text-motion"
    assert security.has_usable_access(output)
    assert security.has_usable_access(provenance)


def test_code_scene_encode_delivers_the_clip_through_security(tmp_path, monkeypatch):
    """代码片段缓存同样是交付文件，不能只搬运不修复。"""
    delivered: list[tuple[Path, Path]] = []
    monkeypatch.setattr(code_scenes.capture.security, "deliver",
                        lambda temporary, destination: delivered.append(
                            (Path(temporary), Path(destination))) or Path(destination))
    work = tmp_path / "work"
    work.mkdir()
    # 逐帧采集的产物是编号连续的 PNG：编码前先核对帧数与编号，缺一帧就拒绝补帧。
    for index in range(30):
        (work / f"frame-{index:06d}.png").write_bytes(b"frame")
    output = tmp_path / "outputs" / "code-cache" / "clip.mp4"

    monkeypatch.setattr(code_scenes.capture.audio, "ffmpeg",
                        lambda args: (work / "encoded.mp4").write_bytes(b"clip"))
    decoded = SimpleNamespace(returncode=0, stdout="\n".join(str(index) for index in range(30)))
    monkeypatch.setattr(code_scenes.capture, "subprocess", SimpleNamespace(run=lambda *args, **kwargs: decoded))
    code_scenes._encode(work, output, 30, 1920, 1080)
    assert delivered == [(work / "encoded.mp4", output)]


def test_code_scene_encode_rejects_missing_or_misnumbered_frames(tmp_path, monkeypatch):
    """缺帧或编号不连续时明确失败，不用重复帧补齐。"""
    from m2v.core.errors import M2VError

    monkeypatch.setattr(code_scenes.capture.audio, "ffmpeg", lambda args: None)
    for names in ([], ["frame-000000.png"], ["frame-000000.png", "frame-000002.png"]):
        work = tmp_path / ("work-" + str(len(names)))
        work.mkdir()
        for name in names:
            (work / name).write_bytes(b"frame")
        with pytest.raises(M2VError):
            code_scenes._encode(work, tmp_path / "clip.mp4", 2, 1920, 1080)


def test_media_import_delivers_adopted_media_through_security(tmp_path, monkeypatch):
    """导入素材经临时目录暂存后搬到 ``assets/media``，必须走交付原语。"""
    root, _manifest = project(tmp_path)
    make_image(root / "assets/incoming.png")
    delivered: list[tuple[Path, Path]] = []
    monkeypatch.setattr(media_assets.security, "deliver",
                        lambda temporary, destination: delivered.append(
                            (Path(temporary), Path(destination))) or Path(destination))

    record = importer(root, [entry("photo", "image", localPath="assets/incoming.png")])
    adopted = record["assets"][0]
    assert len(delivered) == 1
    staged, destination = delivered[0]
    assert destination == root / adopted["path"]
    # 交付原语被替换成记录器：文件在暂存目录里（随临时目录一并清理），
    # 摘要一致说明搬运的正是这份素材。
    assert staged.parent.name.startswith("import-") and staged.name == "photo.png"
    assert media_assets.asset_digest(root / "assets/incoming.png") == adopted["sha256"]
