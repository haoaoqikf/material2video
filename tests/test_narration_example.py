"""三个示例均使用独立旁白与屏幕摘要。"""
import json
from pathlib import Path
from m2v.types.general import explainer
ROOT = Path(__file__).resolve().parents[1]


def test_examples_use_bound_narration_and_distinct_screen_copy():
    for file in (ROOT / "examples").glob("*/storyboard.json"):
        board = json.loads(file.read_text(encoding="utf-8"))
        explainer.validate(board, file.parent)
        for scene in board["scenes"]:
            assert scene["template"] == "code"
            narration = "".join(p["text"] for p in scene["narrationSegments"])
            # 画面标题只是元数据：它不得等同于旁白，也不得代替旁白。
            title = scene["content"].get("title")
            if title:
                assert title != narration, f"{file.parent.name}/{scene['id']} 的画面标题照抄了旁白"
            assert (file.parent / scene["content"]["entry"]).is_file()
