from __future__ import annotations

import os
import hashlib
import pytest
from types import SimpleNamespace
from pathlib import Path

from a2v import production
from a2v import article_text
from a2v.errors import A2VError
from conftest import make_project


def _ready_record() -> dict:
    storyboard = {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]}
    digest = "d" * 64
    input_review = {
        "countingVersion": article_text.COUNTING_VERSION,
        "source": {"path": "article.md", "sha256": digest}, "charCount": 140,
        "lengthStatus": "pass",
        "singleScene": {"status": "pass", "claim": "逐步试错", "metaphor": "飞镖靶",
                        "problemSpans": [], "rationale": "人物、飞镖与靶可持续存在，状态推进论证"},
        "status": "pass", "assessment": {"reviewer": "ai", "model": "test", "session": "test"},
    }
    value = production.initialize_template(storyboard, {"storyboard": "s", "assets": "a", "media": "m"}, input_review)
    value["materials"] = {
        name: {"path": f"outputs/{name}", "sha256": {"keyframes": "a", "samples": "b", "rehearsal": "c"}[name] * 64,
               "fingerprints": {"storyboard": "s", "assets": "a", "media": "m"}}
        for name in ("keyframes", "samples", "rehearsal")
    }
    value["direction"]["keyScenes"] = {"opening": "open", "core": "core", "climax": "close"}
    value["direction"]["pace"] = "开场慢、推理加速、高潮停留"
    for scene in storyboard["scenes"]:
        value["direction"]["scenePlans"][scene["id"]] = {"start": "起点", "change": "变化", "result": "结果"}
    value["reviews"]["keyScenes"] = {}
    for scene_id in {"open", "core", "close"}:
        value["reviews"]["keyScenes"][scene_id] = _passing_review()
    value["reviews"]["full"] = _passing_review(full=True)
    return value


def _passing_review(full: bool = False) -> dict:
    reviews = {}
    for kind in (("static", "dynamic", "content") if full else ("static", "dynamic")):
        material_name = "keyframes" if kind == "static" else ("rehearsal" if full else "samples")
        reviews[kind] = {
            "status": "pass",
            "dimensions": {name: {"status": "pass", "evidence": "联系表/有声样片中可观察到对应结果", **({"score": 4} if kind == "content" else {})}
                           for name in production.REVIEW_DIMENSIONS[kind]},
            "evidence": "逐幕核对，相关画面与口播一致",
            "assessment": {"reviewer": "ai", "model": "Codex current-session", "session": "test-session",
                           "materials": {material_name: {"keyframes": "a", "samples": "b", "rehearsal": "c"}[material_name] * 64}},
        }
    return reviews


def _bind_test_input(record: dict, root: Path) -> None:
    article_dir = root / "videos" / "demo"
    article_dir.mkdir(parents=True, exist_ok=True)
    source = article_dir / "article.md"
    body = "x" * 140
    source.write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode()).hexdigest()
    record["inputReview"]["source"] = {"path": "videos/demo/article.md", "sha256": digest}
    record["fingerprints"]["input"] = digest
    record["materialRoot"] = os.path.relpath(root, article_dir)


def test_template_deduplicates_key_scene_review_slots() -> None:
    storyboard = {"scenes": [{"id": "one"}, {"id": "two"}, {"id": "three"}]}
    template = production.initialize_template(storyboard, {"storyboard": "s", "assets": "a", "media": None})
    template["materials"] = {
        name: {"path": f"outputs/{name}", "sha256": {"keyframes": "a", "samples": "b", "rehearsal": "c"}[name] * 64,
               "fingerprints": {"storyboard": "s", "assets": "a", "media": None}}
        for name in ("keyframes", "samples", "rehearsal")
    }
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


