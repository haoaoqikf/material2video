"""有声准备与媒体清单的节拍解析：真实词边界 → 全片累加帧区间。

入口只接受分镜 v4（任务 4.3），因此这里读写的都是 v4 语义：节拍是清单顶层的
``resolvedBeats``（带 ``stageId``，帧号落在全片累加轴上），阶段时长由真实语音派生。
只针对 v3 形状的用例（幕内 ``resolvedBeats``、v1–v3 清单兼容、v3 字符串 narration）
已删除：它们描述的行为已经不存在，v4 的清单版本与生成口径由
tests/test_prepare_v4_media.py 覆盖，旧契约的拒绝由 tests/test_v4_only_entrances.py 覆盖。

保留下来的算法层意图——分段解析成单调帧区间、中文标点还原不移动边界、
重复短语按原文顺序消费、长句跨帧、覆盖不完整必须失败、阶段延长后 beat 仍在区间内——
改用 ``m2v.subtitles.segment_windows`` / ``m2v.beats.resolve_from_windows``
与全片累加帧号表达；清单顶层 ``resolvedBeats`` 的非法形态也在这里继续覆盖。
"""

from __future__ import annotations

import json
import math
import re
import wave
from pathlib import Path

import pytest

import m2v.engine.beats as beats
import m2v.types.article.media as media_mod
import m2v.types.article.prepare as prep
import m2v.engine.subtitles as subtitles
import m2v.types.article.timeline_v4 as timeline_v4
from m2v.engine.audio import wav_duration
from m2v.core.errors import M2VError
from m2v.types.article.media import load_media

#: 与 TTS 替身、字幕解析口径一致：只有文字字符才有词边界，标点没有独立时间。
_WORD = re.compile(r"[\w\u4e00-\u9fff]")


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


def write(tmp_path: Path, script: dict) -> Path:
    path = tmp_path / "storyboard.json"
    path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
    return path


def prepare(tmp_path: Path, script: dict) -> tuple[Path, Path]:
    source = write(tmp_path, script)
    return source, prep.prepare(source, tmp_path / "media")


def words_for(text: str, *, per_char: float = 0.25, gap: float = 0.05,
              lead: float = 0.1) -> list[dict]:
    """按原文顺序为每个文字字符造词边界：标点拿不到时间，与 TTS 替身同形。"""
    cursor, words = lead, []
    for token in _WORD.findall(text):
        words.append({"text": token, "start": cursor, "end": cursor + per_char})
        cursor += per_char + gap
    return words


def windows_for(segments: list[str]) -> tuple[str, list[dict], list[tuple[float, float]]]:
    """把分段口播解析为秒区间，返回完整口播、词边界与各段窗口。"""
    text = "".join(segments)
    words = words_for(text)
    return text, words, subtitles.segment_windows(text, segments, words, words[-1]["end"] + 0.2)


def stage_of(segments: list[str], beat_ids: list[str], duration_frames: int = 400) -> dict:
    """一段只有口播与 beat 声明的 v4 stage，用来直接驱动 ``resolve_from_windows``。"""
    return {
        "id": "opening",
        "durationInFrames": duration_frames,
        "narrationSegments": [
            {"id": f"n{index + 1}", "text": text, "beatId": beat_id}
            for index, (text, beat_id) in enumerate(zip(segments, beat_ids))
        ],
        "beats": [
            {"id": beat_id, "action": "establish", "targets": ["target"], "meaning": f"第 {index + 1} 拍"}
            for index, beat_id in enumerate(dict.fromkeys(beat_ids))
        ],
    }


def stage_offsets(media) -> dict[str, tuple[int, int]]:
    """各 stage 在**全片累加帧轴**上的 ``(起点, 终点)``：与清单 stages 同源。"""
    offsets, cursor = {}, 0
    for stage in media.data["stages"]:
        offsets[stage["id"]] = (cursor, cursor + stage["durationInFrames"])
        cursor += stage["durationInFrames"]
    return offsets


