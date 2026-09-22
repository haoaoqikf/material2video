"""语义节拍：结构校验、引用完整性与共享求值模型。

覆盖 openspec 变更 add-narration-synced-visual-beats 的任务 1.1 与 1.2：
分段口播与 beats 的互斥/唯一性/引用校验，以及无声等比例解析与逐帧求值。
"""

from __future__ import annotations

import copy
import json
import pathlib

import pytest

from a2v import beats, storyboard


def beat_script() -> dict:
    """一幕带论证结构证据（chart + connector）的非文字幕，声明两个 beat。"""
    return {
        "version": 2,
        "schemaVersion": 2,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "visualDirection": {
            "motif": "积累",
            "compositionBias": "mixed",
            "density": "balanced",
            "rhythm": "steady",
            "avoid": [],
        },
        "scenes": [
            {
                "id": "loop",
                "type": "process",
                "durationInFrames": 120,
                "data": {"values": [{"label": "一月", "value": 3}], "note": "来源：内部统计"},
                "visualIntent": {
                    "relation": "cause",
                    "focus": "chart",
                    "composition": "center",
                    "density": "sparse",
                    "tone": "neutral",
                    "mode": "chart",
                    "claim": "投入累积到临界点才改变产出",
                    "showWithoutText": "一根柱子被逐段垫高，旁边的箭头方向不变",
                    "primaryObject": "被逐段垫高的柱子与方向箭头",
                    "motionMeaning": "柱子按 beat 逐步垫高，说明累积过程",
                },
                "sceneTree": {
                    "id": "root",
                    "type": "stack",
                    "children": [
                        {
                            "id": "chart",
                            "type": "chart",
                            "contentRef": "data.values",
                            "chart": "bar",
                            "schematic": True,
                        },
                        {"id": "arrow", "type": "connector", "direction": "ltr"},
                    ],
                },
                "motions": [],
                "beats": [
                    {"id": "b1", "action": "establish", "targets": ["chart"], "meaning": "先建立基线"},
                    {"id": "b2", "action": "accumulate", "targets": ["chart"], "meaning": "数值逐段累积"},
                ],
                "narrationSegments": [
                    {"id": "n1", "text": "先看基线。", "beatId": "b1"},
                    {"id": "n2", "text": "再看累积到临界点。", "beatId": "b2"},
                ],
            }
        ],
    }


def scene(data: dict) -> dict:
    return data["scenes"][0]


def errors(data: dict, strict: bool = False) -> list[str]:
    report = storyboard.validate(data, strict=strict)
    return [f"{issue.path}: {issue.message}" for issue in report.errors]


def warnings(data: dict) -> list[str]:
    return [f"{issue.path}: {issue.message}" for issue in storyboard.validate(data).warnings]


def messages(data: dict, strict: bool = False) -> str:
    return " | ".join(errors(data, strict))


# ---------------------------------------------------------------- 结构校验


def test_segmented_narration_is_valid():
    data = beat_script()
    assert not [item for item in errors(data) if ".beats" in item or "narrationSegments" in item]


def test_narration_and_segments_are_mutually_exclusive():
    data = beat_script()
    scene(data)["narration"] = "整段口播"
    assert "互斥" in messages(data)


def test_duplicate_beat_id_is_rejected():
    data = beat_script()
    scene(data)["beats"][1]["id"] = "b1"
    assert "重复" in messages(data)


def test_duplicate_segment_id_is_rejected():
    data = beat_script()
    scene(data)["narrationSegments"][1]["id"] = "n1"
    assert "重复" in messages(data)


def test_unknown_action_is_rejected():
    data = beat_script()
    scene(data)["beats"][1]["action"] = "wiggle"
    assert "未知语义动作" in messages(data)


def test_blank_meaning_is_rejected():
    data = beat_script()
    scene(data)["beats"][0]["meaning"] = "   "
    assert "meaning 必须是非空字符串" in messages(data)


def test_dangling_beat_reference_is_rejected():
    data = beat_script()
    scene(data)["narrationSegments"][1]["beatId"] = "missing"
    assert "悬空引用" in messages(data)


def test_orphan_beat_is_rejected():
    data = beat_script()
    scene(data)["narrationSegments"] = scene(data)["narrationSegments"][:1]
    assert "没有被任何口播段引用" in messages(data)


def test_unknown_target_is_rejected():
    data = beat_script()
    scene(data)["beats"][1]["targets"] = ["ghost"]
    assert "beat 目标 ghost 不存在" in messages(data)


def test_action_unsupported_by_target_is_rejected():
    data = beat_script()
    scene(data)["beats"][1]["targets"] = ["arrow"]  # connector 不支持 accumulate
    assert "不支持语义动作" in messages(data)


