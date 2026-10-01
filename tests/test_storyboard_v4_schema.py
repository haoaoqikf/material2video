from __future__ import annotations

import copy
import json
from pathlib import Path

from a2v.storyboard_v4 import validate


VECTORS = json.loads((Path(__file__).parent / "fixtures" / "storyboard-v4-vectors.json").read_text(encoding="utf-8"))


def _mutate(name: str) -> dict:
    value = copy.deepcopy(VECTORS["valid"])
    if name == "version-v3":
        value.update(version=3, schemaVersion=3)
    elif name == "duplicate-stage":
        value["stages"].append(copy.deepcopy(value["stages"][0]))
    elif name == "unknown-root":
        value["legacyField"] = True
    elif name == "stage-renderer":
        value["stages"][0]["renderer"] = {"kind": "tree"}
    elif name == "stage-transition":
        value["stages"][0]["transition"] = {"kind": "inherit"}
    elif name == "duplicate-beat":
        value["stages"][0]["beats"].append(copy.deepcopy(value["stages"][0]["beats"][0]))
    elif name == "missing-track-baseline":
        value["world"]["stateTracks"] = [{"id": "track-a", "target": "player", "property": "state",
            "binding": {"beatId": "throw-1"}, "to": "focus", "interpolation": "step-end"}]
    elif name == "track-target-type":
        value["world"]["stateTracks"] = [{"id": "track-a", "target": "dart", "property": "value",
            "binding": {"beatId": "throw-1"}, "to": 1, "interpolation": "linear"}]
    elif name == "invalid-track-beat":
        value["world"]["stateTracks"] = [{"id": "track-a", "target": "player", "property": "state",
            "binding": {"beatId": "absent"}, "to": "focus", "interpolation": "step-end"}]
    elif name in {"overlapping-track", "illegal-interpolation"}:
        value["world"]["sceneTree"]["children"][0]["state"] = "rest"
        track = {"id": "track-a", "target": "player", "property": "state",
            "binding": {"beatId": "throw-1"}, "to": "focus", "interpolation": "step-end"}
        if name == "overlapping-track": value["world"]["stateTracks"] = [track, {**track, "id": "track-b", "to": "done"}]
        else: value["world"]["stateTracks"] = [{**track, "interpolation": "linear"}]
    elif name == "length-171":
        value["stages"][0]["durationInFrames"] = 1200
        value["stages"][0]["narrationSegments"][0]["text"] = "甲" * 171
    elif name == "duration-short":
        value["stages"][0]["durationInFrames"] = 34 * value["fps"]
    elif name == "duration-long":
        value["stages"][0]["durationInFrames"] = 46 * value["fps"]
    elif name == "silent-only":
        value["stages"][0].pop("narrationSegments")
        value["stages"][0].pop("beats")
    elif name == "too-many-global-nodes":
        root = value["world"]["sceneTree"]
        for group_index in range(9):
            root["children"].append({"id": f"extra-group-{group_index}", "type": "group", "children": [
                {"id": f"extra-{group_index}-{node_index}", "type": "shape", "shape": "circle"}
                for node_index in range(4)
            ]})
    return value


def test_shared_v4_contract_vectors() -> None:
    assert validate(VECTORS["valid"]).ok
    for case in VECTORS["invalid"]:
        assert not validate(_mutate(case["mutation"])).ok, case["name"]


def test_declared_duration_boundaries_and_40_seconds_with_171_chars() -> None:
    for seconds in (35, 45):
        value = copy.deepcopy(VECTORS["valid"])
        value["stages"][0]["durationInFrames"] = seconds * value["fps"]
        assert validate(value).ok, seconds
    messages = [issue.message for issue in validate(_mutate("length-171")).errors]
    assert any("171 字" in message for message in messages)


def _soundtrack_is_rejected(soundtrack: dict | None, **segment: object) -> bool:
    value = copy.deepcopy(VECTORS["valid"])
    if soundtrack is not None:
        value["soundtrack"] = soundtrack
    value["stages"][0]["narrationSegments"][0].update(segment)
    return not validate(value).ok


