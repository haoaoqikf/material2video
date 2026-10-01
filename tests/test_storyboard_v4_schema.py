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
    return value


def test_shared_v4_contract_vectors() -> None:
    assert validate(VECTORS["valid"]).ok
    for case in VECTORS["invalid"]:
        assert not validate(_mutate(case["mutation"])).ok, case["name"]
