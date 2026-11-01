from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.core.project import load_project
from m2v.commands import _require_review, _review_criteria
from m2v.types.financial.migration import migrate
from m2v.type_system.relocation import relocate
from m2v.type_system import registry
from m2v.type_system.registry import VideoType
from conftest import create_typed_project, register_synthetic_type


def test_general_render_needs_no_visual_approval_and_preserves_referenced_evidence(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "work"
    outputs = root / "outputs"
    outputs.mkdir(parents=True)
    manifest = {"schemaVersion": 1, "id": "work", "type": "general"}
    prepared = {"preparedFingerprint": "current", "durationInFrames": 60,
                "width": 1920, "height": 1080, "fps": 60}
    final = outputs / "video.mp4"
    frame = outputs / "qa" / "frame.png"
    frame.parent.mkdir()
    frame.write_bytes(b"evidence")
    (outputs / "visual-notes.md").write_text("未复查；[帧](qa/frame.png)", encoding="utf-8")

    def render(*_args):
        final.write_bytes(b"rendered")
        return final

    video_type = VideoType("general", lambda *_: None, lambda *_: prepared,
                          lambda *_: None, render, prepared_check=lambda *_: prepared)
    monkeypatch.setattr(registry, "_registry", {"general": video_type})
    monkeypatch.setattr("m2v.commands.load_project", lambda *_: (root, manifest))

    assert main(["status", "--project", str(root)]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["review"]["required"] is False
    assert "技术就绪" in status["review"]["detail"]
    assert main(["render", "--project", str(root)]) == 0
    assert frame.is_file() and final.is_file()


def test_init_writes_all_financial_material_templates_under_content_root(tmp_path: Path) -> None:
    root = tmp_path / "content"
    assert main(["init", "--type", "financial-timeseries", "--project", "demo", "--content-root", str(root)]) == 0
    project_root, manifest = load_project(root / "videos" / "financial-timeseries" / "demo")
    assert set(manifest["materials"]) == {"request", "prices", "plan"}
    assert all((project_root / name).is_file() for name in manifest["materials"].values())
    with open(project_root / "animation-plan.json", encoding="utf-8") as stream:
        plan = json.load(stream)
        assert plan["schemaVersion"] == 8
        assert {k: manifest["output"][k] for k in ("width", "height")} == plan["canvas"]


def test_init_accepts_explicit_canonical_type_path(tmp_path: Path) -> None:
    root = tmp_path / "content"
    assert main(["init", "--type", "general", "--project", "videos/general/demo", "--content-root", str(root)]) == 0
    assert (root / "videos" / "general" / "demo" / "project.json").is_file()


def test_init_rejects_wrong_or_incomplete_type_path(tmp_path: Path) -> None:
    root = tmp_path / "content"
    assert main(["init", "--type", "general", "--project", "videos/financial-timeseries/demo", "--content-root", str(root)]) == 2
    assert main(["init", "--type", "general", "--project", "videos/demo", "--content-root", str(root)]) == 2


def test_init_accepts_explicit_canonical_category_path(tmp_path: Path) -> None:
    root = tmp_path / "content"
    assert main(["init", "--type", "driving-route", "--project",
                 "videos/route-journey/driving-route/demo", "--content-root", str(root)]) == 0
    assert (root / "videos" / "route-journey" / "driving-route" / "demo" / "project.json").is_file()


def test_relocate_moves_flat_categorized_type_into_category(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    marker = root / ".agents" / "skills" / "material2video" / "SKILL.md"
    marker.parent.mkdir(parents=True)
    marker.write_text("skill", encoding="utf-8")
    create_typed_project(root / "videos" / "driving-route" / "demo", "driving-route")
    source = root / "videos" / "driving-route" / "demo"

    result = relocate(source)

    assert result.target == root / "videos" / "route-journey" / "driving-route" / "demo"
    assert not source.exists()
    assert (result.target / "project.json").is_file()
    assert result.backup.is_dir()


def test_relocate_reports_project_already_in_canonical_category_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    marker = root / ".agents" / "skills" / "material2video" / "SKILL.md"
    marker.parent.mkdir(parents=True)
    marker.write_text("skill", encoding="utf-8")
    source = root / "videos" / "route-journey" / "road-trip" / "demo"
    create_typed_project(source, "road-trip")

    with pytest.raises(M2VError, match="已经位于标准目录"):
        relocate(source)


def test_relocate_moves_project_and_outputs_with_complete_backup(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    marker = root / ".agents" / "skills" / "material2video" / "SKILL.md"
    marker.parent.mkdir(parents=True)
    marker.write_text("skill", encoding="utf-8")
    create_typed_project(root / "videos" / "demo", "financial-timeseries")
    source = root / "videos" / "demo"
    (source / "outputs" / "media").mkdir(parents=True)
    (source / "outputs" / "media" / "media.json").write_text("{}", encoding="utf-8")
    original_files = {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*") if p.is_file()}

    result = relocate(source)

    assert result.target == root / "videos" / "financial-timeseries" / "demo"
    assert not source.exists()
    assert {p.relative_to(result.target).as_posix(): p.read_bytes() for p in result.target.rglob("*") if p.is_file()} == original_files
    assert {p.relative_to(result.backup).as_posix(): p.read_bytes() for p in result.backup.rglob("*") if p.is_file()} == original_files


def test_relocate_supports_external_content_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    marker = repo / ".agents" / "skills" / "material2video" / "SKILL.md"
    marker.parent.mkdir(parents=True)
    marker.write_text("skill", encoding="utf-8")
    content = tmp_path / "content"
    source = content / "videos" / "demo"
    create_typed_project(source, "general")

    result = relocate(source, content_root=content)

    assert result.target == content / "videos" / "general" / "demo"
    assert not source.exists()
    assert result.backup.is_dir()


def test_relocate_keeps_conflicting_source_file_and_retries(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    marker = root / ".agents" / "skills" / "material2video" / "SKILL.md"
    marker.parent.mkdir(parents=True)
    marker.write_text("skill", encoding="utf-8")
    create_typed_project(root / "videos" / "demo", "financial-timeseries")
    source = root / "videos" / "demo"
    (source / "unique.txt").write_text("move", encoding="utf-8")
    target = root / "videos" / "financial-timeseries" / "demo"
    target.mkdir(parents=True)
    (target / "unique.txt").write_text("keep-target", encoding="utf-8")

    first = relocate(source)
    assert first.conflicts == (source / "unique.txt",)
    assert (target / "unique.txt").read_text(encoding="utf-8") == "keep-target"
    assert (source / "unique.txt").read_text(encoding="utf-8") == "move"
    assert (target / "project.json").is_file()
    assert len(list(source.parent.glob("demo.m2v-relocation-backup-*"))) == 1

    (target / "unique.txt").unlink()
    second = relocate(source)
    assert not second.conflicts
    assert not source.exists()
    assert (target / "unique.txt").read_text(encoding="utf-8") == "move"
    assert (target / "project.json").is_file()
    assert first.backup == second.backup


def test_relocate_rejects_non_project_source_without_moving_it(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    marker = root / ".agents" / "skills" / "material2video" / "SKILL.md"
    marker.parent.mkdir(parents=True)
    marker.write_text("skill", encoding="utf-8")
    source = root / "videos" / "legacy"
    source.mkdir(parents=True)
    (source / "article.md").write_text("source", encoding="utf-8")
    with pytest.raises(M2VError, match="project.json"):
        relocate(source)
    assert (source / "article.md").is_file()


def test_same_named_projects_receive_distinct_stable_ids(tmp_path: Path) -> None:
    first = tmp_path / "one" / "作品"
    second = tmp_path / "two" / "作品"
    first_id = load_project(create_typed_project(first, "general").parent)[1]["id"]
    second_id = load_project(create_typed_project(second, "general").parent)[1]["id"]
    assert first_id != second_id
    assert load_project(first)[1]["id"] == first_id


def test_registered_test_type_appears_without_editing_cli_dispatch(monkeypatch, capsys) -> None:
    monkeypatch.setattr(registry, "_registry", {})
    noop = lambda *_args, **_kwargs: None
    registry.register(VideoType("test-only", noop, noop, noop, noop))
    assert main(["types"]) == 0
    assert '"type": "test-only"' in capsys.readouterr().out


def test_review_record_requires_every_type_specific_criterion(tmp_path: Path, monkeypatch) -> None:
    from m2v.types.general.adapter import TYPE as general_type

    monkeypatch.setattr(registry, "_registry", {"general": general_type})
    root = tmp_path / "general"
    root.mkdir()
    preview_file = root / "outputs" / "previews" / "video.mp4"
    preview_file.parent.mkdir(parents=True)
    preview_file.write_bytes(b"preview")
    manifest = {"id": "review-test", "type": "general"}
    prepared = {"preparedFingerprint": "fingerprint", "props": {"compiledScenes": [
        {"id": "a", "template": "point"}],}, "audio": {"segments": [{"sceneId": "master"}]}}
    criteria = _review_criteria(root, manifest, prepared)
    evidence = {name: "已逐项检查" for name in criteria}
    record = {"schemaVersion": 1, "status": "pass", "projectId": manifest["id"],
        "preparedFingerprint": prepared["preparedFingerprint"], "criteria": criteria, "evidence": evidence,
        "candidate": {"key": "key", "preparedFingerprint": prepared["preparedFingerprint"],
                    "path": str(preview_file.resolve()),
                    "sha256": hashlib.sha256(preview_file.read_bytes()).hexdigest()}}
    record["candidate"]["frames"] = prepared["durationInFrames"] = 30
    (root / "outputs" / "delivery.json").write_text(json.dumps(record["candidate"]), encoding="utf-8")
    (root / "outputs" / "review.json").write_text(json.dumps(record), encoding="utf-8")
    _require_review(root, manifest, prepared)

    evidence.pop("narrationSync")
    (root / "outputs" / "review.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(M2VError, match="当前类型的每项结论"):
        _require_review(root, manifest, prepared)


def test_preview_outside_the_project_root_needs_no_record(
    tmp_path: Path, monkeypatch
) -> None:
    """预演可以显式输出到作品根之外；片段检查不再写预演记录。

    示例作品的默认产物也在作品根下的 `outputs/`，显式外部输出只是可选工具，
    因此作品根之外的输出目录不影响片段检查。
    """
    root = tmp_path / "examples" / "demo"
    root.mkdir(parents=True)
    manifest = {"schemaVersion": 1, "id": "demo", "type": "outside-preview"}
    prepared = {"preparedFingerprint": "fp", "durationInFrames": 30}
    preview = tmp_path / "custom" / "previews" / "video.mp4"
    preview.parent.mkdir(parents=True)
    preview.write_bytes(b"full preview")
    # prepare 已经写过 outputs/prepared.json，预演记录沿用同一个目录
    (root / "outputs").mkdir()

    video_type = VideoType(
        "outside-preview", lambda *_: None, lambda *_: None,
        lambda *_args, **_kwargs: preview, lambda *_: "rendered.mp4",
    )
    register_synthetic_type(monkeypatch, "outside-preview", "预演落在作品根之外")
    monkeypatch.setattr(registry, "_registry", {"outside-preview": video_type})
    monkeypatch.setattr("m2v.commands.load_project", lambda _path: (root, manifest))
    monkeypatch.setattr("m2v.commands.load_current_prepared", lambda *_args: prepared)

    assert main(["preview", "--project", str(root)]) == 0

    assert preview.is_file()
    assert not (root / "outputs/preview-record.json").exists()


def test_unified_review_template_and_export_run_type_hooks(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[str] = []
    root = tmp_path / "hook-project"
    root.mkdir()
    manifest = {"schemaVersion": 1, "id": "hook-project", "type": "review-hook"}
    prepared = {"preparedFingerprint": "hook-fingerprint", "durationInFrames": 30, "width": 1080, "height": 1920, "fps": 60}
    preview = root / "outputs" / "previews" / "video.mp4"
    preview.parent.mkdir(parents=True)
    preview.write_bytes(b"full preview")
    (root / "outputs" / "delivery.json").write_text(json.dumps({
        "key": "key", "path": str(preview.resolve()),
        "sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
        "preparedFingerprint": prepared["preparedFingerprint"], "frames": 30,
    }), encoding="utf-8")

    def type_review_template(*_args) -> None:
        calls.append("template")

    def type_review_gate(*_args) -> None:
        calls.append("gate")

    final_video = root / "outputs" / "rendered.mp4"
    old_video = root / "outputs" / "old.mp4"
    old_video.write_bytes(b"old")

    def render_video(*_args) -> Path:
        final_video.write_bytes(b"new final")
        return final_video

    video_type = VideoType(
        "review-hook", lambda *_: None, lambda *_: None,
        lambda *_: preview, render_video,
        review_gate=type_review_gate,
        review_criteria=lambda *_: {"specialized": "专用评审"},
        review_template=type_review_template,
    )
    register_synthetic_type(monkeypatch, "review-hook", "review hook test")
    monkeypatch.setattr(registry, "_registry", {"review-hook": video_type})
    monkeypatch.setattr("m2v.commands.load_project", lambda _path: (root, manifest))
    monkeypatch.setattr("m2v.commands.load_current_prepared", lambda *_args: prepared)

    assert main(["review-template", "--project", str(root)]) == 0
    generic = json.loads((root / "outputs" / "review.json").read_text(encoding="utf-8"))
    assert generic["criteria"] == {"specialized": "专用评审"}
    assert calls == ["template"]

    generic["status"] = "pass"
    generic["evidence"] = {"specialized": "已按类型材料逐项检查"}
    (root / "outputs" / "review.json").write_text(json.dumps(generic), encoding="utf-8")
    assert main(["review", "--project", str(root)]) == 0
    assert calls == ["template", "gate"]
    assert main(["render", "--project", str(root)]) == 0
    assert calls == ["template", "gate", "gate"]
    assert "rendered.mp4" in capsys.readouterr().out
    assert final_video.read_bytes() == b"new final"
    assert not old_video.exists()
    assert not preview.exists()
    assert (root / "outputs" / "review.json").is_file()


def test_type_without_manual_review_uses_type_gate_and_status(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[str] = []
    root = tmp_path / "auto-review"
    root.mkdir()
    manifest = {"schemaVersion": 1, "id": "auto-review", "type": "auto-review"}
    prepared = {"preparedFingerprint": "auto-fingerprint", "durationInFrames": 30, "width": 1080, "height": 1920, "fps": 60}
    outputs = root / "outputs"
    outputs.mkdir()
    preview = outputs / "previews" / "preview.mp4"
    preview.parent.mkdir()
    preview.write_bytes(b"full preview")
    record = {"status": "delivered", "key": "key", "path": str(preview.resolve()), "sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
              "preparedFingerprint": prepared["preparedFingerprint"], "frames": 30}
    (outputs / "delivery.json").write_text(json.dumps(record), encoding="utf-8")
    final = outputs / "final.mp4"

    def gate(*_args): calls.append("gate")
    def render(*_args): final.write_bytes(b"final"); return final

    video_type = VideoType("auto-review", lambda *_: None, lambda *_: None,
        lambda *_args, **_kwargs: preview, render, review_gate=gate, manual_review_available=False)
    register_synthetic_type(monkeypatch, "auto-review", "自动验收测试")
    monkeypatch.setattr(registry, "_registry", {"auto-review": video_type})
    monkeypatch.setattr("m2v.commands.load_project", lambda _path: (root, manifest))
    monkeypatch.setattr("m2v.commands.load_current_prepared", lambda *_args: prepared)

    assert main(["review-template", "--project", str(root)]) == 0
    assert not (outputs / "review.json").exists()
    assert main(["review", "--project", str(root)]) == 0
    assert main(["render", "--project", str(root)]) == 0
    assert calls == ["gate", "gate"]
    assert final.read_bytes() == b"final"
    assert main(["status", "--project", str(root)]) == 0
    output = capsys.readouterr().out
    assert '"not-required"' in output


def test_financial_status_without_delivery_record_reports_prepared(tmp_path: Path, monkeypatch) -> None:
    from m2v.commands import _status
    from m2v.types.financial.adapter import TYPE as financial_type
    from dataclasses import replace

    root = tmp_path / "finance"
    record_dir = root / "outputs" / "previews"
    record_dir.mkdir(parents=True)
    preview = record_dir / "preview.mp4"
    preview.write_bytes(b"full preview")
    (record_dir / "preview-record.json").write_text(json.dumps({
        "path": "outputs/previews/preview.mp4", "sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
        "preparedFingerprint": "fp", "materialsAndAssetsSha256": "bound-digest",
    }), encoding="utf-8")
    manifest = {"id": "finance", "type": "financial-timeseries"}
    monkeypatch.setattr("m2v.commands.load_current_prepared", lambda *_: {"preparedFingerprint": "fp"})
    monkeypatch.setattr(registry, "_registry", {
        "financial-timeseries": replace(financial_type, review_gate=lambda *_: None)})
    result = _status(root, manifest)
    assert result["stage"] == "prepared"
    assert "candidate" not in result
    assert result["review"]["status"] == "not-required"


def test_failed_unified_render_does_not_clean_old_outputs(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "failed-render"
    outputs = root / "outputs"
    outputs.mkdir(parents=True)
    old_video = outputs / "old.mp4"
    old_video.write_bytes(b"still valid")
    manifest = {"schemaVersion": 1, "id": "failed-render", "type": "render-failure"}

    def fail_render(*_args) -> Path:
        raise M2VError("render failed")

    video_type = VideoType(
        "render-failure", lambda *_: None, lambda *_: None,
        lambda *_args, **_kwargs: None, fail_render,
    )
    register_synthetic_type(monkeypatch, "render-failure", "失败渲染测试")
    monkeypatch.setattr(registry, "_registry", {"render-failure": video_type})
    monkeypatch.setattr("m2v.commands.load_project", lambda _path: (root, manifest))
    monkeypatch.setattr("m2v.commands.load_current_prepared", lambda *_args: {"preparedFingerprint": "fp"})
    monkeypatch.setattr("m2v.commands._require_type_review", lambda *_args: None)

    assert main(["render", "--project", str(root)]) == 1
    assert old_video.read_bytes() == b"still valid"
    assert "render failed" in capsys.readouterr().err
