from __future__ import annotations

import pytest
from types import SimpleNamespace
from pathlib import Path

from a2v import production
from a2v.errors import A2VError
from conftest import make_project


def _ready_record() -> dict:
    storyboard = {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]}
    value = production.initialize_template(storyboard, {"storyboard": "s", "assets": "a", "media": "m"})
    value["direction"]["keyScenes"] = {"opening": "open", "core": "core", "climax": "close"}
    value["direction"]["pace"] = "开场慢、推理加速、高潮停留"
    for scene in storyboard["scenes"]:
        value["direction"]["scenePlans"][scene["id"]] = {"start": "起点", "change": "变化", "result": "结果"}
    value["reviews"]["keyScenes"] = {}
    for scene_id in {"open", "core", "close"}:
        value["reviews"]["keyScenes"][scene_id] = _passing_review()
    value["reviews"]["full"] = _passing_review()
    return value


def _passing_review() -> dict:
    return {
        kind: {
            "status": "pass",
            "dimensions": {name: {"status": "pass", "evidence": "联系表/有声样片中可观察到对应结果"}
                           for name in production.REVIEW_DIMENSIONS[kind]},
            "evidence": "逐幕核对，相关画面与口播一致",
        }
        for kind in ("static", "dynamic")
    }


def test_template_deduplicates_key_scene_review_slots() -> None:
    storyboard = {"scenes": [{"id": "one"}, {"id": "two"}, {"id": "three"}]}
    template = production.initialize_template(storyboard, {"storyboard": "s", "assets": "a", "media": None})
    template["direction"]["keyScenes"] = {"opening": "one", "core": "one", "climax": "two"}
    template["reviews"]["keyScenes"] = {scene: _passing_review() for scene in {"one", "two"}}
    template["direction"]["pace"] = "先慢后快"
    template["direction"]["scenePlans"] = {scene: {"start": "a", "change": "b", "result": "c"} for scene in ("one", "two", "three")}
    production.validate_record(template, {"one", "two", "three"})
    # The initializer gives every scene a slot; roles sharing an ID still use
    # one slot, while non-key scenes remain available if the user reassigns roles.
    initialized = production.initialize_template(storyboard, {"storyboard": "s", "assets": "a", "media": None})
    assert set(initialized["reviews"]["keyScenes"]) == {"one", "two", "three"}
    assert set(template["reviews"]["keyScenes"]) == {"one", "two"}


def test_validate_record_reports_unknown_scene_at_field_path() -> None:
    record = _ready_record()
    record["direction"]["keyScenes"]["climax"] = "missing"
    with pytest.raises(A2VError, match=r"direction\.keyScenes\.climax.*未知场景"):
        production.validate_record(record, {"open", "core", "close"})


def test_gate_blocks_stale_inputs_and_open_required_rework() -> None:
    record = _ready_record()
    storyboard = {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]}
    assert production.gate("unused", storyboard, {"storyboard": "s", "assets": "a", "media": "m"}) is not None
    record = _ready_record()
    record["rework"] = [{"id": "r1", "dimension": "rhythm", "problem": "节奏平", "direction": "拉开快慢",
                          "returnStage": "motion", "severity": "required", "status": "open", "sceneIds": ["close"]}]
    current = {"storyboard": "s", "assets": "a", "media": "m"}
    assert production.gate_for_status(record, storyboard, {**current, "assets": "changed"}) == "评审已过期：assets"
    assert production.gate_for_status(record, storyboard, current) == "存在未解决的必改项"


def test_gate_blocks_failed_key_scene_and_full_review() -> None:
    storyboard = {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]}
    current = {"storyboard": "s", "assets": "a", "media": "m"}
    record = _ready_record()
    record["reviews"]["keyScenes"]["close"]["dynamic"]["status"] = "fail"
    for name in production.REVIEW_DIMENSIONS["dynamic"]:
        record["reviews"]["keyScenes"]["close"]["dynamic"]["dimensions"][name] = {"status": "pass", "evidence": "复查"}
    record["reviews"]["keyScenes"]["close"]["dynamic"]["dimensions"]["rhythm"] = {"status": "fail", "evidence": "高潮与前后幕同速"}
    assert "关键幕 close" in production.gate_for_status(record, storyboard, current)
    record = _ready_record()
    record["reviews"]["full"]["static"]["status"] = "pending"
    for name in production.REVIEW_DIMENSIONS["static"]:
        record["reviews"]["full"]["static"]["dimensions"][name] = {"status": "pending", "evidence": ""}
    assert production.gate_for_status(record, storyboard, current) is not None


def test_failed_review_rework_recheck_closes_only_on_current_version() -> None:
    storyboard = {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]}
    current = {"storyboard": "s", "assets": "a", "media": "m"}
    record = _ready_record()
    failed = record["reviews"]["keyScenes"]["close"]["static"]
    failed["dimensions"]["climax_weight"] = {"status": "fail", "evidence": "高潮结果停留不足"}
    failed["status"] = "fail"
    failed["evidence"] = "高潮场景与前一幕权重接近"
    record["rework"] = [{"id": "R-01", "dimension": "climax_weight", "problem": "高潮分量不足",
                         "direction": "拉开过程与结果的节奏", "returnStage": "motion",
                         "severity": "required", "status": "open", "sceneIds": ["close"]}]
    assert "尚未通过" in production.gate_for_status(record, storyboard, current)

    # A new passing review still cannot close a required item by itself.
    record["reviews"]["keyScenes"]["close"]["static"] = _passing_review()["static"]
    assert production.gate_for_status(record, storyboard, current) == "存在未解决的必改项"
    record["rework"][0].update({"status": "resolved", "recheck": {
        "status": "pass", "evidence": "修订版结果停留清楚",
        "fingerprints": current,
    }})
    assert production.gate_for_status(record, storyboard, current) is None
    changed = {**current, "assets": "new-assets"}
    assert "过期" in production.gate_for_status(record, storyboard, changed)


