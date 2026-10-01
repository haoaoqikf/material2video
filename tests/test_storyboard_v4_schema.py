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
    return value


def test_shared_v4_contract_vectors() -> None:
    assert validate(VECTORS["valid"]).ok
    for case in VECTORS["invalid"]:
        assert not validate(_mutate(case["mutation"])).ok, case["name"]
