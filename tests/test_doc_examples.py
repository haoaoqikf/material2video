"""文章到分镜手册应准确描述当前 v4 单场景制作链路。"""

from pathlib import Path

REFERENCE = Path(__file__).resolve().parents[1] / ".agents/skills/material2video/references/article-to-storyboard.md"


def test_workflow_starts_with_input_review_and_designs_one_world():
    text = REFERENCE.read_text(encoding="utf-8")
    assert "输入审查 → 核心观点与隐喻设计 → 分镜及动画编排" in text
    assert "同一个视觉世界" in text and "阶段代表推理进展" in text


def test_length_and_runtime_gates_are_documented_separately():
    text = REFERENCE.read_text(encoding="utf-8")
    assert "130～170字" in text and "35～45秒" in text and "实际时长" in text


def test_candidate_requires_explicit_adoption_and_re_review():
    text = REFERENCE.read_text(encoding="utf-8")
    assert "候选稿须用户明确采用并重新审查后才能制作" in text


def test_v4_contract_uses_world_and_stages_not_stage_local_scenes():
    text = REFERENCE.read_text(encoding="utf-8")
    assert "全片唯一 renderer" in text
    assert "阶段代表推理进展，不是换场" in text


def test_repository_example_set_is_fixed_and_limited_to_three():
    text = REFERENCE.read_text(encoding="utf-8")
    assert "最多 3 个" in text
    assert "不新增、删除或替换目录" in text
