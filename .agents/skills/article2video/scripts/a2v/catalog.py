"""视觉组件目录：校验器读的镜像（由注册表生成）。

组件的实现在 React 工程（`web/src/components/`）；这里保存的是**校验需要的那部分**：
每个组件认识哪些标注键、能吃下多少条目、默认给哪种场景类型，以及
canvas 类组件与「示意」标组件两份清单。

**这份镜像不是手抄的**：生成区由 `scripts/sync_catalog.py` 从
`web/src/registry/registry.json`（唯一真源）生成，手工改动会在
`tests/test_web_registry.py` 的「重新生成无差异」断言上失败并指名本文件。
生成机制建立之前，这里与浏览器端注册表各抄一份、漂移过一次
（图节点只允许 `{id}`），症状是整份分镜在一条路径上画不出来、另一条说它合法。

新增组件时改两处：`web/src/registry/registry.json` 登记元数据、
`web/src/registry/index.ts` 接上组件本体，然后运行生成命令。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Component:
    """一个视觉组件的目录条目。"""

    kind: str
    #: 该组件认识的标注键。分镜写了别的键只会让标签空着，因此校验器会提醒。
    labels: frozenset[str]
    #: 组件能舒适容纳的条目数区间（items / nodes / values）。None 表示不限制。
    items: tuple[int, int] | None = None
    #: 这个组件适合表达什么，用于错误信息与文档。
    summary: str = ""


# >>> generated:registry >>>
FIGURE_CATALOG: dict[str, Component] = {
    'balance': Component(
        kind='balance',
        labels=frozenset({'leftPan', 'rightPan'}),
        items=(2, 2),
        summary='一边重一边轻，随后证明重的那个是空壳',
    ),
    'chart': Component(
        kind='chart',
        labels=frozenset({'note', 'unit'}),
        items=(2, 6),
        summary='柱状/折线/饼图：数据序列随帧显影，关键数值同步输出为 DOM 文本',
    ),
    'exchange': Component(
        kind='exchange',
        labels=frozenset({'leftNode', 'rightNode'}),
        items=(2, 2),
        summary='双向关系，两个端点互相选择',
    ),
    'flow': Component(
        kind='flow',
        labels=frozenset(),
        items=(2, 6),
        summary='因果链/流程步骤：dagre 分层布局，自上而下逐步连线，节点文字按实测宽度定形',
    ),
    'gap': Component(
        kind='gap',
        labels=frozenset({'assumption', 'dropLabel', 'fact', 'noDropLabel'}),
        items=(2, 2),
        summary='量出真正失去了多少：一侧从满到空，另一侧从头就没有',
    ),
    'iceberg': Component(
        kind='iceberg',
        labels=frozenset({'surface'}),
        items=(1, 3),
        summary='看得见的一角与看不见的主体不是一回事',
    ),
    'loop': Component(
        kind='loop',
        labels=frozenset({'gauge'}),
        items=(3, 6),
        summary='循环往复，每转一圈积累一点',
    ),
    'number': Component(
        kind='number',
        labels=frozenset(),
        items=(1, 1),
        summary='按帧递增显示数值，并展示标签与说明',
    ),
    'stairs': Component(
        kind='stairs',
        labels=frozenset({'after', 'axis', 'before'}),
        items=(2, 5),
        summary='次数累积带来的位置变化，并在末段翻转视角',
    ),
    'versus': Component(
        kind='versus',
        labels=frozenset({'left', 'note', 'right'}),
        items=(2, 2),
        summary='两种反应并排，箭头指出该从哪边转向哪边',
    ),
}

# 分镜没有声明 figure.kind 时，按场景类型取用的默认组件。
DEFAULT_KINDS: dict[str, str] = {
    'chart': 'chart',
    'comparison': 'versus',
    'conclusion': 'exchange',
    'diagram': 'loop',
    'list': 'iceberg',
    'number': 'number',
    'quote': 'gap',
    'timeline': 'stairs',
    'title': 'balance',
}

# 画面主体由 canvas 绘制的组件：它们内部的文字量不到，
# 观感闸门（K7 文字溢出 / K8 容器内溢出）对图形内部**不适用**，
# 体检报告必须写明这一判定范围并说明原因（见 inspect.py / keynote.py）。
CANVAS_KINDS: frozenset[str] = frozenset({'chart'})

# 会把 figure.schematic 自动画成「示意」标的组件。
# 其它组件声明了该标记时，校验器要求文案里自己出现「示意」二字，
# 否则「标记为示意」只存在于数据里，观众看不到。
SCHEMATIC_KINDS: frozenset[str] = frozenset({'chart'})
# <<< generated:registry <<<


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
