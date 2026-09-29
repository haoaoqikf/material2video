"""仓库内的示例是交付标杆：必须通过严格校验，不能带着警告出厂。

严格模式把警告也算作失败（`main_validate` 里 `args.strict and report.warnings`），
因此布局多样性、文字幕预算这类提醒同样要求清零。标杆示例如果只在非严格模式下
「通过」，交给使用者的就是一份自己都没过交付门禁的分镜。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from a2v import cli

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
STORYBOARDS = sorted(EXAMPLES.glob("*/storyboard.json"))


def test_examples_are_discovered() -> None:
    assert len(STORYBOARDS) >= 5, "示例目录结构变了，这条守卫会静默失效"


@pytest.mark.parametrize("path", STORYBOARDS, ids=lambda item: item.parent.name)
def test_shipped_example_passes_strict_validation(path: Path) -> None:
    assert cli.main_validate([str(path), "--strict"]) == 0, f"{path.parent.name} 未通过严格校验"
