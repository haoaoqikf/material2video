from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from a2v.cli import main
from a2v.core.errors import A2VError
from a2v.core.project import create_project, load_project
from a2v.cli import _require_review, _review_criteria
from a2v.types.migration import migrate
from a2v.types import registry
from a2v.types.registry import VideoType
from conftest import v4_storyboard


def test_init_writes_all_financial_material_templates_under_content_root(tmp_path: Path) -> None:
    root = tmp_path / "content"
    assert main(["init", "--type", "financial-timeseries", "--project", "videos/demo", "--content-root", str(root)]) == 0
    project_root, manifest = load_project(root / "videos" / "demo")
    assert set(manifest["materials"]) == {"request", "prices", "plan"}
    assert all((project_root / name).is_file() for name in manifest["materials"].values())
    with open(project_root / "animation-plan.json", encoding="utf-8") as stream:
        assert json.load(stream)["schemaVersion"] == 7


def test_article_v4_migration_is_backup_first_and_repeat_fails(tmp_path: Path) -> None:
    root = tmp_path / "作品一"
    root.mkdir()
    storyboard = v4_storyboard()
    (root / "storyboard.json").write_text(json.dumps(storyboard), encoding="utf-8")
    (root / "production.json").write_text('{"status":"pass"}', encoding="utf-8")
    old_preview_record = root / "outputs" / "previews" / "preview-record.json"
    old_preview_record.parent.mkdir(parents=True)
    old_preview_record.write_text('{"status":"pass"}', encoding="utf-8")
    manifest_path = migrate(root, "article-v4")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["type"] == "article-narrative"
    history = root / "outputs" / "history"
    archived_record = next(history.glob("migration-*/migration.json"))
    archive_data = json.loads(archived_record.read_text(encoding="utf-8"))
    assert archive_data["status"] == "historical"
    assert not (root / "production.json").exists()
    assert not old_preview_record.exists()
    assert (archived_record.parent / "production.json").is_file()
    assert (archived_record.parent / "outputs/previews/preview-record.json").is_file()
    assert len(list(tmp_path.glob("作品一.a2v-backup-*"))) == 1
    try:
        migrate(root, "article-v4")
    except A2VError as exc:
        assert "重复迁移" in str(exc)
    else:
        raise AssertionError("重复迁移必须失败")


def test_same_named_projects_receive_distinct_stable_ids(tmp_path: Path) -> None:
    first = tmp_path / "one" / "作品"
    second = tmp_path / "two" / "作品"
    first_id = load_project(create_project(first, "general").parent)[1]["id"]
    second_id = load_project(create_project(second, "general").parent)[1]["id"]
    assert first_id != second_id
    assert load_project(first)[1]["id"] == first_id


def test_migration_failure_restores_old_records_and_materials(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "rollback"
    root.mkdir()
    (root / "storyboard.json").write_text(json.dumps(v4_storyboard()), encoding="utf-8")
    (root / "production.json").write_text('{"status":"pass"}', encoding="utf-8")
    production_before = (root / "production.json").read_bytes()
    storyboard_before = (root / "storyboard.json").read_bytes()
    write_text = Path.write_text

    def fail_history(path: Path, *args, **kwargs):
        if path.name == "migration.json":
            raise OSError("simulated history write failure")
        return write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_history)
    with pytest.raises(OSError, match="simulated history write failure"):
        migrate(root, "article-v4")
    assert not (root / "project.json").exists()
    assert (root / "production.json").read_bytes() == production_before
    assert (root / "storyboard.json").read_bytes() == storyboard_before


def test_registered_test_type_appears_without_editing_cli_dispatch(monkeypatch, capsys) -> None:
    monkeypatch.setattr(registry, "_registry", {})
    noop = lambda *_args, **_kwargs: None
    registry.register(VideoType("test-only", "测试扩展类型", noop, noop, noop, noop))
    assert main(["types"]) == 0
    assert '"type": "test-only"' in capsys.readouterr().out


def test_review_record_requires_every_type_specific_criterion(tmp_path: Path, monkeypatch) -> None:
    from a2v.types.general.adapter import TYPE as general_type

    monkeypatch.setattr(registry, "_registry", {"general": general_type})
    root = tmp_path / "general"
    root.mkdir()
    preview_file = root / "outputs" / "previews" / "video.mp4"
    preview_file.parent.mkdir(parents=True)
    preview_file.write_bytes(b"preview")
    manifest = {"id": "review-test", "type": "general"}
    prepared = {"preparedFingerprint": "fingerprint", "props": {"compiledScenes": [
        {"id": "code", "type": "code"}],}, "audio": {"segments": [{"sceneId": "code"}]}}
    criteria = _review_criteria(root, manifest, prepared)
    evidence = {name: "已逐项检查" for name in criteria}
    record = {"schemaVersion": 1, "status": "pass", "projectId": manifest["id"],
        "preparedFingerprint": prepared["preparedFingerprint"], "criteria": criteria, "evidence": evidence,
        "preview": {"preparedFingerprint": prepared["preparedFingerprint"],
                    "path": "outputs/previews/video.mp4",
                    "sha256": hashlib.sha256(preview_file.read_bytes()).hexdigest()}}
    (root / "outputs" / "review.json").write_text(json.dumps(record), encoding="utf-8")
    _require_review(root, manifest, prepared)

    evidence.pop("audioSubtitles")
    (root / "outputs" / "review.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(A2VError, match="当前类型的每项结论"):
        _require_review(root, manifest, prepared)


def test_unified_review_template_and_export_run_type_hooks(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[str] = []
    root = tmp_path / "hook-project"
    root.mkdir()
    manifest = {"schemaVersion": 1, "id": "hook-project", "type": "review-hook"}
    prepared = {"preparedFingerprint": "hook-fingerprint"}
    preview = root / "outputs" / "previews" / "video.mp4"
    preview.parent.mkdir(parents=True)
    preview.write_bytes(b"full preview")
    (root / "outputs" / "preview-record.json").write_text(json.dumps({
        "path": "outputs/previews/video.mp4",
        "sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
        "preparedFingerprint": prepared["preparedFingerprint"],
    }), encoding="utf-8")

    def type_review_template(*_args) -> None:
        calls.append("template")

    def type_review_gate(*_args) -> None:
        calls.append("gate")

    video_type = VideoType(
        "review-hook", "review hook test", lambda *_: None, lambda *_: None,
        lambda *_: preview, lambda *_: "rendered.mp4",
        review_gate=type_review_gate,
        review_criteria=lambda *_: {"specialized": "专用评审"},
        review_template=type_review_template,
    )
    monkeypatch.setattr(registry, "_registry", {"review-hook": video_type})
    monkeypatch.setattr("a2v.cli.load_project", lambda _path: (root, manifest))
    monkeypatch.setattr("a2v.cli.load_current_prepared", lambda *_args: prepared)

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
