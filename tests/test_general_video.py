from __future__ import annotations

import json
import hashlib
import wave
from pathlib import Path

import pytest

from m2v.core.errors import M2VError
from m2v.core.project import load_project, load_current_prepared
from m2v.types.general import adapter
from conftest import create_typed_project


def _tone(path: Path, seconds: float) -> None:
    """写一个真实可解码的 24kHz 单声道 WAV；声音测试需要合法 PCM。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        stream.writeframes(b"\0\0" * int(seconds * 24000))


def _project(tmp_path: Path, plan: dict) -> tuple[Path, dict]:
    root = tmp_path / "通用作品"
    create_typed_project(root, "general")
    manifest_path = root / "project.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["tts"] = {"voice": "zh-CN-YunxiNeural"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (root / "general-plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return load_project(root)


def test_compile_uses_one_frame_axis_and_rejects_three_way_overlap(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "a", "type": "graphic", "duration": {"frames": 60}},
        {"id": "b", "type": "graphic", "duration": {"frames": 60}, "transition": {"type": "crossfade", "frames": 12}},
        {"id": "c", "type": "graphic", "duration": {"frames": 60}, "transition": {"type": "crossfade", "frames": 12}},
    ]})
    adapter.validate(root, manifest)
    compiled = adapter._compile(adapter._plan(root, manifest))
    assert [scene["startFrame"] for scene in compiled["compiledScenes"]] == [0, 48, 96]
    assert compiled["durationInFrames"] == 156

    compiled["scenes"][1]["transition"]["frames"] = 30
    compiled["scenes"][2]["transition"]["frames"] = 30
    with pytest.raises(M2VError, match="三个场景同时重叠"):
        adapter._compile(compiled)


def test_prepare_binds_plan_and_reports_expired_when_material_changes(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "opening", "type": "graphic", "duration": {"frames": 45},
         "data": {"title": "标题"}},
    ]})
    prepared = adapter.prepare(root, manifest)
    assert prepared["durationInFrames"] == 45
    assert load_current_prepared(root, manifest)["preparedFingerprint"] == prepared["preparedFingerprint"]
    (root / "general-plan.json").write_text('{"schemaVersion":1,"scenes":[]}', encoding="utf-8")
    with pytest.raises(M2VError, match="材料已变化"):
        load_current_prepared(root, manifest)


def test_mux_audio_uses_frame_delays_and_overlap_fades(monkeypatch, tmp_path: Path) -> None:
    import m2v.types.general.adapter as general

    wav = tmp_path / "voice.wav"
    wav.write_bytes(b"wave")
    seen = {}
    def fake_run(command, **kwargs):
        seen["command"] = command
        return type("Result", (), {"returncode": 0, "stderr": ""})()
    monkeypatch.setattr(general.subprocess, "run", fake_run)
    general._mux_audio(tmp_path, tmp_path / "video.mp4", tmp_path / "out.mp4",
        [{"path": "voice.wav", "startFrame": 30, "durationInFrames": 120,
          "fadeInFrames": 12, "fadeOutFrames": 12,
          "sha256": hashlib.sha256(wav.read_bytes()).hexdigest()}], 30, 300)
    command = seen["command"]
    filters = command[command.index("-filter_complex") + 1]
    assert "adelay=1000|1000" in filters
    assert "afade=t=in" in filters and "afade=t=out" in filters


def test_code_scene_is_scanned_before_prepare(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "unsafe", "type": "code", "duration": {"frames": 30},
         "renderer": {"kind": "code", "module": "unsafe"}},
    ]})
    scenes = root / "scenes"
    scenes.mkdir()
    (scenes / "unsafe.tsx").write_text(
        "export default function Unsafe() { return fetch('https://example.invalid'); }\n",
        encoding="utf-8",
    )
    with pytest.raises(M2VError, match="网络 API"):
        adapter.validate(root, manifest)


def test_graphic_relations_and_data_are_bounded_and_referenced(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "chart", "type": "graphic", "duration": {"frames": 60}, "data": {
            "nodes": [{"id": "cause", "label": "原因"}, {"id": "effect", "label": "结果"}],
            "links": [{"from": "cause", "to": "effect", "label": "推动"}],
            "values": [{"label": "指标", "value": 12.5}],
        }},
    ]})
    adapter.validate(root, manifest)
    plan = adapter._plan(root, manifest)
    assert plan["scenes"][0]["data"]["links"][0]["to"] == "effect"

    broken = plan["scenes"][0]["data"]
    broken["links"][0]["to"] = "missing"
    with pytest.raises(M2VError, match="引用已声明节点"):
        adapter._validate_graphic_data("chart", broken)


@pytest.mark.parametrize(("field", "message"), [
    ("duration", "保留完整时间轴"),
    ("narration", "保留自身声音"),
])
def test_embedded_scene_rejects_parent_trim_or_narration(tmp_path: Path, field: str, message: str) -> None:
    scene = {"id": "embedded", "type": "article-narrative", "project": "child"}
    scene[field] = {"frames": 30} if field == "duration" else "不能覆盖片段声音"
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [scene]})
    with pytest.raises(M2VError, match=message):
        adapter._plan(root, manifest)


def test_embedded_scene_rejects_reference_cycle_and_transition_overflow(tmp_path: Path) -> None:
    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "cycle", "type": "article-narrative", "project": "."},
    ]})
    with pytest.raises(M2VError, match="project"):
        adapter._plan(root, manifest)

    root, manifest = _project(tmp_path / "overflow", {"schemaVersion": 1, "scenes": [
        {"id": "first", "type": "graphic", "duration": {"frames": 12}},
        {"id": "second", "type": "graphic", "duration": {"frames": 20},
         "transition": {"type": "crossfade", "frames": 12}},
    ]})
    with pytest.raises(M2VError, match="淡化不能超过前一场景时长"):
        adapter._plan(root, manifest)


def test_soundtrack_accepts_music_only_and_rejects_effects_and_bad_refs(tmp_path: Path) -> None:
    bed = {"sourceRef": "assets/bed.wav", "gainDb": -24, "loop": True,
           "fadeInMs": 500, "fadeOutMs": 500}
    plan = {"schemaVersion": 1, "soundtrack": {"music": bed}, "scenes": [
        {"id": "only", "type": "graphic", "duration": {"frames": 60}, "data": {"title": "标题"}},
    ]}
    root, manifest = _project(tmp_path, plan)
    adapter._plan(root, manifest)  # 音床通过校验

    bad_effect = {"sourceRef": "assets/effect.wav", "sceneId": "only", "beatId": "b1", "gainDb": -12}
    root, manifest = _project(tmp_path / "effect", {**plan, "soundtrack": {"music": bed, "effects": [bad_effect]}})
    with pytest.raises(M2VError, match="没有 beat 轴"):
        adapter._plan(root, manifest)

    for position, (broken, message) in enumerate((
        ({"sourceRef": "../secret.wav"}, "本地相对路径"),
        ({"sourceRef": "assets/bed.wav", "gainDb": 10}, "增益"),
        ({"sourceRef": "assets/bed.wav", "loop": "yes"}, "布尔值"),
        ({"sourceRef": "assets/bed.wav", "fadeInMs": 99999}, "淡入淡出"),
    )):
        root, manifest = _project(tmp_path / f"broken-{position}",
                                  {**plan, "soundtrack": {"music": broken}})
        with pytest.raises(M2VError, match=message):
            adapter._plan(root, manifest)


def test_soundtrack_music_is_ducked_into_one_master_track(tmp_path: Path, monkeypatch) -> None:
    from types import SimpleNamespace
    from m2v.engine import audio as audio_engine

    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "intro", "type": "graphic", "duration": {"frames": 45}, "data": {"title": "开场"}},
        {"id": "spoken", "type": "graphic", "narration": "一段口播。", "data": {"title": "口播"}},
    ], "soundtrack": {"music": {"sourceRef": "assets/bed.wav", "gainDb": -24, "loop": True}}})
    bed_raw = root / "assets" / "bed.wav"
    _tone(bed_raw, 1)
    cache = root / "outputs" / "audio-cache"
    cache.mkdir(parents=True, exist_ok=True)
    voice_path = cache / "voice.wav"
    _tone(voice_path, 1)

    def fake_speech(_text: str, _cache: Path, *, voice: str | None = None, rate: str | None = None,
                    rhythm: dict | None = None):
        return voice_path, [{"start": 0.0, "end": 0.5, "text": "字幕"}], [], 1.5, False

    monkeypatch.setattr(adapter.registry, "get", lambda _name: SimpleNamespace(prepare_narration=fake_speech))
    seen: dict[str, object] = {}

    def fake_mix(narration, target, duration, cues, music, effects, work):
        seen.update(duration=duration, cues=cues, music=music, effects=effects)
        (work / "audio.wav").write_bytes(b"mixed")
        return None

    def fake_concatenate(parts, _fps, target, _fades=None):
        seen["parts"] = parts
        target.write_bytes(b"voice")

    monkeypatch.setattr(audio_engine, "concatenate", fake_concatenate)
    monkeypatch.setattr(audio_engine, "normalize", lambda _s, target: target.write_bytes(b"voice"))
    monkeypatch.setattr(audio_engine, "mix", fake_mix)

    prepared = adapter.prepare(root, manifest)

    # 整片一条音轨落到起点，不再逐场景 adelay；音乐解析到真实素材并进入闪避包络。
    assert prepared["audio"]["segments"] == [{
        "sceneId": "master", "path": "outputs/audio.wav", "startFrame": 0,
        "durationInFrames": prepared["durationInFrames"], "fadeInFrames": 0, "fadeOutFrames": 0,
        "sha256": hashlib.sha256(b"mixed").hexdigest()}]
    assert (root / "outputs" / "audio.wav").read_bytes() == b"mixed"
    assert seen["music"] == (bed_raw, {"sourceRef": "assets/bed.wav", "gainDb": -24, "loop": True})
    # 拼接按全片帧边界推进：无口播场景补静音，口播场景占满到下一幕起点。
    assert seen["parts"] == [(None, 45), (voice_path, 57)]
    assert sum(length for _source, length in seen["parts"]) == prepared["durationInFrames"]
    # 闪避包络用的是全片时间：第二幕的口播从 45 帧（1.5 秒）起，不是从 0 起。
    assert seen["cues"] == [{"start": 1.5, "end": 2.0}]
    assert seen["duration"] == prepared["durationInFrames"] / 30
    assert seen["effects"] == []
    assert json.loads(prepared["inputs"]["sound"])["soundtrack"] == {
        "music": {"sourceRef": "assets/bed.wav", "gainDb": -24, "loop": True}}


def _sine(path: Path, seconds: float, frequency: float, amplitude: float = 0.6) -> None:
    """写一段真实正弦 WAV；电平断言需要非静音信号。"""
    import math
    import struct

    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(seconds * 24000)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        stream.writeframes(b"".join(
            struct.pack("<h", round(amplitude * 32767 * math.sin(2 * math.pi * frequency * index / 24000)))
            for index in range(frames)))


def test_master_track_keeps_scene_frame_boundaries_and_bed_to_the_end(tmp_path: Path, monkeypatch) -> None:
    """整片母版轨必须按帧边界对齐：口播留在自己那幕，音床铺到最后一段。"""
    from types import SimpleNamespace

    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "spoken", "type": "graphic", "narration": "一段口播。", "data": {"title": "口播"}},
        {"id": "tail", "type": "graphic", "duration": {"frames": 60}, "data": {"title": "收尾"}},
    ], "soundtrack": {"music": {"sourceRef": "assets/bed.wav", "gainDb": -20, "loop": True,
                                "fadeInMs": 100, "fadeOutMs": 300}}})
    voice_path = root / "outputs" / "audio-cache" / "voice.wav"
    _sine(voice_path, 2.0, 440.0)
    _sine(root / "assets" / "bed.wav", 0.5, 110.0, amplitude=0.4)

    def fake_speech(_text: str, _cache: Path, *, voice: str | None = None, rate: str | None = None,
                    rhythm: dict | None = None):
        return voice_path, [{"start": 0.0, "end": 2.0, "text": "字幕"}], [], 2.0, False

    monkeypatch.setattr(adapter.registry, "get", lambda _name: SimpleNamespace(prepare_narration=fake_speech))
    prepared = adapter.prepare(root, manifest)
    assert prepared["durationInFrames"] == 132  # 72 帧口播幕 + 60 帧静音幕

    with wave.open(str(root / "outputs" / "audio.wav"), "rb") as stream:
        rate = stream.getframerate()
        count = stream.getnframes()
        raw = stream.readframes(count)
    import struct

    samples = struct.unpack(f"<{count}h", raw)
    assert count == round(prepared["durationInFrames"] / 30 * rate)

    def peak(start: float, end: float) -> int:
        window = samples[round(start * rate):round(end * rate)]
        return max(abs(value) for value in window)

    speech = peak(0.2, 1.8)          # 第一幕口播：接近满幅
    quiet_tail = peak(2.6, 3.2)      # 第二幕只有音床
    ending = peak(4.25, 4.4)         # 片尾：音床仍在（正在淡出）
    assert speech > 5000
    # 音床在旁白结束后必须继续铺满：按口播时长压紧拼接时这两段都是数字静音。
    assert quiet_tail > 500
    assert quiet_tail < speech / 2
    assert ending > 0


def test_concatenate_applies_scene_fade_progress(tmp_path: Path) -> None:
    """单条母版轨的淡化要在拼接时按槽位施加，否则交叉淡化处声音硬切。"""
    import struct

    from m2v.engine import audio as audio_engine

    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    _sine(first, 1.0, 440.0)
    _sine(second, 1.0, 440.0)
    output = tmp_path / "out.wav"
    audio_engine.concatenate([(first, 30), (second, 30)], 30, output, [(0, 12), (12, 0)])

    with wave.open(str(output), "rb") as stream:
        rate = stream.getframerate()
        samples = struct.unpack(f"<{stream.getnframes()}h", stream.readframes(stream.getnframes()))

    def peak(start: float, end: float) -> int:
        return max(abs(value) for value in samples[round(start * rate):round(end * rate)])

    # 12 帧 @30fps = 0.4 秒淡化窗口，跨接缝前后各占一段。
    assert peak(0.15, 0.35) > 5000        # 槽位内部保持满幅
    assert peak(1.65, 1.85) > 5000
    assert peak(0.99, 0.9999) < 1500      # 接缝前按淡化进度收尾
    assert peak(1.0001, 1.01) < 1500      # 接缝后按淡化进度起头

    # 不给 fades 时保持逐字节原样拼接（文章与素材剪辑的既有行为）。
    plain = tmp_path / "plain.wav"
    audio_engine.concatenate([(first, 30), (second, 30)], 30, plain)
    with wave.open(str(plain), "rb") as stream:
        raw = stream.readframes(stream.getnframes())
    assert raw[:24000 * 2] == first.read_bytes()[44:44 + 24000 * 2]


def test_narration_derive_maps_subtitles_and_rejects_fixed_capacity_overflow(tmp_path: Path, monkeypatch) -> None:
    from types import SimpleNamespace

    root, manifest = _project(tmp_path, {"schemaVersion": 1, "scenes": [
        {"id": "spoken", "type": "graphic", "narration": "一段口播。", "data": {"title": "口播"}},
    ]})

    def fake_speech(_text: str, cache: Path, *, voice: str | None = None, rate: str | None = None,
                    rhythm: dict | None = None):
        wav = cache / "fake.wav"
        wav.write_bytes(b"wav")
        return wav, [{"start": 0.0, "end": 0.5, "text": "字幕"}], [], 1.5, False

    monkeypatch.setattr(adapter.registry, "get", lambda _name: SimpleNamespace(prepare_narration=fake_speech))
    prepared = adapter.prepare(root, manifest)
    assert prepared["durationInFrames"] == 57
    assert prepared["subtitles"] == [{"startFrame": 0, "endFrame": 15, "text": "字幕"}]

    fixed_root, fixed_manifest = _project(tmp_path / "fixed", {"schemaVersion": 1, "scenes": [
        {"id": "fixed", "type": "graphic", "duration": {"frames": 30},
         "narration": "口播放不下。", "data": {"title": "固定容量"}},
    ]})
    with pytest.raises(M2VError, match="超出固定帧容量"):
        adapter.prepare(fixed_root, fixed_manifest)
