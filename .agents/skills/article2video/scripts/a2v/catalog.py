"""视觉组件目录的服务端镜像。

组件真正的实现是浏览器端的 `assets/figures.js`；这里保存的是**校验需要的那部分**：
每个组件认识哪些标注键、能吃下多少条目、默认给哪种场景类型。

为什么要镜像而不是让校验器去解析 JS：校验器要在开渲前给出可定位的错误，
而 JS 里的注册逻辑不是稳定的文本格式。代价是两处可能漂移，因此
`tests/test_figures_assets.py` 会把这份镜像与 `figures.js` 逐项对照，
不一致就失败——目录只有一个真源，其余都是它的投影。

新增组件时改三处：`assets/figures.js` 注册、这里登记、`references/figure-catalog.md` 记一行。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Component:
    """一个视觉组件的目录条目。"""

    kind: str
    #: 该组件认识的标注键。分镜写了别的键只会让标签空着，因此校验器会提醒。
    labels: frozenset[str]
    #: 组件能舒适容纳的条目数区间（items / nodes）。None 表示不限制。
    items: tuple[int, int] | None = None
    #: 这个组件适合表达什么，用于错误信息与文档。
    summary: str = ""


FIGURE_CATALOG: dict[str, Component] = {
    "balance": Component(
        kind="balance",
        labels=frozenset({"leftPan", "rightPan"}),
        summary="一边重一边轻，随后证明重的那个是空壳",
    ),
    "gap": Component(
        kind="gap",
        labels=frozenset({"assumption", "fact", "dropLabel", "noDropLabel"}),
        summary="量出真正失去了多少：一侧从满到空，另一侧从头就没有",
    ),
    "iceberg": Component(
        kind="iceberg",
        labels=frozenset({"surface"}),
        items=(1, 3),
        summary="看得见的一角与看不见的主体不是一回事",
    ),
    "loop": Component(
        kind="loop",
        labels=frozenset({"gauge"}),
        items=(3, 6),
        summary="循环往复，每转一圈积累一点",
    ),
    "stairs": Component(
        kind="stairs",
        labels=frozenset({"axis", "before", "after"}),
        items=(2, 5),
        summary="次数累积带来的位置变化，并在末段翻转视角",
    ),
    "exchange": Component(
        kind="exchange",
        labels=frozenset({"leftNode", "rightNode"}),
        summary="双向关系，两个端点互相选择",
    ),
    "versus": Component(
        kind="versus",
        labels=frozenset({"left", "right", "note"}),
        summary="两种反应并排，箭头指出该从哪边转向哪边",
    ),
    "number": Component(
        kind="number",
        labels=frozenset(),
        summary="按帧递增显示数值，并展示标签与说明",
    ),
}

#: 分镜没有声明 figure.kind 时，按场景类型取用的默认组件。
#: 页面里的 DEFAULT_FIGURES 必须与它一致（有测试对照）。
DEFAULT_KINDS: dict[str, str] = {
    "title": "balance",
    "quote": "gap",
    "comparison": "versus",
    "list": "iceberg",
    "diagram": "loop",
    "timeline": "stairs",
    "conclusion": "exchange",
    "number": "number",
}


def known_kinds() -> list[str]:
    return sorted(FIGURE_CATALOG)


def component(kind: str) -> Component | None:
    return FIGURE_CATALOG.get(kind)


def resolve_kind(scene_type: str, figure: object) -> str | None:
    """算出这一幕实际会用到哪个组件：分镜声明优先，否则用默认映射。"""
    if isinstance(figure, dict):
        declared = figure.get("kind")
        if isinstance(declared, str) and declared.strip():
            return declared.strip()
    return DEFAULT_KINDS.get(scene_type)
