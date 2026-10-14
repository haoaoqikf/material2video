"""文章手册描述当前 v5 模板、真实时长和输入审查。"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/".agents/skills/material2video/references"


def test_workflow_and_compatibility_documented():
    text=(ROOT/"article-to-storyboard.md").read_text(encoding="utf-8")
    assert "输入审查 → 提炼核心观点" in text
    assert "候选稿须用户明确采用并重新审查后才能制作" in text
    assert "实际时长" in text and "60 秒" in text
    assert "最多 3 个" in text and "不新增、删除或替换目录" in text
    schema=(ROOT/"storyboard-schema.md").read_text(encoding="utf-8")
    assert "v1～v4 必须重新编排" in schema
    assert all(kind in schema for kind in ['point','compare','steps','cause','image'])
