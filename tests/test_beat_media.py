"""有声准备与媒体清单的节拍解析：真实词边界 → 场景内帧区间。

覆盖 openspec 变更 add-narration-synced-visual-beats 的任务 2.1 与 2.2：
中文标点、长句、重复短语与场景延长下的解析结果，以及清单读写的兼容与失败口径。
"""

from __future__ import annotations

import copy
import json
import re
import wave
from pathlib import Path

import pytest

from a2v import beats, media as media_mod, prepare as prep, storyboard as sb
from a2v.errors import A2VError
from a2v.media import load_media
from test_beats import beat_script


def tone(path: Path, duration: float = 2.0) -> None:
    import math
    import struct

    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        samples = (
            int(2000 * math.sin(2 * math.pi * 440 * n / 24000))
            for n in range(round(duration * 24000))
        )
        stream.writeframes(b"".join(struct.pack("<h", n) for n in samples))


@pytest.fixture
def speech(monkeypatch):
    """按字生成词边界：每字 0.12s、字间 0.02s、尾部 0.2s，可复现。"""
    calls: list[str] = []

    def install(per_char: float = 0.12, gap: float = 0.02, tail: float = 0.2) -> list[str]:
        async def fake(text, voice, rate, output):
            calls.append(text)
            tokens = re.findall(r"[\w\u4e00-\u9fff]", text)
            words, cursor = [], 0.1
            for token in tokens:
                words.append({"text": token, "start": cursor, "end": cursor + per_char})
                cursor += per_char + gap
            tone(Path(output), cursor + tail)
            return words

        monkeypatch.setattr(prep, "synthesize", fake)
        return calls

    return install


def write(tmp_path: Path, script: dict) -> Path:
    path = tmp_path / "storyboard.json"
    path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
    return path


def prepare(tmp_path: Path, script: dict) -> tuple[Path, Path]:
    source = write(tmp_path, script)
    return source, prep.prepare(source, tmp_path / "media")


def test_segments_resolve_to_monotonic_scene_frames(tmp_path, speech):
    speech()
    source, manifest = prepare(tmp_path, beat_script())
    media = load_media(manifest, source)
    resolved = media.data["scenes"][0]["resolvedBeats"]
    assert [item["id"] for item in resolved] == ["b1", "b2"]
    # 替身从 0.1s 开始给词边界：起点向下取整，因此是第 3 帧
    assert resolved[0]["startFrame"] == 3
    assert resolved[0]["endFrame"] == resolved[1]["startFrame"]
    assert resolved[1]["endFrame"] <= media.data["scenes"][0]["durationInFrames"]
    # 第一段更短，拿到的帧数也更少
    assert resolved[0]["endFrame"] - resolved[0]["startFrame"] < resolved[1]["endFrame"] - resolved[1]["startFrame"]
    # 画面时间轴（有效分镜）与清单同源
    timeline = media.storyboard.scenes[0].beat_timeline
    assert timeline.estimated is False
    assert [item.to_json() for item in timeline.beats] == resolved


def test_chinese_punctuation_is_restored_without_shifting_boundaries(tmp_path, speech):
    speech()
    script = beat_script()
    scene = script["scenes"][0]
    scene["narrationSegments"] = [
        {"id": "n1", "text": "先看基线；", "beatId": "b1"},
        {"id": "n2", "text": "再看累积到临界点！", "beatId": "b2"},
    ]
    source, manifest = prepare(tmp_path, script)
    media = load_media(manifest, source)
    assert [cue["text"] for cue in media.data["cues"]] == ["先看基线；", "再看累积到临界点！"]
    resolved = media.data["scenes"][0]["resolvedBeats"]
    assert resolved[0]["endFrame"] == resolved[1]["startFrame"]


def test_repeated_phrase_maps_to_its_own_segment(tmp_path, speech):
    speech()
    script = beat_script()
    scene = script["scenes"][0]
    # 两段包含同一个短语：必须按原文顺序各归各段，而不是都映射到前一处
    scene["narrationSegments"] = [
        {"id": "n1", "text": "先看基线。", "beatId": "b1"},
        {"id": "n2", "text": "先看基线，再看累积。", "beatId": "b2"},
    ]
    source, manifest = prepare(tmp_path, script)
    media = load_media(manifest, source)
    resolved = media.data["scenes"][0]["resolvedBeats"]
    assert resolved[0]["endFrame"] - resolved[0]["startFrame"] < resolved[1]["endFrame"] - resolved[1]["startFrame"]


def test_long_sentence_is_split_across_frames(tmp_path, speech):
    speech()
    script = beat_script()
    scene = script["scenes"][0]
    long_text = "这是一句明显超过二十八个字的口播内容用来验证长句仍然按词边界逐段解析成帧区间"
    scene["narrationSegments"] = [
        {"id": "n1", "text": "先看基线。", "beatId": "b1"},
        {"id": "n2", "text": long_text, "beatId": "b2"},
    ]
    source, manifest = prepare(tmp_path, script)
    media = load_media(manifest, source)
    assert media.data["scenes"][0]["durationInFrames"] > scene["durationInFrames"]
    resolved = media.data["scenes"][0]["resolvedBeats"]
    assert resolved[1]["endFrame"] <= media.data["scenes"][0]["durationInFrames"]