def test_stage_segments_resolve_to_monotonic_global_frames(tmp_path, speech, valid_script_v4):
    source, manifest = prepare(tmp_path, valid_script_v4)
    media = load_media(manifest, source)
    resolved = media.data["resolvedBeats"]
    # 每段口播按声明顺序落到全片累加帧号上，阶段归属由 stageId 标明
    assert [(item["stageId"], item["id"]) for item in resolved] == [
        ("opening", "beat-open"), ("opening", "beat-aim"),
        ("core", "beat-adjust"), ("core", "beat-mark"),
        ("closing", "beat-settle"), ("closing", "beat-hold"),
    ]
    # 替身从 0.1s 开始给词边界：起点向下取整，因此是第 3 帧
    assert resolved[0]["startFrame"] == 3
    offsets = stage_offsets(media)
    assert media.storyboard.total_frames == sum(
        stage["durationInFrames"] for stage in media.data["stages"])
    for index, item in enumerate(resolved):
        start, end = offsets[item["stageId"]]
        assert start <= item["startFrame"] < item["endFrame"] <= end
        # 同一阶段内单调不重叠；跨阶段时全局帧号同样只能前进
        if index:
            assert resolved[index - 1]["endFrame"] <= item["startFrame"]
    opening = [item for item in resolved if item["stageId"] == "opening"]
    # 第一段更短，拿到的帧数也更少
    assert opening[0]["endFrame"] - opening[0]["startFrame"] < opening[1]["endFrame"] - opening[1]["startFrame"]
    # 画面时间轴（有效分镜）与清单同源，且不是无声估算
    timeline = timeline_v4.resolve_v4(media.data["source"], media.data)
    assert timeline.estimated is False
    assert [dict(item) for item in timeline.beats] == resolved


def test_chinese_punctuation_is_restored_without_shifting_boundaries():
    segments = ["先看基线；", "再看累积到临界点！"]
    text, words, windows = windows_for(segments)
    # 服务只回文字：标点由原文还原进字幕，但段边界仍由**词本身**决定
    cues = subtitles.cues_from_words(text, words, words[-1]["end"] + 0.2)
    assert [cue["text"] for cue in cues] == segments
    assert windows[0] == (words[0]["start"], words[3]["end"])
    assert windows[1] == (words[4]["start"], words[-1]["end"])
    timeline = beats.resolve_from_windows(stage_of(segments, ["b1", "b2"]), windows, 30, 400)
    assert timeline.estimated is False
    assert timeline.beats[0].end_frame == math.ceil(windows[0][1] * 30)
    assert timeline.beats[1].start_frame >= timeline.beats[0].end_frame


def test_repeated_phrase_maps_to_its_own_segment():
    segments = ["先看基线。", "先看基线，再看累积。"]
    _, words, windows = windows_for(segments)
    # 两段包含同一个短语：必须按原文顺序各归各段，而不是都映射到前一处
    assert windows[0] == (words[0]["start"], words[3]["end"])
    assert windows[1][0] == words[4]["start"]
    assert windows[1][1] == words[-1]["end"]
    timeline = beats.resolve_from_windows(stage_of(segments, ["b1", "b2"]), windows, 30, 400)
    assert timeline.beats[0].frames < timeline.beats[1].frames


def test_long_sentence_is_split_across_frames():
    long_text = "这是一句明显超过二十八个字的口播内容用来验证长句仍然按词边界解析成帧区间"
    segments = ["先看基线。", long_text]
    _, words, windows = windows_for(segments)
    stage = stage_of(segments, ["b1", "b2"])
    # 声明帧数装不下真实语音时直接失败，而不是把长句挤成零帧
    with pytest.raises(M2VError, match="超出场景"):
        beats.resolve_from_windows(stage, windows, 30, 120)
    timeline = beats.resolve_from_windows(stage, windows, 30, 400)
    long_beat = timeline.beats[1]
    assert long_beat.id == "b2"
    # 长句占据自己那份真实语音对应的整段帧区间，跨了很多帧
    assert long_beat.end_frame == math.ceil(windows[1][1] * 30)
    assert long_beat.frames == math.ceil(windows[1][1] * 30) - math.floor(windows[1][0] * 30)
    assert long_beat.frames > timeline.beats[0].frames
    # 超过二十八个字的句子在字幕层被切成多条 cue，但 beat 区间不被切碎
    long_words = words_for(long_text)
    long_cues = subtitles.cues_from_words(long_text, long_words, long_words[-1]["end"] + 0.2)
    assert len(long_cues) > 1
    assert all(len(cue["text"]) <= 28 for cue in long_cues)


def test_stage_extension_keeps_beats_inside_the_stage(tmp_path, speech, valid_script_v4):
    declared = 350
    for stage in valid_script_v4["stages"]:
        stage["durationInFrames"] = declared
    source, manifest = prepare(tmp_path, valid_script_v4)
    media = load_media(manifest, source)
    frames = [stage["durationInFrames"] for stage in media.data["stages"]]
    # 真实语音比声明更长：每个阶段都被拉长，而不是截断口播
    assert all(value > declared for value in frames)
    assert [stage.duration_in_frames for stage in media.storyboard.stages] == frames
    assert media.storyboard.total_frames == sum(frames)
    offsets = stage_offsets(media)
    for item in media.data["resolvedBeats"]:
        start, end = offsets[item["stageId"]]
        assert start <= item["startFrame"] < item["endFrame"] <= end
    # 源分镜不被改写：仍是声明时长
    declared_stages = json.loads(source.read_text(encoding="utf-8"))["stages"]
    assert [stage["durationInFrames"] for stage in declared_stages] == [declared] * 3


