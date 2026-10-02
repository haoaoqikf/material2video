"""水箱示例体现当前标准的全片持续场景与语义节拍。"""

from __future__ import annotations

import json
from pathlib import Path

from a2v import article_text, storyboard_v4

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/buffer-smoothing/storyboard.json"
DOC = ROOT / ".agents/skills/article2video/references/article-to-storyboard.md"


def _example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_example_passes_v4_strict_validation():
    report = storyboard_v4.validate(_example())
    assert not report.errors, [issue.format() for issue in report.issues]


def test_multiple_stages_share_one_persistent_world():
    board = _example()
    assert len(board["stages"]) > 1
    assert board["world"]["id"] and board["world"]["renderer"]
    assert all("renderer" not in stage and "sceneTree" not in stage for stage in board["stages"])


def test_every_stage_has_segmented_narration_and_semantic_beats():
    for stage in _example()["stages"]:
        assert stage["narrationSegments"] and stage["beats"]
        beat_ids = {beat["id"] for beat in stage["beats"]}
        assert all(segment["beatId"] in beat_ids for segment in stage["narrationSegments"])


def test_final_narration_obeys_the_standard_character_range():
    board = _example()
    narration = "".join(segment["text"] for stage in board["stages"] for segment in stage["narrationSegments"])
    assert 130 <= article_text.count_characters(narration) <= 170


def test_example_uses_one_world_metaphor_across_stages():
    board = _example()
    assert board["world"]["metaphor"]
    assert all(stage["visualIntent"]["primaryObject"] for stage in board["stages"])


def test_creation_reference_links_the_example_and_new_workflow():
    text = DOC.read_text(encoding="utf-8")
    assert "输入审查 → 核心观点与隐喻设计" in text