def test_scene_extension_keeps_beats_inside_the_scene(tmp_path, speech):
    speech(per_char=0.5, gap=0.05)
    script = beat_script()
    source, manifest = prepare(tmp_path, script)
    media = load_media(manifest, source)
    frames = media.data["scenes"][0]["durationInFrames"]
    assert frames > script["scenes"][0]["durationInFrames"]
    assert media.storyboard.scenes[0].duration_in_frames == frames
    for item in media.data["scenes"][0]["resolvedBeats"]:
        assert item["endFrame"] <= frames


def test_segment_without_word_boundaries_fails(tmp_path, speech):
    speech()
    script = beat_script()
    script["scenes"][0]["narrationSegments"] = [
        {"id": "n1", "text": "先看基线。", "beatId": "b1"},
        {"id": "n2", "text": "。。。", "beatId": "b2"},
    ]
    source = write(tmp_path, script)
    with pytest.raises(A2VError, match="没有对应的词边界"):
        prep.prepare(source, tmp_path / "media")


def test_incomplete_text_coverage_fails(tmp_path, monkeypatch):
    async def partial(text, voice, rate, output):
        tone(Path(output), 2.0)
        tokens = re.findall(r"[\w\u4e00-\u9fff]", text)[:2]
        return [
            {"text": token, "start": 0.1 + index * 0.2, "end": 0.2 + index * 0.2}
            for index, token in enumerate(tokens)
        ]

    monkeypatch.setattr(prep, "synthesize", partial)
    source = write(tmp_path, beat_script())
    with pytest.raises(A2VError, match="未覆盖完整口播"):
        prep.prepare(source, tmp_path / "media")


def test_manifest_records_version_two(tmp_path, speech):
    speech()
    _, manifest = prepare(tmp_path, beat_script())
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    assert data["version"] == media_mod.MANIFEST_VERSION == 3
    assert all("resolvedBeats" in scene for scene in data["scenes"])


def test_v3_string_narration_is_rejected_before_speech(tmp_path):
    script = beat_script()
    scene = script["scenes"][0]
    for key in ("beats", "narrationSegments"):
        scene.pop(key)
    scene["narration"] = "整段口播。"
    source = write(tmp_path, script)
    with pytest.raises(A2VError, match="v3 不接受字符串 narration"):
        prep.prepare(source, tmp_path / "media")


def test_legacy_manifest_with_segments_asks_for_prepare_again(tmp_path, speech):
    speech()
    source, manifest = prepare(tmp_path, beat_script())
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    data["version"] = 1
    Path(manifest).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(A2VError, match="重新 prepare"):
        load_media(manifest, source)


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda beats_list: beats_list[1].update(startFrame=beats_list[0]["endFrame"] - 5), "倒退或重叠"),
        (lambda beats_list: beats_list[1].update(endFrame=100000), "超出场景"),
        (lambda beats_list: beats_list[1].update(endFrame=beats_list[1]["startFrame"]), "帧区间为空"),
        (lambda beats_list: beats_list[1].update(action="wiggle"), "未知语义动作"),
        (lambda beats_list: beats_list[0].update(meaning="  "), "meaning 不能为空"),
        (lambda beats_list: beats_list.pop(), "没有解析出帧区间"),
    ],
)
def test_invalid_resolved_beats_are_rejected(tmp_path, speech, mutate, expected):
    speech()
    source, manifest = prepare(tmp_path, beat_script())
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    mutate(data["scenes"][0]["resolvedBeats"])
    Path(manifest).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(A2VError, match=expected):
        load_media(manifest, source)


def test_resolved_beats_must_match_source_declaration(tmp_path, speech):
    speech()
    source, manifest = prepare(tmp_path, beat_script())
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    data["scenes"][0]["resolvedBeats"][0]["targets"] = ["arrow"]
    Path(manifest).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(A2VError, match="与源分镜声明不一致"):
        load_media(manifest, source)


def test_resolved_beats_are_required_for_segmented_scenes(tmp_path, speech):
    speech()
    source, manifest = prepare(tmp_path, beat_script())
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    data["scenes"][0]["resolvedBeats"] = []
    Path(manifest).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(A2VError, match="必须有已解析的节拍区间"):
        load_media(manifest, source)


def test_effective_storyboard_carries_resolved_beats(tmp_path, speech):
    speech()
    source, manifest = prepare(tmp_path, beat_script())
    media = load_media(manifest, source)
    effective = media_mod.effective_storyboard(media)
    assert effective["scenes"][0]["resolvedBeats"] == media.data["scenes"][0]["resolvedBeats"]
    written = media_mod.write_effective_storyboard(media)
    on_disk = json.loads(written.read_text(encoding="utf-8"))
    assert on_disk["scenes"][0]["resolvedBeats"] == media.data["scenes"][0]["resolvedBeats"]
    # 源分镜不被改写
    assert "resolvedBeats" not in json.loads(source.read_text(encoding="utf-8"))["scenes"][0]


