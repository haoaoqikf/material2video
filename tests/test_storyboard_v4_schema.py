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
