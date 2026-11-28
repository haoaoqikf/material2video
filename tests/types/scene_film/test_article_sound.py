"""文章音效与母版混音：内置提示音、本地素材与时间边界。"""
from __future__ import annotations

import json
import math
import shutil
import struct
import wave
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.core.project import load_current_prepared
from m2v.engine.sound import asset_digest
from m2v.types.scene_film import explainer
from film_runtime.core.errors import VideoError
from film_runtime.types.scene_film import explainer_prepare, soundtrack
from helpers.scene_film import bind_fixture_implementation, board, fake_record, fake_tts, project, scene, scene_root



def write_tone(path: Path, seconds: float = 8, frequency: float = 220) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        out.writeframes(b"".join(
            struct.pack("<h", round(6000 * math.sin(2 * math.pi * frequency * i / 24000)))
            for i in range(round(seconds * 24000))))
    return path


def with_soundtrack(data: dict, track: dict) -> dict:
    data["soundtrack"] = track
    return data


@pytest.fixture(scope='module')
def reference_tones(tmp_path_factory):
    root = tmp_path_factory.mktemp('sound-validation')
    return (write_tone(root / 'bed.wav', .05), write_tone(root / 'click.wav', .05))


@pytest.fixture
def sound_assets(tmp_path, reference_tones):
    target = tmp_path / 'assets'
    target.mkdir()
    for source in reference_tones:
        shutil.copyfile(source, target / source.name)


def test_builtin_tones_are_deterministic_and_distinct(tmp_path):
    assert soundtrack.BUILTINS == ("ding", "ding-dong", "click", "transition")
    lengths = {}
    for name in soundtrack.BUILTINS:
        first, second = tmp_path / f"{name}-1.wav", tmp_path / f"{name}-2.wav"
        soundtrack.synthesize(name, first)
        soundtrack.synthesize(name, second)
        assert first.read_bytes() == second.read_bytes()
        with wave.open(str(first), "rb") as stream:
            assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) == (1, 2, 24000)
            lengths[name] = stream.getnframes()
        assert lengths[name] > 0
    assert len(set(lengths.values())) == len(lengths)


def test_validate_accepts_music_and_effects(tmp_path, sound_assets):
    data = with_soundtrack(board(), {
        "music": {"sourceRef": "assets/bed.wav", "gainDb": -20, "loop": True, "fadeInMs": 500, "fadeOutMs": 1200},
        "effects": [
            {"builtin": "ding-dong", "sceneId": "a", "offsetMs": 0, "gainDb": -18},
            {"sourceRef": "assets/click.wav", "sceneId": "a", "segmentId": "a-line", "offsetMs": -200},
        ]})
    explainer.validate(data, scene_root(tmp_path))


@pytest.mark.parametrize("track,match", [
    ({"music": {"gainDb": -20}}, "sourceRef"),
    ({"music": {"sourceRef": "../outside.wav"}}, "本地文件"),
    ({"music": {"sourceRef": "missing.wav"}}, "本地文件"),
    ({"music": {"sourceRef": "assets/bed.wav", "gainDb": 3}}, "gainDb"),
    ({"music": {"sourceRef": "assets/bed.wav", "loop": "yes"}}, "loop"),
    ({"music": {"sourceRef": "assets/bed.wav", "fadeInMs": 1.5}}, "fadeInMs"),
    ({"music": {"sourceRef": "assets/bed.wav", "fadeOutMs": 70000}}, "fadeOutMs"),
    ({"effects": {"builtin": "ding"}}, "最多 128 项"),
    ({"effects": [{"builtin": "ding", "sourceRef": "assets/click.wav", "sceneId": "a"}]}, "二选一"),
    ({"effects": [{"sceneId": "a"}]}, "二选一"),
    ({"effects": [{"builtin": "boom", "sceneId": "a"}]}, "未知内置音效"),
    ({"effects": [{"builtin": "ding", "sceneId": "zzz"}]}, "未知 sceneId"),
    ({"effects": [{"builtin": "ding", "sceneId": "a", "segmentId": "zzz"}]}, "未知 segmentId"),
    ({"effects": [{"builtin": "ding", "sceneId": "a", "offsetMs": 60001}]}, "offsetMs"),
    ({"effects": [{"builtin": "ding", "sceneId": "a", "offsetMs": 1.5}]}, "offsetMs"),
    ({"effects": [{"builtin": "ding", "sceneId": "a", "gainDb": 2}]}, "gainDb"),
    ({"effects": [{"sourceRef": "missing.wav", "sceneId": "a"}]}, "本地文件"),
    ({"music": {"sourceRef": "assets/bed.wav"}, "extra": 1}, "未知字段"),
])
def test_validate_rejects_invalid_soundtrack(tmp_path, sound_assets, track, match):
    with pytest.raises(M2VError, match=match):
        explainer.validate(with_soundtrack(board(), track), scene_root(tmp_path))


