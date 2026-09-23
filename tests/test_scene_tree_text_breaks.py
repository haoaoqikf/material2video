"""场景树文本换行契约：分镜里的换行符必须是硬换行。

视觉规范要求「用分镜里的换行符手动断行，不要让浏览器自动折行决定
重点词的位置」。文本原语曾把 ``\\n`` 折叠成空格，折行位置交给浏览器，
出现「吗」「分」这类单字孤行。这里钉住样式层的行为：文本原语必须以
``white-space: pre-line`` 渲染，且该规则属于文本原语而不是别的原语。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "web" / "src" / "styles" / "scene-tree.css"


def _strip_comments(css: str) -> str:
    """去掉 /* */ 注释：注释文本不能参与选择器或规则体的判定。"""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _text_primitive_rules(css: str) -> list[str]:
    """抽出所有属于文本原语（`.a2v-primitive-text`）的规则块。"""
    blocks: list[str] = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", _strip_comments(css)):
        selectors, body = match.group(1), match.group(2)
        selectors = " ".join(selectors.split())
        if any(part.strip() == ".a2v-primitive-text" for part in selectors.split(",")):
            blocks.append(body)
    return blocks


def test_text_primitive_renders_hard_line_breaks():
    rules = _text_primitive_rules(CSS.read_text(encoding="utf-8"))
    assert rules, "scene-tree.css 必须有针对 .a2v-primitive-text 的规则"
    joined = "\n".join(rules)
    assert "white-space: pre-line" in joined, (
        "文本原语必须声明 white-space: pre-line，让分镜换行符成为硬换行"
    )


def test_line_break_rule_is_not_broadcast_to_other_primitives():
    """换行行为只属于文本原语：布局与图形原语不得整体继承 pre-line。"""
    css = _strip_comments(CSS.read_text(encoding="utf-8"))
    for selector in (".a2v-primitive", ".a2v-primitive-stack", ".a2v-primitive-surface"):
        blocks = [
            body
            for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
            if selector in [part.strip() for part in selectors.split(",")]
        ]
        joined = "\n".join(blocks)
        assert "pre-line" not in joined, f"{selector} 不应声明 pre-line"


def test_chart_labels_stay_readable():
    """柱状图类别标签必须取标签档字号，且柱状图容器留出标签带。"""
    css = _strip_comments(CSS.read_text(encoding="utf-8"))
    bar_span = next(
        body
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
        if ".a2v-primitive-bar span" in [part.strip() for part in selectors.split(",")]
    )
    assert "--a2v-size-label" in bar_span, "柱状图标签应取标签档字号（--a2v-size-label）"
    assert "top: calc(100% + 8px)" in bar_span, "类别标签应排在柱体外，避免压在强调色上降低对比度"
    assert "--a2v-text-1" in bar_span, "类别标签应使用可读性正文墨色"


def test_schematic_labels_use_accessible_accent_ink():
    """浅色主题强调蓝只有 4.55:1；示意标记须切换到正文对比度墨色。"""
    css = _strip_comments(CSS.read_text(encoding="utf-8"))
    schematic = next(
        body
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
        if ".a2v-schematic" in [part.strip() for part in selectors.split(",")]
    )
    assert "--a2v-accent-ink" in schematic
    bar_chart = next(
        body
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
        if ".a2v-chart-bar" in [part.strip() for part in selectors.split(",")]
    )
    assert "padding-bottom" in bar_chart, "柱状图需要底部标签带，标签不得与后续内容重叠"


def test_chart_wrapper_does_not_double_the_label_band():
    """原语包装盒（.a2v-primitive.a2v-primitive-chart）必须随内容撑开。

    入场揭示动效给包装盒加 clip-path: inset(0)（终态）：内层图表一旦溢出
    包装盒，溢出内容就被裁掉——角标曾因此整块消失。包装盒不得自带高度，
    标签带只由内层（.a2v-chart-bar）声明。
    """
    css = _strip_comments(CSS.read_text(encoding="utf-8"))
    outer = next(
        body
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
        if ".a2v-primitive.a2v-primitive-chart"
        in [part.strip() for part in selectors.split(",")]
    )
    assert "height: auto" in outer, "包装盒必须随内容撑开，防止内层溢出被揭示裁剪"
    assert "padding-bottom" not in outer, "标签带只由内层 .a2v-chart-bar 声明"