def test_empty_targets_is_rejected():
    data = beat_script()
    scene(data)["beats"][0]["targets"] = []
    assert "至少要有一个目标节点" in messages(data)


def test_non_contiguous_beat_reference_is_rejected():
    data = beat_script()
    scene(data)["beats"].append({"id": "b3", "action": "deplete", "targets": ["chart"], "meaning": "回落"})
    scene(data)["narrationSegments"] = [
        {"id": "n1", "text": "第一句。", "beatId": "b1"},
        {"id": "n2", "text": "第二句。", "beatId": "b2"},
        {"id": "n3", "text": "第三句。", "beatId": "b1"},
    ]
    assert "不连续" in messages(data)


def test_consecutive_segments_may_share_one_beat():
    data = beat_script()
    scene(data)["narrationSegments"] = [
        {"id": "n1", "text": "第一句，", "beatId": "b1"},
        {"id": "n2", "text": "还是同一拍。", "beatId": "b1"},
        {"id": "n3", "text": "第二拍。", "beatId": "b2"},
    ]
    assert not [item for item in errors(data) if "beats" in item or "narrationSegments" in item]
    model = storyboard._build(data, storyboard.Report())
    timeline = model.scenes[0].beat_timeline
    assert [item.id for item in timeline.beats] == ["b1", "b2"]


def test_derived_resolved_beats_cannot_be_authored():
    data = beat_script()
    scene(data)["resolvedBeats"] = []
    assert "派生" in messages(data)


def test_scene_too_short_for_segments_is_rejected():
    data = beat_script()
    scene(data)["durationInFrames"] = 1
    assert "装不下" in messages(data)


# ------------------------------------------------- 新作品严格规则（任务 1.3）


def test_non_text_narrated_scene_needs_beats_in_strict_mode():
    data = beat_script()
    for key in ("beats", "narrationSegments"):
        scene(data).pop(key)
    scene(data)["narration"] = "整段口播"
    assert "没有语义节拍" in messages(data, strict=True)


def test_legacy_string_narration_only_warns_in_ordinary_mode():
    data = beat_script()
    for key in ("beats", "narrationSegments"):
        scene(data).pop(key)
    scene(data)["narration"] = "整段口播"
    assert not [item for item in errors(data) if "beats" in item]
    assert any("兼容模式" in item for item in warnings(data))


def test_text_and_silent_scenes_are_exempt():
    data = beat_script()
    for key in ("beats", "narrationSegments"):
        scene(data).pop(key)
    scene(data)["visualIntent"]["mode"] = "typography"
    scene(data)["narration"] = "纯文字幕口播"
    assert "没有语义节拍" not in messages(data, strict=True)

    silent = beat_script()
    for key in ("beats", "narrationSegments"):
        scene(silent).pop(key)
    assert "没有语义节拍" not in messages(silent, strict=True)


def test_single_beat_and_neutral_only_actions_are_rejected_in_strict_mode():
    data = beat_script()
    scene(data)["beats"] = [{"id": "b1", "action": "highlight", "targets": ["chart"], "meaning": "强调"}]
    scene(data)["narrationSegments"] = [{"id": "n1", "text": "只有一句。", "beatId": "b1"}]
    detail = messages(data, strict=True)
    assert "至少需要 2 个 beat" in detail
    assert "改变对象状态或关系" in detail


def test_code_scene_beats_only_check_identifier_shape():
    data = beat_script()
    scene(data)["renderer"] = {"kind": "code", "module": "intro"}
    scene(data).pop("sceneTree")
    scene(data)["beats"][1]["targets"] = ["runtime-probe-id"]
    assert not [item for item in errors(data) if "不存在" in item]


# ------------------------------------------------------- 无声解析与求值（1.2）


def test_proportional_spans_cover_duration_exactly():
    spans = beats.proportional_spans(100, ["短。", "这是一句明显更长的口播内容。"])
    assert spans[0][0] == 0
    assert spans[-1][1] == 100
    assert all(end > start for start, end in spans)
    assert spans[1][0] == spans[0][1]


def test_proportional_spans_are_deterministic_and_keep_one_frame_each():
    texts = ["甲", "乙", "丙", "丁", "戊"]
    first = beats.proportional_spans(37, texts)
    assert first == beats.proportional_spans(37, texts)
    assert all(end - start >= 1 for start, end in first)
    assert sum(end - start for start, end in first) == 37


def test_proportional_spans_reject_impossible_duration():
    with pytest.raises(Exception):
        beats.proportional_spans(2, ["甲", "乙", "丙"])


def test_silent_timeline_reserves_stable_reading_tail():
    model = storyboard._build(beat_script(), storyboard.Report())
    timeline = model.scenes[0].beat_timeline
    assert timeline.estimated is True
    assert timeline.beats[-1].end_frame == 120 - beats.STABLE_READING_FRAMES
    assert timeline.beats[0].start_frame == 0


