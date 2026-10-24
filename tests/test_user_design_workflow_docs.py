"""用户已给出可执行方案时的 general 流程文档契约。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / ".agents/skills/material2video/references"


def test_detailed_user_general_design_is_adopted_without_reopening_selection():
    workflow = (REFERENCES / "production-workflow.md").read_text(encoding="utf-8")
    adoption = workflow.split("## 用户详细方案直接采用\n", 1)[1].split("## 立意六项", 1)[0]
    for token in ("核心表达", "关键事件", "画面顺序", "主要约束", "足以开始设计或试制",
                  "不强制补齐三个叙事候选或两个美术方向", "不重复论证", "最小且不冲突原则",
                  "独立评审", "视觉事件与视觉力量", "最终候选", "事实", "技术可行性",
                  "最小必要调整", "个人审美偏好不构成硬冲突", "沿用原有候选流程"):
        assert token in adoption

    skill = (ROOT / ".agents/skills/material2video/SKILL.md").read_text(encoding="utf-8")
    assert "用户详细方案直接采用" in skill
    assert "不强制补齐叙事候选或两个美术方向" in skill
    assert "用户给出的 general 方案足以执行时直接采用" in (ROOT / "README.md").read_text(encoding="utf-8")

    creative = (REFERENCES / "creative-production.md").read_text(encoding="utf-8")
    assert "用户方案足以执行时直接采用" in creative
    assert "用户已明确足以执行的美术方向时不强制另做方向选案" in creative
    reviewers = (REFERENCES / "subagent-review.md").read_text(encoding="utf-8")
    assert "用户未给定方向时" in reviewers
    assert "叙事候选比较 | 方案确定（触发常规候选路径时）" in reviewers

    # 力量机制仍用于测试呈现，不能借此重新选定用户的核心创意。
    impact = (REFERENCES / "visual-impact-design.md").read_text(encoding="utf-8")
    assert "至少三个视觉机制不同的候选" in impact
    delta = ROOT / "openspec/changes/adopt-user-detailed-general-design/specs/video-production-workflow/spec.md"
    spec = delta.read_text(encoding="utf-8")
    for scenario in ("用户方案足以开始试制", "方案遗漏次要实现细节", "独立评审检查方案执行",
                     "存在可验证的硬冲突", "用户只给出宽泛主题"):
        assert f"#### Scenario: {scenario}" in spec
    assert "范围例外" in spec
