"""七部示例的归属、材料、依赖与打包边界。"""
from __future__ import annotations

import json

import pytest

from helpers.examples import EXAMPLE_PATHS, TYPE_EXAMPLES
from m2v.cli import main
from m2v.core.project import load_project
from m2v.production.dependencies import scene_sources
from m2v.types.scene_film.code_scenes.config import build_scene


@pytest.mark.parametrize("slug", sorted(EXAMPLE_PATHS))
def test_example_materials_and_scene_imports(slug, tmp_path):
    root = EXAMPLE_PATHS[slug]
    project_root, project = load_project(root)
    assert project_root == root.resolve()
    assert project["type"] == root.parent.name
    assert slug in TYPE_EXAMPLES[project["type"]]
    board = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    assert board["version"] == board["schemaVersion"] == 9
    assert "style" not in project
    assert main(["validate", "--project", str(root)]) == 0
    for scene in board["scenes"]:
        deps = scene_sources(root, scene)
        assert "style" not in deps
        assert not deps["conservativeReasons"]
        build_scene(root, scene, tmp_path / scene["id"])