def test_soundtrack_keeps_the_v3_numeric_and_path_contract() -> None:
    """v4 沿用根级声音设置：素材路径、增益、循环、淡入淡出与音效偏移口径不变。"""
    assert not _soundtrack_is_rejected({"music": {"sourceRef": "bed.wav"}})
    assert _soundtrack_is_rejected({"music": {"sourceRef": "../bed.wav"}})
    assert _soundtrack_is_rejected({"music": {"sourceRef": "https://example.com/bed.wav"}})
    assert _soundtrack_is_rejected({"music": {"sourceRef": "assets\\bed.wav"}})
    assert _soundtrack_is_rejected({"music": {"sourceRef": "bed.wav", "gainDb": 1}})
    assert _soundtrack_is_rejected({"music": {"sourceRef": "bed.wav", "gainDb": -61}})
    assert _soundtrack_is_rejected({"music": {"sourceRef": "bed.wav", "loop": "yes"}})
    assert _soundtrack_is_rejected({"music": {"sourceRef": "bed.wav", "fadeInMs": 60001}})
    assert _soundtrack_is_rejected({"music": {"sourceRef": "bed.wav", "unknown": 1}})


def test_effects_keep_their_bounds_and_global_identity() -> None:
    stage = VECTORS["valid"]["stages"][0]["id"]
    beat = VECTORS["valid"]["stages"][0]["beats"][0]["id"]
    drop = {"sourceRef": "assets/drop.wav", "stageId": stage, "beatId": beat, "offsetMs": 0, "gainDb": -12}
    assert not _soundtrack_is_rejected({"effects": [drop]})
    assert _soundtrack_is_rejected({"effects": [{**drop, "offsetMs": 60001}]})
    assert _soundtrack_is_rejected({"effects": [{**drop, "offsetMs": -60001}]})
    assert _soundtrack_is_rejected({"effects": [{**drop, "offsetMs": 1.5}]})
    assert _soundtrack_is_rejected({"effects": [{**drop, "gainDb": -61}]})
    assert _soundtrack_is_rejected({"effects": [{**drop, "sourceRef": "/abs/drop.wav"}]})
    assert _soundtrack_is_rejected({"effects": [{**drop, "stageId": "absent"}]})
    assert _soundtrack_is_rejected({"effects": [{**drop, "beatId": "absent"}]})
    assert _soundtrack_is_rejected({"effects": [drop] * 129})
    # 音效归属由 stageId + beatId 表达，旧的 sceneId 不再接受。
    assert _soundtrack_is_rejected({"effects": [{**drop, "sceneId": stage}]})


def test_per_segment_speech_is_rejected_instead_of_silently_ignored() -> None:
    """v4 按整段口播统一语速合成：逐段 speech 必须显式拒绝，不能静默忽略。"""
    value = copy.deepcopy(VECTORS["valid"])
    value["stages"][0]["narrationSegments"][0]["speech"] = {"rate": "+10%"}
    issues = validate(value).errors
    assert any("speech" in issue.path and "不再支持逐段 speech" in issue.message for issue in issues)


def test_narration_segments_require_ids_text_and_local_beats() -> None:
    for patch in ({"id": "bad id"}, {"text": "  "}, {"beatId": "absent"}, {"extra": 1}):
        value = copy.deepcopy(VECTORS["valid"])
        value["stages"][0]["narrationSegments"][0].update(patch)
        assert not validate(value).ok, patch


def test_visual_intent_uses_the_same_controlled_vocabulary_as_the_browser() -> None:
    """Python 通过的分镜不能在契约页被 zod 拒绝：两端共用同一套受控词汇。"""
    for patch in ({"relation": "cause-and-effect"}, {"focus": "target"}, {"composition": "middle"},
                  {"density": "even"}, {"tone": "happy"}, {"mode": "diagram"},
                  {"claim": ""}, {"primaryObject": "  "}, {"extra": True}):
        value = copy.deepcopy(VECTORS["valid"])
        value["stages"][0]["visualIntent"].update(patch)
        assert not validate(value).ok, patch
    assert validate(VECTORS["valid"]).ok