@pytest.mark.media
def test_prepare_mixes_builtin_and_local_effects(tmp_path, monkeypatch):
    root, manifest = project(tmp_path)
    bed = write_tone(root / "assets/bed.wav", 8)
    click = write_tone(root / "assets/click.wav", .2, 880)
    data = with_soundtrack(board(), {
        "music": {"sourceRef": "assets/bed.wav", "gainDb": -24, "loop": True, "fadeInMs": 800, "fadeOutMs": 800},
        "effects": [
            {"builtin": "ding", "sceneId": "a", "offsetMs": 0, "gainDb": -20},
            {"sourceRef": "assets/click.wav", "sceneId": "a", "segmentId": "a-line", "offsetMs": 300},
        ]})
    (root / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    fake_tts(monkeypatch)
    fake_record(monkeypatch)
    bind_fixture_implementation(root, monkeypatch)
    result = explainer_prepare.prepare(root, manifest)
    master = root / result["audio"]["segments"][0]["path"]
    assert result["durationInFrames"] == 84
    # 母版严格等于全片时长：8 秒循环音床被裁到 84 帧，而不是拖长成片。
    with wave.open(str(master), "rb") as stream:
        assert stream.getnframes() == 84 * 400
    # 本地音床与音效进入版本绑定，替换素材会让准备失效。
    assert result["inputs"]["file:assets/bed.wav"] == asset_digest(bed)
    assert result["inputs"]["file:assets/click.wav"] == asset_digest(click)
    load_current_prepared(root, manifest)
    bed.write_bytes(b"changed")
    with pytest.raises(M2VError, match=r"文件已变化.*assets/bed\.wav"):
        load_current_prepared(root, manifest)


@pytest.mark.media
def test_effect_start_beyond_duration_is_rejected(tmp_path, monkeypatch):
    root, manifest = project(tmp_path)
    data = with_soundtrack(board(), {"effects": [
        {"builtin": "transition", "sceneId": "a", "offsetMs": 60000}]})
    (root / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    fake_tts(monkeypatch)
    fake_record(monkeypatch)
    with pytest.raises(VideoError, match="起点越界"):
        explainer_prepare.prepare(root, manifest)


@pytest.mark.media
def test_effect_offset_must_land_inside_the_clip(tmp_path, monkeypatch):
    """负偏移可以把音效提前到幕首之前，但不能越过全片起点。"""
    root, manifest = project(tmp_path)
    data = board()
    data["scenes"].append(scene("b", transition="fade"))
    with_soundtrack(data, {"effects": [{"builtin": "click", "sceneId": "b", "offsetMs": -8000}]})
    (root / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    fake_tts(monkeypatch)
    fake_record(monkeypatch)
    # 第二幕起点 68 帧 ≈ 1.13 秒，提前 8 秒会落到全片之外。
    with pytest.raises(VideoError, match="起点越界"):
        explainer_prepare.prepare(root, manifest)


@pytest.mark.media
def test_soundtrack_without_music_normalizes_narration(tmp_path, monkeypatch):
    root, manifest = project(tmp_path)
    data = with_soundtrack(board(), {"effects": [{"builtin": "ding-dong", "sceneId": "a"}]})
    (root / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    fake_tts(monkeypatch)
    fake_record(monkeypatch)
    result = explainer_prepare.prepare(root, manifest)
    master = root / result["audio"]["segments"][0]["path"]
    with wave.open(str(master), "rb") as stream:
        assert stream.getnframes() == result["durationInFrames"] * 400
