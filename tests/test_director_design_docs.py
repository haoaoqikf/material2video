"""general 导演设计必须贯穿 DESIGN、storyboard 映射与粗片验收。"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / ".agents/skills/material2video/references"


def test_director_design_is_a_four_layer_design_record_in_phase_one():
    workflow = (REF / "production-workflow.md").read_text(encoding="utf-8")
    section = workflow.split("## 四阶段主线", 1)[1].split("## 三类记录", 1)[0]
    assert "| 方案确定 |" in section
    assert "关键镜头导演卡" in section
    assert "| 粗片验证 |" in section
    assert "| 精制修订 |" in section
    assert "| 最终验收 |" in section
    assert "第五阶段" not in section

    creative = (REF / "visual-creative-direction.md").read_text(encoding="utf-8")
    for layer in ("视觉隐喻回答", "视觉事件回答", "导演设计回答", "视觉力量回答"):
        assert layer in creative
    assert "不新增 `DIRECTION.md`" in creative


def test_director_card_is_tiered_and_distinguishes_camera_motion_from_intent():
    creative = (REF / "visual-creative-direction.md").read_text(encoding="utf-8")
    for field in (
        "Scene Goal", "Visual Metaphor", "Initial State", "Visual Event",
        "Audience Expectation", "Hidden Information", "Reveal",
        "Camera / Attention", "Final Recognition", "完整时间窗口",
    ):
        assert field in creative
    assert "普通镜头" in creative and "核心高潮镜头" in creative
    assert "相机动作必须写出目的和认知作用" in creative
    assert "镜头可以不动" in creative
    assert "不是每幕固定公式" in creative


def test_design_maps_director_intent_to_existing_storyboard_fields_only():
    creative = (REF / "visual-creative-direction.md").read_text(encoding="utf-8")
    schema = (REF / "storyboard-schema.md").read_text(encoding="utf-8")
    scene = (REF / "scene-design-and-acceptance.md").read_text(encoding="utf-8")
    for token in ("scene.id", "shots[].id", "shots[].target", "startFrame", "endFrame"):
        assert token in creative
        assert token in schema
        assert token in scene
    assert "不属于 v8 storyboard JSON" in schema
    assert "不得为了表达导演意图增加 v8 JSON 字段" in (REF / "production-workflow.md").read_text(encoding="utf-8")
    assert "不得由实现阶段自行补造核心表达或揭示机制" in schema

    skill = (ROOT / ".agents/skills/material2video/SKILL.md").read_text(encoding="utf-8")
    prompt = (REF / "article-to-storyboard.md").read_text(encoding="utf-8")
    assert "在 `DESIGN.md` 写导演卡" in skill
    assert "导演卡（写入 DESIGN.md）" in prompt
    assert "不重新发明核心揭示顺序" in prompt


def test_rough_review_requires_the_full_director_window_and_recognition_check():
    scene = (REF / "scene-design-and-acceptance.md").read_text(encoding="utf-8")
    creative = (REF / "visual-creative-direction.md").read_text(encoding="utf-8")
    for token in ("完整时间窗口", "预期是否建立", "信息何时公开", "注意力是否被竞争", "认识是否改变"):
        assert token in scene
    assert "静帧只能支持构图，不能证明隐藏和揭示过程" in scene
    assert "回到导演卡修订" in creative
    assert "不能用增亮、换色、Bloom 或轻微调速关闭导演问题" in creative


def test_static_direct_examples_keep_existing_storyboard_contract():
    # Director intent remains in DESIGN.md; shipped JSON examples remain valid v8
    # materials and are not expanded with new metadata fields.
    for slug in ("american-science-milestones", "five-life-choices", "solar-system-journey"):
        data = json.loads((ROOT / "examples" / slug / "storyboard.json").read_text(encoding="utf-8"))
        assert data["version"] == 8
        assert data["schemaVersion"] == 8
        assert "director" not in data
        for scene in data["scenes"]:
            assert "director" not in scene
            assert "direction" not in scene

