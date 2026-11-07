"""项目级运动 skill 的结构性契约。"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".agents" / "skills"


@pytest.mark.parametrize("name, commit, license_file, license_marker", [
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
