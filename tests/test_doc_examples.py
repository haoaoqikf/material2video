"""文档里的正反例必须与校验器结论一致。

`references/article-to-storyboard.md` 同时给出「文字卡片冒充图形论证」的反例与
「图形承担论证」的正例。本用例直接抽取文档中的 JSON 代码块重新校验，
避免契约演进后文档示例悄悄失真。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from a2v import storyboard as sb

REFERENCE = (
    Path(__file__).resolve().parents[1]
    / ".agents"
    / "skills"
    / "article2video"
    / "references"
    / "article-to-storyboard.md"
)

GRAPHIC_MODES = {"metaphor", "process", "comparison", "cycle", "chart", "image"}


def _section_json(heading: str) -> dict:
    """取出 `### <heading>` 小节里的第一个 json 代码块。"""
    text = REFERENCE.read_text(encoding="utf-8")
    section = re.search(
        rf"^###\s*{heading}[^\n]*\n(.*?)(?=^###\s|\Z)", text, re.MULTILINE | re.DOTALL
    )
    assert section, f"文档缺少小节：{heading}"
    block = re.search(r"```json\s*\n(.*?)```", section.group(1), re.DOTALL)
    assert block, f"{heading} 小节缺少 json 代码块"
    return json.loads(block.group(1))


def _messages(report) -> str:
    return "\n".join(f"{issue.path}: {issue.message}" for issue in report.issues)


def test_negative_example_is_rejected_by_strict_validation():
    report = sb.validate(_section_json("反例"), strict=True)
    assert not report.ok
    messages = _messages(report)
    # 三幕都声明了图形模式，结构上却只有文字与图标
    assert "声明为 comparison" in messages
    assert "声明为 process" in messages
    assert "声明为 chart" in messages
    assert "scenes[0].visualIntent.mode" in messages
    assert "scenes[1].visualIntent.mode" in messages
    assert "scenes[2].visualIntent.mode" in messages
    # 全片预算同时被触发：三幕全是文字幕
    assert "文字幕 3/3 幕，超过允许上限 1" in messages
    assert "相邻两幕均为文字幕" in messages
    # 模式覆盖按声明计数，反例声明了 3 种图形模式；它由逐幕结构反证拦下，
    # 而不是靠覆盖门槛——否则「全部声明、全部没有证据」会绕开覆盖检查。
    assert "非文字视觉模式只有" not in messages


def test_negative_example_stays_compatible_without_strict():
    """预算与结构反证只在严格校验生效，普通校验保持可预览可渲染。"""
    report = sb.validate(_section_json("反例"))
    assert report.ok
    assert report.errors == []


def test_positive_example_passes_strict_validation():
    report = sb.validate(_section_json("正例"), strict=True)
    assert report.ok, _messages(report)


def test_examples_describe_the_same_scenes():
    negative = _section_json("反例")
    positive = _section_json("正例")
    assert [scene["id"] for scene in negative["scenes"]] == [
        scene["id"] for scene in positive["scenes"]
    ]
    # 反例逐幕声明图形模式，正例改用能拿出结构证据的模式
    assert {scene["visualIntent"]["mode"] for scene in negative["scenes"]} <= GRAPHIC_MODES
    assert positive["scenes"][0]["visualIntent"]["mode"] == "typography"


def test_positive_example_declares_evidence_modes():
    positive = _section_json("正例")
    modes = [scene["visualIntent"]["mode"] for scene in positive["scenes"]]
    assert modes == ["typography", "process", "chart"]
    assert set(modes) & GRAPHIC_MODES == {"process", "chart"}
