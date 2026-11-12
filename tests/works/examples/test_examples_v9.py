"""随附示例的归属、材料、依赖与打包边界。"""
from __future__ import annotations

import json

import pytest

from helpers.examples import EXAMPLE_PATHS, TYPE_EXAMPLES
from m2v.cli import main
from m2v.core.project import load_project
from m2v.production.dependencies import scene_sources
import subprocess


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
        # 动态素材 ID（如从普通函数调用 useMediaAsset）保守绑定全部登记素材；
        # 除此之外不应出现未解析本地引用或动态导入。
        assert set(deps["conservativeReasons"]) <= {"动态素材 ID，保守绑定全部登记素材"}
        work = tmp_path / scene["id"]
        work.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(["node", str(root / "scripts/build-code-scene.mjs"), str(root),
                                 scene["content"]["entry"], str(work)],
                                cwd=root, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=120)
        assert result.returncode == 0, result.stderr[-2000:]
