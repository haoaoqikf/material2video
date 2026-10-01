"""仓库内的示例是交付标杆：必须通过严格校验，不能带着警告出厂。

严格模式把警告也算作失败（`main_validate` 里 `args.strict and report.warnings`），
因此布局多样性、文字幕预算这类提醒同样要求清零。标杆示例如果只在非严格模式下
「通过」，交给使用者的就是一份自己都没过交付门禁的分镜。

入口只接受 v4：已经改编为单场景动态叙事的示例必须通过严格校验；还没有改编的
旧幕级示例必须被明确拒绝，而不是继续按旧契约通过——「仍然能过」才是这里最危险的
状态。改编进度由 `LEGACY_EXAMPLES` 显式记录，只允许缩小，改编完成后再要求它为空。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from a2v import cli

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
STORYBOARDS = sorted(EXAMPLES.glob("*/storyboard.json"))

#: 尚未改编为 v4 的示例（任务 6.5–6.9）。改编一个就删一个，不允许新增。
LEGACY_EXAMPLES: set[str] = {
    "declarative-number",
    "keynote-baseline",
    "milestone-climb",
    "narration-beats",
    "why-effort-fails",
}


def _declared_version(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8")).get("version")


def test_examples_are_discovered() -> None:
    assert len(STORYBOARDS) >= 5, "示例目录结构变了，这条守卫会静默失效"


def test_only_recorded_examples_are_still_legacy() -> None:
    legacy = {path.parent.name for path in STORYBOARDS if _declared_version(path) != 4}
    assert legacy == LEGACY_EXAMPLES, (
        "旧契约示例集合与登记的待改编清单不一致：新增旧示例必须重新编排，"
        "已改编的示例请从 LEGACY_EXAMPLES 中移除"
    )


@pytest.mark.parametrize("path", STORYBOARDS, ids=lambda item: item.parent.name)
def test_shipped_example_matches_the_v4_contract(path: Path) -> None:
    if path.parent.name in LEGACY_EXAMPLES:
        assert cli.main_validate([str(path), "--strict"]) == 2, (
            f"{path.parent.name} 仍是旧契约示例，入口必须明确拒绝而不是继续放行"
        )
        return
    assert cli.main_validate([str(path), "--strict"]) == 0, f"{path.parent.name} 未通过严格校验"
