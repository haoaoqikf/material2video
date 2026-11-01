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
