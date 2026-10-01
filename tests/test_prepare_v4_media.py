import copy
import json
import wave
from pathlib import Path

from a2v import media as media_mod, prepare as prepare_mod
from a2v.timeline_v4 import resolve_v4


def _two_stage_storyboard():
    fixture = json.loads((Path(__file__).parent / "fixtures" / "storyboard-v4-vectors.json").read_text(encoding="utf-8"))
    source = copy.deepcopy(fixture["valid"])
    first = source["stages"][0]
    text = first["narrationSegments"][0]["text"]
    first["durationInFrames"] = 525
    first["narrationSegments"][0]["text"] = text[: len(text) // 2]
    second = copy.deepcopy(first)
    second.update(id="ending", durationInFrames=525)
    second["narrationSegments"][0].update(id="line-ending", text=text[len(text) // 2 :], beatId="throw-ending")
    second["beats"][0]["id"] = "throw-ending"
    source["stages"].append(second)
    return source


def test_prepare_v4_writes_ordered_global_beats_and_standard_duration(tmp_path, monkeypatch):
    source = _two_stage_storyboard()
    storyboard = tmp_path / "storyboard.json"
    storyboard.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    cache = tmp_path / "media" / "cache"

    calls = []
    def fake_scene_audio(text, voice, rate, directory, force, *, contract_version):
        calls.append(contract_version)
        path = directory / f"stage-{len(calls)}.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"mock audio")
        return path, [{"start": 0, "end": 15, "text": "口播"}], [], 16.0, False

    monkeypatch.setattr(prepare_mod, "_scene_audio", fake_scene_audio)
    monkeypatch.setattr(prepare_mod, "segment_windows", lambda text, segments, words, duration: [(0.0, duration)])
    monkeypatch.setattr(prepare_mod.audio, "concatenate", lambda parts, fps, target: target.write_bytes(b"wav"))
    monkeypatch.setattr(prepare_mod.audio, "mix", lambda narration, target, duration, cues, music, effects, work: target.write_bytes(b"wav"))
    monkeypatch.setattr(prepare_mod.security, "grant_inherited_access", lambda path: None)

    result = prepare_mod.prepare(storyboard, tmp_path / "media")
    manifest = json.loads(result.read_text(encoding="utf-8"))
    assert calls == [4, 4]
    assert manifest["version"] == 4
    assert [(stage["id"], stage["durationInFrames"]) for stage in manifest["stages"]] == [("opening", 525), ("ending", 525)]
    assert [(beat["stageId"], beat["id"], beat["startFrame"], beat["endFrame"]) for beat in manifest["resolvedBeats"]] == [
        ("opening", "throw-1", 0, 480), ("ending", "throw-ending", 525, 1005),
    ]
    assert manifest["standardCheck"]["actualDurationInFrames"] == 1050
    assert manifest["standardCheck"]["durationStatus"] == "pass"
    resolved = resolve_v4(source, manifest)
    assert resolved.total_frames == 1050
    assert resolved.stages[1].start_frame == 525
    assert resolved.beats[1]["startFrame"] == 525
    assert resolved.estimated is False

    for reference in (manifest["audio"], manifest["narration"]):
        with wave.open(str(result.parent / reference), "wb") as stream:
            stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            stream.writeframes(b"\0\0" * (35 * 24000))
    media = media_mod.load_media(result, storyboard)
    assert media.storyboard.total_frames == 1050
    effective = media_mod.effective_storyboard(media)
    assert effective["mediaTimeline"]["resolvedBeats"] == manifest["resolvedBeats"]
    assert effective["subtitleCues"] == manifest["cues"]


def test_v4_manifest_generation_invalidates_legacy_media_and_cache_keys_are_versioned(tmp_path):
    source = _two_stage_storyboard()
    path = tmp_path / "media.json"
    path.write_text(json.dumps({"version": 3, "source": source}), encoding="utf-8")
    try:
        media_mod.load_media(path)
    except Exception as error:
        assert "v4 分镜的媒体清单版本过旧，请重新 prepare" in str(error)
    else:
        raise AssertionError("v3 清单不得被当成 v4 媒体加载")
    assert prepare_mod._scene_cache_key("同一文本", "voice", "+0%", 3) != prepare_mod._scene_cache_key("同一文本", "voice", "+0%", 4)