def test_beat_timeline_agrees_with_subtitle_cues(tmp_path, speech):
    """字幕 cue、音轨时长与 beat 边界必须落在同一条时间轴上。"""
    speech()
    source, manifest = prepare(tmp_path, beat_script())
    media = load_media(manifest, source)
    scene = media.storyboard.scenes[0]
    fps = media.storyboard.fps
    assert media.storyboard.total_frames / fps == pytest.approx(
        __import__("a2v.audio", fromlist=["wav_duration"]).wav_duration(media.audio),
        abs=1 / 24000,
    )
    for cue in media.data["cues"]:
        assert 0 <= cue["start"] < cue["end"] <= media.storyboard.total_frames / fps
    last = scene.beat_timeline.beats[-1]
    # 结尾留出稳定阅读时间：A5 闸门量的就是这段余量
    assert scene.duration_in_frames - last.end_frame >= 1


def test_effective_storyboard_aligns_cues_beats_and_scene_offsets(tmp_path, speech):
    """字幕 cue、音轨、场景时长与动画边界必须落在同一条时间轴上（任务 2.3）。"""
    import math

    speech()
    script = beat_script()
    script["scenes"].append({
        "id": "closing",
        "type": "conclusion",
        "durationInFrames": 60,
        "data": {"text": "结论"},
        "renderer": {"kind": "tree"},
        "visualIntent": {
            "relation": "focus", "focus": "text", "composition": "full",
            "density": "sparse", "tone": "decisive", "mode": "typography",
            "claim": "结论只有一句话", "showWithoutText": "整屏一句结论，四周留白",
            "primaryObject": "居中的结论文字", "motionMeaning": "结论淡入",
        },
        "camera": {"shot": "wide", "composition": "center", "depth": "flat", "focus": "copy", "segments": [{"beatId": "b1", "kind": "hold", "focus": "copy"}, {"beatId": "b2", "kind": "settle", "focus": "copy"}]},
        "transition": {"kind": "dissolve", "meaning": "切换到结论"},
        "narrationSegments": [{"id": "cn1", "text": "最后", "beatId": "b1"}, {"id": "cn2", "text": "一句话。", "beatId": "b2"}],
        "beats": [{"id": "b1", "action": "establish", "targets": ["copy"], "meaning": "出现结论"}, {"id": "b2", "action": "transform", "targets": ["copy"], "meaning": "把结论固定下来"}],
        "sceneTree": {"id": "root", "type": "overlay", "children": [
            {"id": "copy", "type": "text", "contentRef": "data.text", "role": "headline"},
        ]},
        "motions": [],
    })
    source, manifest = prepare(tmp_path, script)
    media = load_media(manifest, source)
    fps = media.storyboard.fps
    effective = media_mod.effective_storyboard(media)

    # 两幕分段口播都携带派生时间轴
    assert "resolvedBeats" in effective["scenes"][0]
    assert "resolvedBeats" in effective["scenes"][1]
    # 场景偏移由时长累加得到，动画边界以绝对帧为准
    assert [scene.start_frame for scene in media.storyboard.scenes] == [0, 120]

    timeline = media.storyboard.scenes[0].beat_timeline
    cues = media.data["cues"]
    assert len(cues) == 3
    # 字幕 cue 与 beat 同源：同一条 cue 落在同一个 beat 里，边界只差取整的 1 帧
    for index, cue in enumerate(cues[:2]):
        start = math.floor(cue["start"] * fps)
        end = math.ceil(cue["end"] * fps)
        beat = timeline.beats[index]
        assert beat.start_frame <= (start + end) / 2 < beat.end_frame, cue["text"]
        assert abs(beat.start_frame - start) <= 1 and abs(beat.end_frame - end) <= 1, cue["text"]
    # 第二幕的字幕属于第二幕，不会映射回第一幕的 beat
    assert cues[-1]["start"] * fps >= media.storyboard.scenes[1].start_frame
    # 音轨长度与派生时间轴一致
    assert media.storyboard.total_frames / fps == pytest.approx(
        __import__("a2v.audio", fromlist=["wav_duration"]).wav_duration(media.audio),
        abs=1 / 24000,
    )


def test_proportional_and_resolved_paths_share_the_same_shape(tmp_path, speech):
    """无声估算与有声解析产出同构的 beat 时间轴，只是 estimated 不同。"""
    script = beat_script()
    estimated = beats.resolve_silent(script["scenes"][0])
    speech()
    source, manifest = prepare(tmp_path, copy.deepcopy(script))
    media = load_media(manifest, source)
    resolved = media.storyboard.scenes[0].beat_timeline
    assert estimated.estimated is True
    assert resolved.estimated is False
    assert [item.id for item in estimated.beats] == [item.id for item in resolved.beats]
    assert [item.action for item in estimated.beats] == [item.action for item in resolved.beats]