def test_segment_without_word_boundaries_fails(tmp_path, speech, valid_script_v4):
    # 第 3 段只剩标点（全片仍满足 130～170 字）：没有词边界可以对上，必须报错而不是猜时间
    valid_script_v4["stages"][0]["narrationSegments"][2]["text"] = "。。。"
    source = write(tmp_path, valid_script_v4)
    with pytest.raises(M2VError, match="没有对应的词边界"):
        prep.prepare(source, tmp_path / "media")


def test_incomplete_text_coverage_fails(tmp_path, monkeypatch, valid_script_v4):
    async def partial(text, voice, rate, output):
        tone(Path(output), 2.0)
        tokens = re.findall(r"[\w\u4e00-\u9fff]", text)[:2]
        return [
            {"text": token, "start": 0.1 + index * 0.2, "end": 0.2 + index * 0.2}
            for index, token in enumerate(tokens)
        ]

    monkeypatch.setattr(prep, "synthesize", partial)
    source = write(tmp_path, valid_script_v4)
    with pytest.raises(M2VError, match="未覆盖完整口播"):
        prep.prepare(source, tmp_path / "media")


# 已删除 test_manifest_records_version_two：幕内 resolvedBeats 与 version == 3 的断言
# 描述的是媒体契约 v3；v4 清单只记顶层 resolvedBeats + stageId，版本断言由
# tests/test_prepare_v4_media.py 覆盖。

# 已删除 test_v3_string_narration_is_rejected_before_speech：v3 的字符串 narration
# 分支已随 v3 校验器一起移除；「旧分镜只回一条诊断就停止」由
# tests/test_v4_only_entrances.py 覆盖。

# 已删除 test_legacy_manifest_with_segments_asks_for_prepare_again：v3 清单
# （scenes + 幕内 resolvedBeats）已不被读取；旧清单只回「重新 prepare」诊断，
# 该口径由 tests/test_prepare_v4_media.py 的旧清单用例覆盖。


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda items: items[1].update(startFrame=items[0]["endFrame"] - 5), "与源声明或累计时间轴不匹配"),
        (lambda items: items[1].update(endFrame=100000), "与源声明或累计时间轴不匹配"),
        (lambda items: items[1].update(endFrame=items[1]["startFrame"]), "与源声明或累计时间轴不匹配"),
        (lambda items: items[1].update(action="wiggle"), "与源声明或累计时间轴不匹配"),
        (lambda items: items[0].update(meaning="  "), "与源声明或累计时间轴不匹配"),
        (lambda items: items.pop(), "并非所有源 beat 都有全局 resolvedBeats"),
    ],
)
def test_invalid_global_resolved_beats_are_rejected(tmp_path, speech, valid_script_v4, mutate, expected):
    """v4 的节拍在清单顶层：倒退重叠、越出 stage、空区间与改动源声明都必须被拒绝。"""
    source, manifest = prepare(tmp_path, valid_script_v4)
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    mutate(data["resolvedBeats"])
    Path(manifest).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match=expected):
        load_media(manifest, source)


def test_global_resolved_beats_must_match_source_declaration(tmp_path, speech, valid_script_v4):
    source, manifest = prepare(tmp_path, valid_script_v4)
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    data["resolvedBeats"][0]["targets"] = ["arrow"]
    Path(manifest).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match="与源声明或累计时间轴不匹配"):
        load_media(manifest, source)


@pytest.mark.parametrize("missing, expected", [
    ("empty", "并非所有源 beat 都有全局 resolvedBeats"),
    ("absent", "媒体缺少全局 resolvedBeats"),
])
def test_global_resolved_beats_are_required_for_narrated_stages(
        tmp_path, speech, valid_script_v4, missing, expected):
    source, manifest = prepare(tmp_path, valid_script_v4)
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    if missing == "empty":
        data["resolvedBeats"] = []
    else:
        data.pop("resolvedBeats")
    Path(manifest).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(M2VError, match=expected):
        load_media(manifest, source)


def test_effective_storyboard_carries_global_beats_without_rewriting_the_source(
        tmp_path, speech, valid_script_v4):
    source, manifest = prepare(tmp_path, valid_script_v4)
    media = load_media(manifest, source)
    effective = media_mod.effective_storyboard(media)
    assert effective["mediaTimeline"]["resolvedBeats"] == media.data["resolvedBeats"]
    assert effective["mediaTimeline"]["stages"] == media.data["stages"]
    assert effective["subtitleCues"] == media.data["cues"]
    written = media_mod.write_effective_storyboard(media)
    on_disk = json.loads(written.read_text(encoding="utf-8"))
    assert on_disk["mediaTimeline"]["resolvedBeats"] == media.data["resolvedBeats"]
    # 源分镜不被改写：仍是声明时长，也没有派生字段
    original = json.loads(source.read_text(encoding="utf-8"))
    assert original == valid_script_v4
    assert "resolvedBeats" not in original["stages"][0]
    assert "mediaTimeline" not in original


