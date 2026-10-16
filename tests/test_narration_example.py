"""三个示例均使用独立旁白与屏幕摘要。"""
import json
from pathlib import Path
from m2v.types.general import explainer
ROOT=Path(__file__).resolve().parents[1]


def test_examples_use_bound_narration_and_distinct_screen_copy():
    for file in (ROOT/"examples").glob("*/storyboard.json"):
        board=json.loads(file.read_text(encoding="utf-8"));explainer.validate(board,file.parent)
        for scene in board["scenes"]:
            narration="".join(p["text"] for p in scene["narrationSegments"])
            assert scene["content"]["title"] != narration
            if scene["template"] in {"image", "video", "code"}:
                # 素材幕与代码幕可以没有旁白，也可以只写画面标题。
                assert explainer.elements(scene) == ([scene["content"]["caption"]] if "caption" in scene["content"] else [])
                continue
            assert narration and explainer.elements(scene)
