"""正式暗场论证风格包：清单、组件契约、指纹与《接》示例。"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from m2v.core import styles
from m2v.types.general import explainer
from m2v.types.general.code_scenes import build_scene

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "styles" / "dark-proof"
EXAMPLE = PACKAGE / "examples" / "compound-connect"


def test_narration_is_optional():
    from m2v.core.styles import check_requirements
    package = styles.load_style("dark-proof")
    check_requirements(package, has_narration=False)
    check_requirements(package, has_narration=True)


def test_shipped_example_is_a_silent_v8_work():
    project = json.loads((EXAMPLE / "project.json").read_text(encoding="utf-8"))
    assert project["type"] == "general"
    assert project["style"] == {"id": "dark-proof"}
    assert (project["output"]["width"], project["output"]["height"], project["output"]["fps"]) == (1920, 1080, 30)
    board = explainer.load(EXAMPLE, project)
    explainer.validate(board, EXAMPLE, project)
    assert board["version"] == 8 and board["schemaVersion"] == 8


def test_example_media_recipe_is_complete():
    recipe = json.loads((EXAMPLE / "assets" / "recipe.json").read_text(encoding="utf-8"))
    assert recipe["schemaVersion"] == 1
    for item in recipe["assets"]:
        assert item["transform"] == "generate"
        assert item["sampleRateHz"] == 24000 and item["channels"] == 1
        assert item["license"] == "CC0-1.0"
        assert re.fullmatch(r"[0-9a-f]{64}", item["expectedSha256"])


@pytest.mark.slow
def test_example_scene_builds_with_the_package(tmp_path):
    if shutil.which("node") is None:
        pytest.skip("需要 Node.js")
    project = json.loads((EXAMPLE / "project.json").read_text(encoding="utf-8"))
    board = explainer.load(EXAMPLE, project)
    work = tmp_path / "work"
    work.mkdir()
    inputs = build_scene(EXAMPLE, board["scenes"][0], work)
    assert inputs["style"] == styles.load_style("dark-proof")["identity"]["fingerprint"]
    assert (work / "scene.js").is_file()