def test_input_review_blocks_missing_evidence_fail_and_changed_source() -> None:
    storyboard = {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]}
    record = _ready_record()
    current = record["fingerprints"]
    assert production.gate_for_status(record, storyboard, current) is None
    record["inputReview"]["singleScene"]["status"] = "pending"
    record["inputReview"]["status"] = "pending"
    assert "待评审" in production.gate_for_status(record, storyboard, current)
    record = _ready_record()
    record["inputReview"]["singleScene"]["status"] = "fail"
    record["inputReview"]["status"] = "fail"
    assert "未通过" in production.gate_for_status(record, storyboard, current)
    record = _ready_record()
    assert "过期" in production.gate_for_status(record, storyboard, {**current, "input": "e" * 64})


def test_input_review_requires_workspace_relative_source() -> None:
    record = _ready_record()
    record["inputReview"]["source"]["path"] = "../article.md"
    with pytest.raises(A2VError, match=r"inputReview.source.path.*相对路径"):
        production.validate_record(record, {"open", "core", "close"})


def test_adopted_candidate_authorization_is_invalidated_by_candidate_edit(tmp_path: Path) -> None:
    article_dir = tmp_path / "videos" / "demo"
    article_dir.mkdir(parents=True)
    original = article_dir / "article.md"
    original.write_text("长文" * 200, encoding="utf-8")
    candidate = article_dir / "article.candidate.md"
    candidate.write_text("稿" * 140 + "\n", encoding="utf-8")
    accepted = article_dir / "article.accepted.md"
    accepted.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
    _, source_digest = article_text.read_source(original)
    _, candidate_digest = article_text.read_source(candidate)
    _, accepted_digest = article_text.read_source(accepted)
    review = article_text.review_for_file(accepted, tmp_path)
    review.update({"status": "pass", "singleScene": {"status": "pass", "claim": "集中观点",
        "metaphor": "持续流程", "problemSpans": [], "rationale": "同一视觉世界可承载必要推理"},
        "assessment": {"reviewer": "ai", "model": "test", "session": "test"},
        "authorization": {"path": candidate.name, "sha256": candidate_digest,
                           "sourceSha256": source_digest}})
    record = {"inputReview": review, "materialRoot": os.path.relpath(tmp_path, article_dir)}
    record_file = article_dir / "production.json"
    assert production._input_review_issue(record, {"input": accepted_digest}, record_file) is None
    candidate.write_text("修改" * 70 + "\n", encoding="utf-8")
    assert "授权与审查失效" in production._input_review_issue(record, {"input": accepted_digest}, record_file)


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
    assert len(stored["materials"]["keyframes"]["sha256"]) == 64
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
    assert rows[0]["stage"] == "输入文章审查"
    assert rows[0]["status"] == "fail"
    assert any(row["stage"] == "导演规划" and "AI 助手" in row["nextCommand"] for row in rows)


def test_all_stages_pass_accepts_both_success_spellings() -> None:
    """全片评审行的 `pass` 与关键幕/正式渲染行的 `passed` 都算通过。

    两种写法同时出现在同一份状态里：只认其中一种会让「所有评审都填好了」
    的命令仍然返回失败，调用方据此以为还有阻塞项。
    """
    storyboard = {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]}
    current = {"storyboard": "s", "assets": "a", "media": "m"}
    rows = production.status_rows(_ready_record(), storyboard, current)
    assert {row["status"] for row in rows} == {"passed", "pass", "not-required"}
    assert production.all_stages_pass(rows) is True

    blocked = [dict(row) for row in rows]
    blocked[-1]["status"] = "blocked"
    assert production.all_stages_pass(blocked) is False
    stale = [dict(row) for row in rows]
    stale[0]["status"] = "stale"
    assert production.all_stages_pass(stale) is False


def test_completed_review_requires_ai_source_and_visual_material_references() -> None:
    record = _ready_record()
    record["reviews"]["full"]["static"].pop("assessment")
    assert production.validate_record(record, {"open", "core", "close"}) is None
    issue = production.gate_for_status(record, {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]},
                                      {"storyboard": "s", "assets": "a", "media": "m"})
    assert "缺少 AI 评审来源" in issue

    record = _ready_record()
    record["reviews"]["full"]["static"]["assessment"]["materials"].pop("keyframes")
    with pytest.raises(A2VError, match=r"assessment\.materials"):
        production.validate_record(record, {"open", "core", "close"})


