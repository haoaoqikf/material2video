"""视觉原语注册表的 Python 生成镜像；请运行 sync_catalog.py 更新。"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Primitive:
    type: str
    category: str
    children: tuple[int, int]
    props: frozenset[str]
    motions: frozenset[str]
    summary: str

# >>> generated:registry >>>
PRIMITIVE_CATALOG: dict[str, Primitive] = {
    'chart': Primitive(
        type='chart',
        category='content',
        children=(0, 0),
        props=frozenset(['contentRef', 'chart', 'schematic', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='显示柱状、折线或饼图',
    ),
    'column': Primitive(
        type='column',
        category='layout',
        children=(1, 8),
        props=frozenset(['align', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='纵向排列内容',
    ),
    'connector': Primitive(
        type='connector',
        category='graphic',
        children=(0, 0),
        props=frozenset(['direction', 'state']),
        motions=frozenset(['reveal', 'fade', 'draw']),
        summary='按确定方向绘制连接箭头，表达相邻内容之间的推进关系',
    ),
    'grid': Primitive(
        type='grid',
        category='layout',
        children=(1, 6),
        props=frozenset(['columns', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='二列或三列网格',
    ),
    'group': Primitive(
        type='group',
        category='graphic',
        children=(1, 12),
        props=frozenset(['direction', 'gap', 'align']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='为一组节点提供语义分组',
    ),
    'icon': Primitive(
        type='icon',
        category='content',
        children=(0, 0),
        props=frozenset(['icon', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='显示内置符号',
    ),
    'image': Primitive(
        type='image',
        category='content',
        children=(0, 0),
        props=frozenset(['sourceRef', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='显示本地受控图片',
    ),
    'number': Primitive(
        type='number',
        category='content',
        children=(0, 0),
        props=frozenset(['contentRef', 'role', 'schematic', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise', 'count']),
        summary='显示或递增数值',
    ),
    'overlay': Primitive(
        type='overlay',
        category='layout',
        children=(1, 6),
        props=frozenset(['align']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='在同一区域叠加图层',
    ),
    'radial': Primitive(
        type='radial',
        category='layout',
        children=(2, 6),
        props=frozenset([]),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='围绕中心按确定性圆周布局排布子节点',
    ),
    'row': Primitive(
        type='row',
        category='layout',
        children=(1, 6),
        props=frozenset(['align', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='横向排列内容',
    ),
    'shape': Primitive(
        type='shape',
        category='graphic',
        children=(0, 0),
        props=frozenset(['shape', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise', 'draw']),
        summary='显示受控基础形状',
    ),
    'split': Primitive(
        type='split',
        category='layout',
        children=(2, 2),
        props=frozenset(['ratio', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='按受控比例分成两栏',
    ),
    'stack': Primitive(
        type='stack',
        category='layout',
        children=(1, 12),
        props=frozenset(['align', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='叠放内容并按统一对齐排列',
    ),
    'surface': Primitive(
        type='surface',
        category='graphic',
        children=(1, 8),
        props=frozenset(['state', 'gap', 'align']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='承载内容的卡片或面板',
    ),
    'text': Primitive(
        type='text',
        category='content',
        children=(0, 0),
        props=frozenset(['contentRef', 'role', 'align', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        summary='显示分镜文本内容',
    ),
}
# <<< generated:registry <<<

def primitive(node_type: str) -> Primitive | None:
    return PRIMITIVE_CATALOG.get(node_type)

def known_types() -> list[str]:
    return sorted(PRIMITIVE_CATALOG)
