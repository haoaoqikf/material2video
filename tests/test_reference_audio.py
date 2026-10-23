"""参考音轨提取：授权、摘要留证、帧数、覆盖保护与失败清理。"""
from __future__ import annotations

import hashlib
import json
import subprocess
import wave
from pathlib import Path

import pytest
from imageio_ffmpeg import get_ffmpeg_exe

from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.core.project import create_project
from m2v.reference import audio
from m2v.types.general import explainer


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _ffmpeg(*args: str) -> None:
    result = subprocess.run([get_ffmpeg_exe(), "-y", "-v", "error", *args],
                            capture_output=True, timeout=120)
    if result.returncode:
        raise AssertionError(result.stderr.decode("utf-8", "replace"))


def make_reference(root: Path, *, with_audio: bool = True, kind: str = "video") -> Path:
    directory = root / "ref"
    directory.mkdir(parents=True)
    video = directory / "video.mp4"
    args = ["-f", "lavfi", "-i", "color=c=black:s=320x240:d=1.2"]
    if with_audio:
        args += ["-f", "lavfi", "-i", "sine=frequency=440:duration=1.2", "-shortest",
                 "-c:v", "mpeg4", "-c:a", "aac", "-ac", "2"]
    else:
        args += ["-c:v", "mpeg4", "-an"]
    _ffmpeg(*args, "-pix_fmt", "yuv420p", str(video))
    metadata = {
        "schemaVersion": 1, "awemeId": "7697224312599711026", "kind": kind,
        "desc": "测试参考作品", "author": {"uid": "1", "nickname": "Roooose"},
        "createTime": 0, "durationMs": 1200, "declaredWidth": 320, "declaredHeight": 240,
        "coverUrl": "", "sourceUrl": "https://v.douyin.com/test/",
        "finalUrl": "https://www.douyin.com/video/7697224312599711026",
        "capturedAt": "2026-10-22T20:00:00+08:00", "images": [],
    }
    (directory / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    recipe = {
        "schemaVersion": 1, "awemeId": metadata["awemeId"], "kind": kind,
        "sourceUrl": metadata["sourceUrl"], "finalUrl": metadata["finalUrl"],
        "capturedAt": metadata["capturedAt"],
        "files": [{"path": "video.mp4", "sha256": _sha(video), "bytes": video.stat().st_size,
                   "width": 320, "height": 240}],
    }
    (directory / "recipe.json").write_text(json.dumps(recipe, ensure_ascii=False), encoding="utf-8")
    return directory


def make_project(root: Path, video_type: str = "general") -> Path:
    return create_project(root / "work", video_type, {"storyboard": "storyboard.json"}).parent


def test_extract_writes_audio_and_provenance(tmp_path):
    reference = make_reference(tmp_path)
    project = make_project(tmp_path)
    result = audio.extract_audio(reference, project, statement="用户明确要求复用该作品音频")
    target = project / result["audio"]
    provenance = project / result["provenance"]
    assert target.is_file() and provenance.is_file()
    with wave.open(str(target), "rb") as stream:
        assert (stream.getframerate(), stream.getnchannels(), stream.getsampwidth()) == (48000, 2, 2)
        samples = stream.getnframes()
    assert result["audioInfo"]["samples"] == samples
    assert result["timeline"]["fps"] == 30
    assert result["timeline"]["totalFrames"] == (samples * 30 + 47999) // 48000
    assert result["audioInfo"]["framesAt60fps"] == audio.frames_at_60fps(samples)
    assert result["timeline"]["rounding"] == "ceil"
    assert result["soundtrack"]["music"] == {
        "sourceRef": result["audio"], "gainDb": 0, "loop": False, "fadeInMs": 0, "fadeOutMs": 0}
    saved = json.loads(provenance.read_text(encoding="utf-8"))
    assert saved["reference"]["videoSha256"] == _sha(reference / "video.mp4")
    assert saved["audio"]["sha256"] == _sha(target)
    assert saved["authorization"]["statement"] == "用户明确要求复用该作品音频"
    assert "不构成许可" in saved["authorization"]["licenseStatus"]
    assert saved["authorization"]["attribution"] == "抖音 @Roooose"
    assert saved["usage"]["soundtrack"]["music"]["sourceRef"] == result["audio"]


def test_second_run_reuses_identical_audio(tmp_path):
    reference = make_reference(tmp_path)
    project = make_project(tmp_path)
    first = audio.extract_audio(reference, project, statement="授权")
    before = (project / first["audio"]).stat().st_mtime_ns
    second = audio.extract_audio(reference, project, statement="授权")
    assert second["reused"] is True
    assert (project / first["audio"]).stat().st_mtime_ns == before
    assert second["audioInfo"]["sha256"] == first["audioInfo"]["sha256"]


def test_statement_is_required(tmp_path):
    reference = make_reference(tmp_path)
    project = make_project(tmp_path)
    with pytest.raises(M2VError, match="授权"):
        audio.extract_audio(reference, project, statement="   ")


def test_cli_requires_project_statement_and_rejects_fetch_flags(tmp_path):
    reference = make_reference(tmp_path)
    project = make_project(tmp_path)
    assert main(["ref", "audio", str(reference), "--user-authorized", "授权"]) == 1
    assert not (project / "assets/audio").exists()
    assert main(["ref", "audio", str(reference), "--project", str(project)]) == 1
    assert main(["ref", "audio", str(reference), "--project", str(project),
                 "--user-authorized", "授权", "--output", str(tmp_path / "out")]) == 1
    assert main(["ref", "audio", str(reference), "--project", str(project),
                 "--user-authorized", "授权"]) == 0


def test_modified_reference_is_rejected_before_extraction(tmp_path):
    reference = make_reference(tmp_path)
    project = make_project(tmp_path)
    (reference / "video.mp4").write_bytes(b"changed")
    with pytest.raises(M2VError, match="摘要或字节数不符"):
        audio.extract_audio(reference, project, statement="授权")
    assert not list((project / "assets/audio").glob("*.wav"))


def test_existing_target_requires_force(tmp_path):
    reference = make_reference(tmp_path)
    project = make_project(tmp_path)
    first = audio.extract_audio(reference, project, statement="授权")
    target = project / first["audio"]
    target.write_bytes(b"broken")
    with pytest.raises(M2VError, match="不一致"):
        audio.extract_audio(reference, project, statement="授权")
    replaced = audio.extract_audio(reference, project, statement="授权", force=True)
    assert replaced["reused"] is False
    assert target.stat().st_size == replaced["audioInfo"]["bytes"]


@pytest.mark.parametrize("name", ["../escape", "a/b", "..", "CON", "x.wav", "x.provenance.json", "", "中文", "a."])
def test_invalid_names_are_rejected(name):
    with pytest.raises(M2VError):
        audio.validate_name(name)


def test_frames_round_up():
    assert audio.frames_at_60fps(48000) == 60
    assert audio.frames_at_60fps(48001) == 61
    assert audio.frames_at_60fps(48000 * 600) == 36000
    assert audio.frames_at_60fps(48000 * 601) > 36000


def test_video_without_audio_fails_and_leaves_nothing(tmp_path):
    reference = make_reference(tmp_path, with_audio=False)
    project = make_project(tmp_path)
    with pytest.raises(M2VError, match="音频流"):
        audio.extract_audio(reference, project, statement="授权")
    audio_dir = project / "assets/audio"
    assert not list(audio_dir.glob("*"))


def test_note_reference_is_rejected(tmp_path):
    reference = make_reference(tmp_path, kind="note")
    project = make_project(tmp_path)
    with pytest.raises(M2VError, match="不是视频"):
        audio.extract_audio(reference, project, statement="授权")


def test_non_general_project_is_rejected(tmp_path):
    reference = make_reference(tmp_path)
    project = create_project(tmp_path / "financial", "financial-timeseries", {"request": "request.json"}).parent
    with pytest.raises(M2VError, match="general"):
        audio.extract_audio(reference, project, statement="授权")


def test_failed_extraction_leaves_no_partial_files(tmp_path):
    reference = make_reference(tmp_path)
    project = make_project(tmp_path)
    (reference / "video.mp4").write_bytes(b"not a video")
    recipe = json.loads((reference / "recipe.json").read_text(encoding="utf-8"))
    recipe["files"][0]["sha256"] = _sha(reference / "video.mp4")
    recipe["files"][0]["bytes"] = (reference / "video.mp4").stat().st_size
    (reference / "recipe.json").write_text(json.dumps(recipe), encoding="utf-8")
    with pytest.raises(M2VError, match="提取失败"):
        audio.extract_audio(reference, project, statement="授权")
    assert not list((project / "assets/audio").glob("*"))


def test_soundtrack_snippet_passes_storyboard_validation(tmp_path):
    reference = make_reference(tmp_path)
    project = make_project(tmp_path)
    result = audio.extract_audio(reference, project, statement="授权")
    scenes = project / "scenes"
    scenes.mkdir()
    (scenes / "opening.tsx").write_text("export default function Opening() { return null; }\n", encoding="utf-8")
    data = {
        "version": 8, "schemaVersion": 8, "fps": 60, "width": 1080, "height": 1920,
        "title": "音轨片段校验", "input": {"kind": "topic", "topic": "音轨片段校验"},
        "targetSeconds": 1, "soundtrack": result["soundtrack"],
        "scenes": [{
            "id": "a", "template": "code", "keywords": ["音轨"], "durationFrames": 60,
            "transition": "cut", "narrationSegments": [],
            "content": {"entry": "scenes/opening.tsx"},
        }],
    }
    explainer.validate(data, project)
