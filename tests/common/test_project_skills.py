"""项目级视觉设计与运动 skill 的结构性契约。"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"
MAIN = SKILLS / "material2video" / "SKILL.md"


@pytest.mark.parametrize("name, commit, license_file, license_marker", [
    ("frontend-design", "ca45fc496a3436251f191354091d557da31c15b5", "LICENSE.txt", "Apache License"),
    ("motion-design", "f9a8a041b85185ee4881b3471d3415e939aac772", "LICENSE", "MIT License"),
])
def test_project_skill_is_pinned_and_licensed(
    name: str, commit: str, license_file: str, license_marker: str,
) -> None:
    root = SKILLS / name
    for filename in ("SKILL.md", "ADAPTATION.md", "UPSTREAM.md", license_file):
        assert (root / filename).is_file(), f"{name} 缺少 {filename}"
    upstream = (root / "UPSTREAM.md").read_text(encoding="utf-8")
    assert commit in upstream
    assert license_marker in (root / license_file).read_text(encoding="utf-8")


def test_main_skill_points_to_both_project_skills() -> None:
    text = MAIN.read_text(encoding="utf-8")
    assert "../frontend-design/SKILL.md" in text
    assert "../motion-design/SKILL.md" in text


def test_adaptations_state_the_project_boundaries() -> None:
    visual = (SKILLS / "frontend-design" / "ADAPTATION.md").read_text(encoding="utf-8")
    motion = (SKILLS / "motion-design" / "ADAPTATION.md").read_text(encoding="utf-8")
    assert "观察" in visual and "批评" in visual
    assert "motion-design" in visual
    assert "不新增" in visual or "不改变" in visual
    assert "pure-time" in motion
    assert "sequential" in motion
    assert "linear" in motion
    assert "1/3" in motion


def test_old_aesthetic_skill_is_removed() -> None:
    assert not (SKILLS / "aesthetic-foundations").exists()
    for path in (
        MAIN,
        SKILLS / "material2video" / "references" / "guidance-routes.json",
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / "ARCHITECTURE.md",
    ):
        assert "aesthetic-foundations" not in path.read_text(encoding="utf-8"), path


TYPE_GUIDES = ("building-construction", "driving-route", "financial-timeseries",
               "road-trip", "vehicle-showcase")


@pytest.mark.parametrize("type_id", TYPE_GUIDES)
def test_type_guides_link_both_project_skills(type_id: str) -> None:
    """类型指南必须把通用视觉与运动判断交给 skill，自己只留类型特有契约。"""
    guide = SKILLS / "material2video" / "references" / f"{type_id}-video.md"
    text = guide.read_text(encoding="utf-8")
    for target in ("../frontend-design/SKILL.md", "../frontend-design/ADAPTATION.md",
                   "../motion-design/SKILL.md", "../motion-design/ADAPTATION.md"):
        assert target in text, f"{type_id} 缺少 {target}"


def test_guidance_uses_five_blocks_not_the_retired_seven_part_form() -> None:
    """七段式模板已删除，指导文档不得再要求填写七段或按七段取证。"""
    references = SKILLS / "material2video" / "references"
    retired = ("七段是必答问题", "| 七段 |", "七段是否齐全", "七段式定稿")
    for path in references.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for marker in retired:
            assert marker not in text, f"{path.name} 仍在维护 {marker}"
    direction = (references / "visual-creative-direction.md").read_text(encoding="utf-8")
    assert "### 4. 运动计划" in direction
    for block in ("### 1. 题材", "### 2. 视觉计划", "### 3. 叙事计划", "### 5. 风险与证据"):
        assert block in direction


def test_guidance_does_not_copy_upstream_motion_recipes() -> None:
    """项目文档不得复述 skill 的 UI 版缓动配方与毫秒表，通用方法只留一个权威位置。"""
    references = SKILLS / "material2video" / "references"
    upstream_only = ("cubic-bezier", "ease-out-back", "ease-out-expo", "easeInOutBack")
    for path in references.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for marker in upstream_only:
            assert marker not in text, f"{path.name} 复述了上游缓动配方：{marker}"
