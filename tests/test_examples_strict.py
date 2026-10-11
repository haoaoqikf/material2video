"""仓库只分发固定的三个示例，且每份分镜都必须通过严格校验。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import a2v.types.article.cli as cli

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
STORYBOARDS = sorted(EXAMPLES.glob("*/storyboard.json"))
EXPECTED_EXAMPLES = {"buffer-smoothing", "darts-trial-and-error", "keynote-baseline"}


def _declared_version(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8")).get("version")


def test_examples_are_fixed_and_capped() -> None:
    discovered = {path.name for path in EXAMPLES.iterdir() if path.is_dir()}
    assert len(discovered) <= 3, f"示例目录超过上限：{sorted(discovered)}"
    assert discovered == EXPECTED_EXAMPLES, (
        f"示例目录必须固定为 {sorted(EXPECTED_EXAMPLES)}，实际为 {sorted(discovered)}"
    )
    assert {path.parent.name for path in STORYBOARDS} == EXPECTED_EXAMPLES


def test_every_shipped_example_declares_v4() -> None:
    legacy = {path.parent.name for path in STORYBOARDS if _declared_version(path) != 4}
    assert not legacy, f"示例未声明 v4：{sorted(legacy)}"


@pytest.mark.parametrize("path", STORYBOARDS, ids=lambda item: item.parent.name)
def test_shipped_example_matches_the_v4_contract(path: Path) -> None:
    assert cli.main_validate([str(path), "--strict"]) == 0, f"{path.parent.name} 未通过严格校验"
