"""仓库只分发固定的三个示例，且每份分镜都必须通过严格校验。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from m2v.types.general import explainer

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


def test_every_shipped_example_declares_v7() -> None:
    legacy = {path.parent.name for path in STORYBOARDS if _declared_version(path) != 7}
    assert not legacy, f"示例未声明 v7：{sorted(legacy)}"


@pytest.mark.parametrize("path", STORYBOARDS, ids=lambda item: item.parent.name)
def test_shipped_example_matches_the_v7_contract(path: Path) -> None:
    explainer.validate(json.loads(path.read_text(encoding="utf-8")), path.parent)


@pytest.mark.parametrize("path", STORYBOARDS, ids=lambda item: item.parent.name)
def test_example_media_is_content_addressed_and_recorded(path: Path) -> None:
    """示例引用的媒体必须已导入并留证，不能靠未入库的散文件凑数。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    referenced = [scene["content"]["src"] for scene in data["scenes"]
                  if scene["template"] in {"image", "video"}]
    if not referenced:
        return
    record = json.loads((path.parent / "assets/media-sources.json").read_text(encoding="utf-8"))
    recorded = {entry["path"]: entry for entry in record["assets"]}
    assert set(referenced) <= set(recorded), f"示例媒体缺少导入记录：{sorted(set(referenced) - set(recorded))}"
    for relative in referenced:
        file = path.parent / relative
        assert file.is_file()
        assert file.name.startswith(recorded[relative]["sha256"])
        assert recorded[relative]["kind"] == ("video" if file.suffix == ".mp4" else "image")
