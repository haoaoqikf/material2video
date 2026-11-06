"""五类身份、v2/v9 材料和旧入口拒绝。"""
from __future__ import annotations

import json

import pytest

from m2v.cli import main
from m2v.core.errors import M2VError
from m2v.core.project import create_project, load_project, load_current_prepared
from m2v.type_system.catalog import catalog

KINDS = ("text-motion", "data-evolution", "principle-metaphor", "spatial-3d", "documentary-edit")


def edit(path, mutate):
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_catalog_has_only_five_types(capsys):
    assert catalog().names() == KINDS
    assert main(["types"]) == 0
    listing = json.loads(capsys.readouterr().out)
    assert {item["type"] for item in listing} == set(KINDS)
    assert all("category" not in item for item in listing)


@pytest.mark.parametrize("kind", KINDS)
def test_each_type_initializes_validates_and_prepares(tmp_path, kind):
    assert main(["init", "--type", kind, "--project", "demo", "--content-root", str(tmp_path)]) == 0
    root, project = load_project(tmp_path / "videos" / kind / "demo")
    board = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    assert project["schemaVersion"] == 2 and project["type"] == kind
    assert board["version"] == board["schemaVersion"] == 9
    assert main(["validate", "--project", str(root)]) == 0
    assert main(["prepare", "--project", str(root)]) == 0
    prepared = load_current_prepared(root, project)
    assert prepared["contractVersion"] == 2
    assert prepared["compositionId"] == "SceneFilm"


@pytest.mark.parametrize("kind", ("general", "financial-timeseries", "building-construction", "vehicle-showcase", "map-trajectory", "situational-story"))
def test_old_or_extra_types_are_rejected(tmp_path, kind):
    assert main(["init", "--type", kind, "--project", "demo", "--content-root", str(tmp_path)]) == 2
    with pytest.raises(M2VError, match="未知视频类型"):
        create_project(tmp_path / kind, kind, {"storyboard": "storyboard.json"})


def test_old_project_storyboard_style_and_prepared_are_rejected(tmp_path):
    assert main(["init", "--type", "text-motion", "--project", "demo", "--content-root", str(tmp_path)]) == 0
    root = tmp_path / "videos/text-motion/demo"
    project_file = root / "project.json"
    edit(project_file, lambda value: value.update(style={"id": "vibe-night"}))
    with pytest.raises(M2VError, match="style"):
        load_project(root)
    edit(project_file, lambda value: value.pop("style"))
    edit(project_file, lambda value: value.update(category="obsolete"))
    with pytest.raises(M2VError, match="category"):
        load_project(root)
    edit(project_file, lambda value: value.pop("category"))
    edit(project_file, lambda value: value.update(schemaVersion=1))
    with pytest.raises(M2VError, match="schemaVersion"):
        load_project(root)
    edit(project_file, lambda value: value.update(schemaVersion=2))
    board_file = root / "storyboard.json"
    edit(board_file, lambda value: value.update(version=8, schemaVersion=8))
    assert main(["validate", "--project", str(root)]) == 1
    edit(board_file, lambda value: value.update(version=9, schemaVersion=9))
    assert main(["prepare", "--project", str(root)]) == 0
    edit(root / "outputs/prepared.json", lambda value: value.update(contractVersion=1))
    with pytest.raises(M2VError):
        load_current_prepared(root, load_project(root)[1])


def test_removed_commands_are_not_registered(capsys):
    for command in ("general", "styles", "migrate", "relocate", "financial"):
        with pytest.raises(SystemExit):
            main([command])
        assert "invalid choice" in capsys.readouterr().err
