"""金融来源的当前折线计划与帧映射。"""
from __future__ import annotations

import json

import pytest

from helpers.financial import project
from m2v.core.errors import M2VError
from m2v.types.financial import financial


def test_line_plan_is_deterministic_and_has_three_segments(tmp_path):
    root = project(tmp_path)
    request = json.loads((root / "request.json").read_text(encoding="utf-8"))
    prices = json.loads((root / "prices.json").read_text(encoding="utf-8"))
    first = financial.build_line_plan(request, 15, prices)
    second = financial.build_line_plan(request, 15, prices)
    assert first == second
    assert [item["kind"] for item in first["segments"]] == ["opening", "advance", "ending"]
    assert first["segments"][-1]["frames"][1] == 450
    assert financial.frame_date(first, 0).isoformat() == request["displayRange"][0]
    assert financial.frame_date(first, 449).isoformat() == request["displayRange"][1]


def test_plan_generation_uses_declared_source_files(tmp_path):
    root = project(tmp_path)
    files = {"request": "request.json", "prices": "prices.json", "plan": "animation-plan.json"}
    (root / "animation-plan.json").unlink()
    plan = financial.prepare_line_plan(root, 12, files=files)
    assert plan["schemaVersion"] == 8 and plan["durationSeconds"] == 12
    assert not (root / "animation-plan.json").exists(), "生成函数不得自行覆盖材料"


def test_v7_source_plan_is_rejected(tmp_path):
    root = project(tmp_path)
    path = root / "animation-plan.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["schemaVersion"] = 7
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(M2VError, match="v8"):
        financial.load_project(root)


def test_too_short_plan_is_rejected(tmp_path):
    root = project(tmp_path)
    with pytest.raises(M2VError, match="4 秒"):
        financial.prepare_line_plan(root, 3, files={"request": "request.json", "prices": "prices.json", "plan": "animation-plan.json"})
