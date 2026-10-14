"""三个示例均使用独立旁白与屏幕摘要。"""
import json
from pathlib import Path
from m2v.types.article import explainer
ROOT=Path(__file__).resolve().parents[1]


def test_examples_use_bound_narration_and_distinct_screen_copy():
    for file in (ROOT/"examples").glob("*/storyboard.json"):
        board=json.loads(file.read_text(encoding="utf-8"));explainer.validate(board,file.parent)
        for scene in board["scenes"]:
            narration="".join(p["text"] for p in scene["narrationSegments"])
            assert narration and scene["content"]["title"] != narration
            assert explainer.elements(scene)
