"""准备阶段：TTS 缓存、字幕全局帧、音效与准备记录体积。"""
from __future__ import annotations

import json

import pytest

from m2v.core.project import load_current_prepared, load_project
from m2v.types.road_trip import materials, prepare as prepare_module
from road_trip_helpers import write_project, write_wav

pytestmark = pytest.mark.media


def _fake_tts(monkeypatch, tmp_path):
    wav = write_wav(tmp_path / "speech.wav", 1.0)

    def scene_audio(text, voice, rate, cache, **options):
        return wav, [{"start": 0.0, "end": 0.5, "text": text}], [], 1.0, True

    monkeypatch.setattr(prepare_module.tts, "scene_audio", scene_audio)
    monkeypatch.setattr(prepare_module.tts, "preparation",
                        lambda project, texts, **options: {
                            "backend": "edge-tts", "voice": "zh-CN-XiaoxiaoNeural",
                            "rate": "+0%", "source": "project"})


def test_prepare_writes_audio_subtitles_and_small_props(tmp_path, monkeypatch):
    _fake_tts(monkeypatch, tmp_path)
    root = write_project(tmp_path / "trip")
    project = load_project(root)[1]
    prepared = prepare_module.prepare(root, project)
    assert prepared["durationInFrames"] > 0
    assert prepared["props"]["days"][0]["steps"]
    assert prepared["subtitles"]
    assert prepared["audio"]["segments"]
    assert "data:image" not in json.dumps(prepared)
    assert (root / prepared["audio"]["segments"][0]["path"]).is_file()
    assert (root / "outputs/road-trip/ambient.wav").is_file()
    assert "file:routes/day-01.json" in prepared["inputs"]
    loaded = load_current_prepared(root, project)
    assert loaded["preparedFingerprint"] == prepared["preparedFingerprint"]
    assert materials.load_project(root)["days"][0]["id"] == "day-01"


def test_prepared_invalidates_when_narration_changes(tmp_path, monkeypatch):
    _fake_tts(monkeypatch, tmp_path)
    root = write_project(tmp_path / "trip")
    project = load_project(root)[1]
    prepare_module.prepare(root, project)
    trip = json.loads((root / "trip.json").read_text(encoding="utf-8"))
    trip["days"][0]["narration"][0]["text"] = "改过之后的旁白内容。"
    (root / "trip.json").write_text(json.dumps(trip, ensure_ascii=False), encoding="utf-8")
    from m2v.core.errors import M2VError
    with pytest.raises(M2VError, match="作品材料已变化"):
        load_current_prepared(root, project)