def test_resolved_rework_requires_recheck_evidence() -> None:
    record = _ready_record()
    storyboard = {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]}
    current = {"storyboard": "s", "assets": "a", "media": "m"}
    record["rework"] = [{"id": "r1", "dimension": "rhythm", "problem": "节奏平", "direction": "拉开快慢",
                          "returnStage": "motion", "severity": "required", "status": "resolved", "sceneIds": [],
                          "recheck": {"status": "pass", "evidence": "修订版节奏形成起伏",
                                      "fingerprints": {"storyboard": "s", "assets": "a", "media": "m"}}}]
    production.validate_record(record, {"open", "core", "close"})
    assert production.gate_for_status(record, storyboard, current) is None
    record["rework"][0]["recheck"]["evidence"] = ""
    with pytest.raises(A2VError, match=r"rework\[0\]\.recheck"):
        production.validate_record(record, {"open", "core", "close"})
    record["rework"][0]["recheck"]["evidence"] = "依据"
    record["rework"][0]["recheck"]["fingerprints"]["storyboard"] = "old"
    with pytest.raises(A2VError, match=r"rework\[0\]\.recheck\.fingerprints"):
        production.validate_record(record, {"open", "core", "close"})


def test_key_scene_status_marks_passed_reviews_stale_after_input_change() -> None:
    storyboard = {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]}
    record = _ready_record()
    current = {"storyboard": "changed", "assets": "a", "media": "new-media"}
    rows = production.status_rows(record, storyboard, current)
    assert all(row["status"] == "stale" for row in rows if row["stage"].startswith("关键幕:"))


def test_key_scene_ranges_preserve_roles_and_merge_neighbor_context() -> None:
    scenes = [SimpleNamespace(id=name, duration_in_frames=30) for name in ("a", "b", "c", "d", "e")]
    ranges = production.key_scene_ranges(scenes, {"opening": "a", "core": "a", "climax": "b", "extra": "e"}, 30, 150)
    assert ranges == [(0, 74, ["a", "b"], ["opening", "core", "climax"]), (105, 149, ["e"], ["extra"])]


def test_storyboard_fingerprint_changes_when_bytes_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "storyboard.json"
    source.write_text('{"scenes":[]}', encoding="utf-8")
    monkeypatch.setattr(production.remotion, "build_input_fingerprint", lambda **_kwargs: {"digest": "assets"})
    article = SimpleNamespace(workspace_root=tmp_path)
    before = production.current_fingerprints(source, None, article)
    source.write_text('{"scenes": [ ]}', encoding="utf-8")
    after = production.current_fingerprints(source, None, article)
    assert before["storyboard"] != after["storyboard"]


def test_example_production_record_is_outside_versioned_example_source(tmp_path: Path) -> None:
    article_root = make_project(tmp_path, "examples", "demo", script={"scenes": []})
    article = __import__("a2v.paths", fromlist=["for_storyboard"]).for_storyboard(article_root / "storyboard.json")
    assert production.record_path(article) == tmp_path / "videos" / "examples" / "demo" / "production.json"


def test_attaching_material_records_path_and_fingerprint_without_changing_review(tmp_path: Path) -> None:
    import json
    article = SimpleNamespace(workspace_root=tmp_path)
    record_file = tmp_path / "production.json"
    record = _ready_record()
    record_file.write_text(json.dumps(record), encoding="utf-8")
    material = tmp_path / "outputs" / "keyframes.png"
    material.parent.mkdir()
    material.write_bytes(b"image")
    production.attach_material(record_file, article, "keyframes", material, {"storyboard": "s", "assets": "a", "media": None})
    stored = json.loads(record_file.read_text(encoding="utf-8"))
    assert stored["materials"]["keyframes"]["path"] == "outputs/keyframes.png"
    assert stored["reviews"] == record["reviews"]


def test_shipped_production_template_matches_cause_chain_scenes() -> None:
    import json
    from pathlib import Path

    example_dir = Path(__file__).resolve().parents[1] / "examples" / "cause-chain"
    storyboard = json.loads((example_dir / "storyboard.json").read_text(encoding="utf-8"))
    record = json.loads((example_dir / "production.template.json").read_text(encoding="utf-8"))
    production.validate_record(record, {scene["id"] for scene in storyboard["scenes"]})


def test_status_reports_incomplete_template_as_actionable_not_invalid() -> None:
    storyboard = {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]}
    record = production.initialize_template(storyboard, {"storyboard": "s", "assets": "a", "media": None})
    rows = production.status_rows(record, storyboard, {"storyboard": "s", "assets": "a", "media": None})
    assert rows[0]["stage"] == "导演规划"
    assert rows[0]["status"] == "pending"
    assert "direction.keyScenes" in rows[0]["nextCommand"]