def test_beat_timeline_agrees_with_subtitle_cues(tmp_path, speech, valid_script_v4):
    """字幕 cue、音轨时长与阶段结尾的稳定阅读余量必须落在同一条时间轴上。"""
    source, manifest = prepare(tmp_path, valid_script_v4)
    media = load_media(manifest, source)
    seconds = media.storyboard.total_frames / media.storyboard.fps
    assert seconds == pytest.approx(wav_duration(media.audio), abs=1 / 24000)
    assert seconds == pytest.approx(wav_duration(manifest.parent / media.data["narration"]), abs=1 / 24000)
    standard = media.data["standardCheck"]
    assert standard["actualDurationSeconds"] == pytest.approx(seconds, abs=1 / media.storyboard.fps)
    # 148 字口播按每字 0.25 秒落在 35～45 秒
    assert standard["durationStatus"] == "pass"
    for cue in media.data["cues"]:
        assert 0 <= cue["start"] < cue["end"] <= seconds
    # 每个阶段结尾都留出稳定阅读时间：A5 闸门量的就是这段余量
    for stage in media.storyboard.stages:
        local_end = max(item["endFrame"] - stage.start_frame
                        for item in media.data["resolvedBeats"] if item["stageId"] == stage.id)
        assert stage.duration_in_frames - local_end >= 1


def test_effective_storyboard_aligns_cues_beats_and_stage_offsets(tmp_path, speech, valid_script_v4):
    """字幕 cue、beat 与阶段偏移必须落在同一条全片累加时间轴上。"""
    source, manifest = prepare(tmp_path, valid_script_v4)
    media = load_media(manifest, source)
    fps = media.storyboard.fps
    offsets = stage_offsets(media)
    # 阶段偏移由实际时长累加得到，与派生的舞台模型一致
    assert [stage.start_frame for stage in media.storyboard.stages] == [
        offsets[stage["id"]][0] for stage in media.data["stages"]]
    assert media.storyboard.total_frames == sum(
        stage["durationInFrames"] for stage in media.data["stages"])
    cues = media.data["cues"]
    assert cues
    for source_stage in media.data["source"]["stages"]:
        start, end = offsets[source_stage["id"]]
        stage_cues = [cue for cue in cues if start / fps <= cue["start"] < end / fps]
        stage_beats = [item for item in media.data["resolvedBeats"] if item["stageId"] == source_stage["id"]]
        # cue 按句与标点切开，但拼起来仍是这一阶段的完整口播
        assert "".join(cue["text"] for cue in stage_cues) == "".join(
            segment["text"] for segment in source_stage["narrationSegments"])
        # 字幕 cue 与 beat 同源：同一 beat 的首条 cue 定起点、末条 cue 定终点，边界只差取整的 1 帧
        owned: dict[str, list[dict]] = {item["id"]: [] for item in stage_beats}
        for cue in stage_cues:
            midpoint = (math.floor(cue["start"] * fps) + math.ceil(cue["end"] * fps)) / 2
            owner = next((item for item in stage_beats
                          if item["startFrame"] <= midpoint < item["endFrame"]), None)
            assert owner is not None, cue["text"]
            owned[owner["id"]].append(cue)
        for item in stage_beats:
            assert owned[item["id"]], f"beat {item['id']} 没有对应的字幕 cue"
            first = min(owned[item["id"]], key=lambda cue: cue["start"])
            last = max(owned[item["id"]], key=lambda cue: cue["end"])
            assert abs(item["startFrame"] - math.floor(first["start"] * fps)) <= 1, item["id"]
            assert abs(item["endFrame"] - math.ceil(last["end"] * fps)) <= 1, item["id"]


def test_proportional_and_resolved_paths_share_the_same_shape(tmp_path, speech, valid_script_v4):
    """无声估算与有声解析产出同构的 beat 序列，只是 estimated 不同。"""
    estimated = beats.resolve_silent(valid_script_v4["stages"][0])
    source, manifest = prepare(tmp_path, valid_script_v4)
    media = load_media(manifest, source)
    timeline = timeline_v4.resolve_v4(media.data["source"], media.data)
    opening = [item for item in timeline.beats if item["stageId"] == "opening"]
    assert estimated.estimated is True
    assert timeline.estimated is False
    assert [item.id for item in estimated.beats] == [item["id"] for item in opening]
    assert [item.action for item in estimated.beats] == [item["action"] for item in opening]
    assert [list(item.targets) for item in estimated.beats] == [item["targets"] for item in opening]