def test_state_at_is_consistent_for_first_middle_boundary_last_and_random():
    timeline = beats.BeatTimeline(
        (
            beats.ResolvedBeat("b1", "establish", ("a",), "建立", 10, 40),
            beats.ResolvedBeat("b2", "deplete", ("a",), "消耗", 40, 70),
        ),
        False,
    )
    assert timeline.state_at(0) == {"current": None, "progress": 0.0, "completed": [], "estimated": False}
    assert timeline.state_at(10)["current"] == "b1"
    assert timeline.state_at(10)["progress"] == 0.0
    assert timeline.state_at(25)["progress"] == pytest.approx(0.5)
    # 边界帧：b1 的末帧仍属于 b1，b2 的首帧已经属于 b2
    assert timeline.state_at(39)["current"] == "b1"
    assert timeline.state_at(40) == {"current": "b2", "progress": 0.0, "completed": ["b1"], "estimated": False}
    assert timeline.state_at(70) == {"current": None, "progress": 0.0, "completed": ["b1", "b2"], "estimated": False}
    # 随机访问：先跳到后面再回来，结果不变（纯函数、无缓存）
    later = timeline.state_at(95)
    assert later == timeline.state_at(95)
    assert timeline.state_at(25)["progress"] == pytest.approx(0.5)


def test_timeline_validation_reports_regression_overlap_and_out_of_range():
    items = [
        beats.ResolvedBeat("b1", "establish", ("a",), "建立", 0, 40),
        beats.ResolvedBeat("b2", "deplete", ("a",), "消耗", 30, 80),
        beats.ResolvedBeat("b3", "restore", ("a",), "恢复", 90, 200),
    ]
    issues = beats.validate_timeline(items, 120)
    assert any("倒退或重叠" in item for item in issues)
    assert any("超出场景" in item for item in issues)


def test_timeline_validation_rejects_unknown_action_and_blank_meaning():
    items = [beats.ResolvedBeat("b1", "wiggle", ("a",), "  ", 0, 40)]
    issues = beats.validate_timeline(items, 120)
    assert any("未知语义动作" in item for item in issues)
    assert any("meaning 不能为空" in item for item in issues)


def test_timeline_json_roundtrip():
    timeline = beats.BeatTimeline((beats.ResolvedBeat("b1", "connect", ("a", "b"), "连接", 5, 25),), False)
    restored = beats.BeatTimeline.from_json(timeline.to_json(), estimated=False)
    assert restored == timeline


def test_scene_narration_concatenates_segments_in_order():
    data = beat_script()
    assert beats.scene_narration(scene(data)) == "先看基线。再看累积到临界点。"
    legacy = copy.deepcopy(scene(data))
    legacy.pop("narrationSegments")
    legacy["narration"] = "字符串口播"
    assert beats.scene_narration(legacy) == "字符串口播"


# ---------------------------------------------------------------------------
# Python / TypeScript 共用向量：两侧实现必须给出同一批数字
# ---------------------------------------------------------------------------


def shared_vectors() -> dict:
    """两侧共用的向量文件。

    无声估算在两条路径上各有一份实现：Python 用它做闸门采样（A5/A7），
    TypeScript 用它渲染预览与无声成片。两边漂移的话，验收过的边界和画面上
    跑的边界就不是同一批，因此把向量放进仓库、两侧测试读同一份文件。
    """
    path = pathlib.Path(__file__).with_name("fixtures") / "beat-vectors.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_shared_vectors_match_proportional_spans():
    vectors = shared_vectors()["spans"]
    assert vectors, "向量文件不能是空的"
    for vector in vectors:
        spans = beats.proportional_spans(vector["duration"], vector["texts"])
        assert [list(span) for span in spans] == vector["expected"], vector["why"]


def test_shared_vectors_match_silent_resolution():
    vectors = shared_vectors()["scenes"]
    assert vectors, "向量文件不能是空的"
    for vector in vectors:
        data = beat_script()
        target = scene(data)
        target["durationInFrames"] = vector["durationInFrames"]
        target["narrationSegments"] = [
            {"id": f"n{index + 1}", "text": text, "beatId": beat_id}
            for index, (text, beat_id) in enumerate(zip(vector["texts"], vector["beatIds"]))
        ]
        target["beats"] = [
            {"id": beat_id, "action": "transform", "targets": ["chart"], "meaning": f"第 {index + 1} 步"}
            for index, beat_id in enumerate(dict.fromkeys(vector["beatIds"]))
        ]
        timeline = beats.resolve_silent(target)
        actual = [
            {"id": item.id, "startFrame": item.start_frame, "endFrame": item.end_frame}
            for item in timeline.beats
        ]
        assert actual == vector["expected"], vector["why"]
