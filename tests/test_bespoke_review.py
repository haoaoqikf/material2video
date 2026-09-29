from __future__ import annotations

from a2v.bespoke_review import DIMENSIONS, review


def _storyboard(code: bool = True) -> dict:
    renderer = {"kind": "code", "module": "scene"} if code else {"kind": "tree"}
    return {"scenes": [{"id": "one", "renderer": renderer}, {"id": "two", "renderer": {"kind": "tree"}}]}


def _review_text(scores: tuple[int, ...] = (4, 4, 4, 4, 4), evidence: str = "对象依 beat 回流，末帧稳定") -> str:
    values = " | ".join(str(score) for score in scores)
    return (
        "## 定制动画动态评审\n\n状态：启用\n\n"
        "| 场景 | 焦点清晰度 | 动作解释力 | 节奏变化 | 转场连贯性 | 结果可读性 | 依据 |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |\n"
        f"| one | {values} | {evidence} |\n"
        f"| two | {values} | {evidence} |\n"
    )


def test_missing_review_is_pending_for_custom_work(tmp_path):
    result = review(tmp_path / "review.md", _storyboard())
    assert result["status"] == "待评审"
    assert result["missingScenes"] == ["one", "two"]
    assert result["publishable"] is False


def test_all_scenes_with_evidence_and_four_or_more_pass(tmp_path):
    path = tmp_path / "review.md"
    path.write_text(_review_text(), encoding="utf-8")
    result = review(path, _storyboard())
    assert result["status"] == "通过"
    assert result["publishable"] is True


def test_any_score_below_four_blocks_publish(tmp_path):
    path = tmp_path / "review.md"
    path.write_text(_review_text((5, 3, 5, 5, 5)), encoding="utf-8")
    result = review(path, _storyboard())
    assert result["status"] == "不通过"
    assert result["belowThreshold"] == [
        {"scene": scene, "dimension": DIMENSIONS[1], "score": 3} for scene in ("one", "two")
    ]
    assert result["publishable"] is False


def test_missing_evidence_keeps_scene_pending(tmp_path):
    path = tmp_path / "review.md"
    path.write_text(_review_text(evidence=""), encoding="utf-8")
    assert review(path, _storyboard())["status"] == "待评审"


def test_tree_only_work_does_not_require_custom_review(tmp_path):
    result = review(tmp_path / "review.md", _storyboard(code=False))
    assert result["required"] is False
    assert result["status"] == "不适用"
    assert result["publishable"] is True
