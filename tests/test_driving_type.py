"""自驾路线类型接入：初始化默认值、离线生命周期与命令边界。"""
from __future__ import annotations

import json

import pytest

from m2v.cli import main
from m2v.core.project import load_current_prepared, load_project
from driving_helpers import request_document, write_project


def test_init_writes_independent_materials_and_portrait_defaults(tmp_path):
    assert main(["init", "--type", "driving-route", "--project", "demo",
                 "--content-root", str(tmp_path)]) == 0
    root, manifest = load_project(tmp_path / "videos/route-journey/driving-route/demo")
    assert manifest["materials"] == {"request": "request.json", "route": "route.json"}
    assert (manifest["output"]["width"], manifest["output"]["height"]) == (1080, 1920)
    assert manifest["output"]["fps"] == 30
    request = json.loads((root / "request.json").read_text(encoding="utf-8"))
    assert request["schemaVersion"] == 2
    assert request["durationSeconds"] == 30
    assert request["strategy"] == "highway-first"
    assert request["sourceUsage"]["mapTiles"] is False
    route = json.loads((root / "route.json").read_text(encoding="utf-8"))
    assert route["schemaVersion"] == 3
    assert route["route"] is None
    assert route["cost"] is None
    assert not (root / "storyboard.json").exists()


def test_validate_and_prepare_work_offline_without_a_key(tmp_path, monkeypatch, capsys):
    root = write_project(tmp_path)
    manifest = json.loads((root / "project.json").read_text(encoding="utf-8"))
    monkeypatch.delenv("M2V_AMAP_KEY", raising=False)
    assert main(["validate", "--project", str(root)]) == 0
    assert "材料校验通过" in capsys.readouterr().out
    assert main(["prepare", "--project", str(root)]) == 0
    prepared = load_current_prepared(root, manifest)
    assert prepared["compositionId"] == "DrivingRoute"
    assert prepared["durationInFrames"] == 900
    assert prepared["fps"] == 30
    assert (prepared["width"], prepared["height"]) == (1080, 1920)
    assert set(prepared["inputs"]) == {"request", "route"}
    assert prepared["audio"] == {}
    assert prepared["props"]["originLabel"] == "上海"
    assert prepared["props"]["cost"]["durationSeconds"] == 3600
    assert prepared["props"]["cities"][0]["name"] == "上海市"


def test_explicit_duration_only_changes_total_frames(tmp_path, monkeypatch):
    request = request_document()
    request["durationSeconds"] = 12
    root = write_project(tmp_path, request=request)
    assert main(["prepare", "--project", str(root)]) == 0
    manifest = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert load_current_prepared(root, manifest)["durationInFrames"] == 360


def test_explicit_sixty_seconds_uses_1800_frames(tmp_path, monkeypatch):
    request = request_document()
    request["durationSeconds"] = 60
    root = write_project(tmp_path, request=request)
    assert main(["prepare", "--project", str(root)]) == 0
    manifest = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert load_current_prepared(root, manifest)["durationInFrames"] == 1800


def test_status_reports_prepared_without_network(tmp_path):
    root = write_project(tmp_path)
    assert main(["prepare", "--project", str(root)]) == 0
    assert main(["status", "--project", str(root)]) == 0


def test_review_template_explains_automatic_acceptance(tmp_path, capsys):
    root = write_project(tmp_path)
    assert main(["prepare", "--project", str(root)]) == 0
    assert main(["review-template", "--project", str(root)]) == 0
    assert "不提供人工评审模板" in capsys.readouterr().out


def test_fetch_is_the_only_type_auxiliary_command(tmp_path):
    with pytest.raises(SystemExit) as error:
        main(["driving-route", "plan", "--project", str(tmp_path)])
    assert error.value.code == 2