def test_gate_blocks_unregistered_or_stale_visual_material(tmp_path: Path) -> None:
    storyboard = {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]}
    current = {"storyboard": "s", "assets": "a", "media": "m"}
    record = _ready_record()
    record["reviews"]["full"]["static"]["assessment"]["materials"]["keyframes"] = "wrong-digest"
    assert "摘要" in production.gate_for_status(record, storyboard, current)

    record = _ready_record()
    record["materials"]["rehearsal"]["fingerprints"]["media"] = "old-media"
    assert "材料输入版本已过期" in production.gate_for_status(record, storyboard, current)

    root = tmp_path / "workspace"
    record_dir = root / "videos" / "demo"
    record_dir.mkdir(parents=True)
    material = root / "outputs" / "keyframes.png"
    material.parent.mkdir()
    material.write_bytes(b"original")
    _bind_test_input(record, root)
    import hashlib
    digest = hashlib.sha256(b"original").hexdigest()
    record["materialRoot"] = os.path.relpath(root, record_dir)
    record["materials"]["keyframes"].update({"path": "outputs/keyframes.png", "sha256": digest})
    record["reviews"]["full"]["static"]["assessment"]["materials"]["keyframes"] = digest
    for scene_review in record["reviews"]["keyScenes"].values():
        scene_review["static"]["assessment"]["materials"]["keyframes"] = digest
    material.write_bytes(b"replaced")
    assert "摘要已变化" in production.gate_for_status(record, storyboard, current, record_dir / "production.json")


def test_sample_manifest_tracks_and_checks_video_file_digest(tmp_path: Path) -> None:
    import json
    import hashlib

    root = tmp_path / "workspace"
    record_dir = root / "videos" / "demo"
    record_dir.mkdir(parents=True)
    record_file = record_dir / "production.json"
    video = root / "outputs" / "key-scene.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"sample-frame-data")
    manifest = video.parent / "samples.json"
    manifest.write_text(json.dumps({"outputs": [{"file": video.name}]}), encoding="utf-8")
    record = _ready_record()
    _bind_test_input(record, root)
    keyframes = root / "outputs" / "keyframes.png"
    keyframes.write_bytes(b"keyframe")
    keyframes_digest = hashlib.sha256(b"keyframe").hexdigest()
    record["materials"]["keyframes"].update({"path": "outputs/keyframes.png", "sha256": keyframes_digest})
    record["reviews"]["full"]["static"]["assessment"]["materials"]["keyframes"] = keyframes_digest
    for item in record["reviews"]["keyScenes"].values():
        item["static"]["assessment"]["materials"]["keyframes"] = keyframes_digest
    record_file.write_text(json.dumps(record), encoding="utf-8")
    article = SimpleNamespace(workspace_root=root)

    production.attach_material(record_file, article, "samples", manifest,
                               {"storyboard": "s", "assets": "a", "media": "m"})
    stored = json.loads(record_file.read_text(encoding="utf-8"))
    assert stored["materials"]["samples"]["files"][video.name] == hashlib.sha256(b"sample-frame-data").hexdigest()

    updated_digest = stored["materials"]["samples"]["sha256"]
    for item in stored["reviews"]["keyScenes"].values():
        item["dynamic"]["assessment"]["materials"]["samples"] = updated_digest
    video.write_bytes(b"replaced-video")
    issue = production.gate_for_status(stored, {"scenes": [{"id": "open"}, {"id": "core"}, {"id": "close"}]},
                                       {"storyboard": "s", "assets": "a", "media": "m"}, record_file)
    assert "视频材料已缺失或摘要已变化" in issue
