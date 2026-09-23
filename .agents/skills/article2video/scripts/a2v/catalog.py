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
    #: 该原语支持的受控语义动作（beat.action 必须落在目标原语的清单里）。
    actions: frozenset[str]
    summary: str

# >>> generated:registry >>>
#: 受控语义动作全集：beat.action 只能取这些值。
SEMANTIC_ACTIONS: tuple[str, ...] = (
    'establish',
    'connect',
    'transfer',
    'accumulate',
    'deplete',
    'transform',
    'compare',
    'highlight',
    'loop',
    'break',
    'restore',
)
#: 中性动作：只让对象出现或更醒目，不改变状态与关系（A3 闸门据此判定）。
NEUTRAL_ACTIONS: frozenset[str] = frozenset(('establish', 'highlight'))
#: 改变对象状态或关系的动作，与 NEUTRAL_ACTIONS 互补。
CHANGE_ACTIONS: frozenset[str] = frozenset(('connect', 'transfer', 'accumulate', 'deplete', 'transform', 'compare', 'loop', 'break', 'restore'))
#: 动作的中文人读说明：错误信息、报告与文档共用同一份措辞。
ACTION_LABELS: dict[str, str] = {
    'establish': '建立对象或关系',
    'connect': '连接两处内容，表达推进或因果',
    'transfer': '把量或注意力从一个对象转移到另一个',
    'accumulate': '累积增长',
    'deplete': '消耗衰减',
    'transform': '改变形态或类别',
    'compare': '并置比较',
    'highlight': '只强调，不改变状态',
    'loop': '形成闭环回路',
    'break': '打断或断开关系',
    'restore': '回到先前状态'
}
#: 受控图标名白名单：icon/pictogram 只能引用这些名字，未知名字在校验阶段失败。
ICON_NAMES: tuple[str, ...] = (
    'arrow',
    'check',
    'cross',
    'spark',
    'up',
    'down',
    'users',
    'clock',
    'target',
    'alert',
    'lock',
    'link',
    'database',
    'coin',
)
#: 注册表允许的有限跨幕原语变形；同类原语始终允许。
CONTINUITY_TRANSFORMS: frozenset[tuple[str, str]] = frozenset((('flow', 'cycle'), ('cycle', 'timeline'), ('timeline', 'gauge')))

PRIMITIVE_CATALOG: dict[str, Primitive] = {
    'chart': Primitive(
        type='chart',
        category='content',
        children=(0, 0),
        props=frozenset(['contentRef', 'chart', 'schematic', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'restore']),
        summary='显示柱状、折线或饼图',
    ),
    'column': Primitive(
        type='column',
        category='layout',
        children=(1, 8),
        props=frozenset(['align', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'highlight', 'transform']),
        summary='纵向排列内容',
    ),
    'connector': Primitive(
        type='connector',
        category='graphic',
        children=(0, 0),
        props=frozenset(['direction', 'state']),
        motions=frozenset(['reveal', 'fade', 'draw']),
        actions=frozenset(['establish', 'connect', 'break', 'highlight', 'transform', 'restore']),
        summary='按确定方向绘制连接箭头，表达相邻内容之间的推进关系',
    ),
    'cycle': Primitive(
        type='cycle',
        category='layout',
        children=(2, 6),
        props=frozenset(['direction', 'state', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise', 'draw']),
        actions=frozenset(['establish', 'connect', 'transfer', 'accumulate', 'deplete', 'transform', 'highlight', 'loop', 'break', 'restore']),
        summary='把阶段排在闭环轨道上并标出方向与当前阶段',
    ),
    'flow': Primitive(
        type='flow',
        category='layout',
        children=(2, 6),
        props=frozenset(['direction', 'state', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise', 'draw']),
        actions=frozenset(['establish', 'connect', 'transfer', 'accumulate', 'deplete', 'transform', 'highlight', 'loop', 'break', 'restore']),
        summary='按确定方向串起阶段并画箭头，突出当前阶段',
    ),
    'gauge': Primitive(
        type='gauge',
        category='content',
        children=(0, 0),
        props=frozenset(['contentRef', 'schematic', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise', 'count', 'draw']),
        actions=frozenset(['establish', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'restore']),
        summary='用受控指针与刻度显示百分比量级',
    ),
    'grid': Primitive(
        type='grid',
        category='layout',
        children=(1, 6),
        props=frozenset(['columns', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'highlight', 'transform', 'compare']),
        summary='二列或三列网格',
    ),
    'group': Primitive(
        type='group',
        category='graphic',
        children=(1, 12),
        props=frozenset(['direction', 'gap', 'align']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'connect', 'highlight', 'transform', 'compare']),
        summary='为一组节点提供语义分组',
    ),
    'icon': Primitive(
        type='icon',
        category='content',
        children=(0, 0),
        props=frozenset(['icon', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'highlight', 'transform']),
        summary='显示内置符号',
    ),
    'image': Primitive(
        type='image',
        category='content',
        children=(0, 0),
        props=frozenset(['sourceRef', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'highlight', 'transform', 'compare']),
        summary='显示本地受控图片',
    ),
    'number': Primitive(
        type='number',
        category='content',
        children=(0, 0),
        props=frozenset(['contentRef', 'role', 'schematic', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise', 'count']),
        actions=frozenset(['establish', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'restore']),
        summary='显示或递增数值',
    ),
    'overlay': Primitive(
        type='overlay',
        category='layout',
        children=(1, 6),
        props=frozenset(['align']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'highlight', 'transform']),
        summary='在同一区域叠加图层',
    ),
    'pictogram': Primitive(
        type='pictogram',
        category='content',
        children=(0, 0),
        props=frozenset(['contentRef', 'icon', 'schematic', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise', 'count']),
        actions=frozenset(['establish', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'restore']),
        summary='用固定数量的受控图标单位显示占比',
    ),
    'radial': Primitive(
        type='radial',
        category='layout',
        children=(2, 6),
        props=frozenset([]),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'connect', 'compare', 'highlight', 'transform']),
        summary='围绕中心按确定性圆周布局排布子节点',
    ),
    'row': Primitive(
        type='row',
        category='layout',
        children=(1, 6),
        props=frozenset(['align', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'highlight', 'transform']),
        summary='横向排列内容',
    ),
    'shape': Primitive(
        type='shape',
        category='graphic',
        children=(0, 0),
        props=frozenset(['shape', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise', 'draw']),
        actions=frozenset(['establish', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'restore']),
        summary='显示受控基础形状',
    ),
    'split': Primitive(
        type='split',
        category='layout',
        children=(2, 2),
        props=frozenset(['ratio', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'highlight', 'transform', 'compare']),
        summary='按受控比例分成两栏',
    ),
    'stack': Primitive(
        type='stack',
        category='layout',
        children=(1, 12),
        props=frozenset(['align', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'highlight', 'transform']),
        summary='叠放内容并按统一对齐排列',
    ),
    'surface': Primitive(
        type='surface',
        category='graphic',
        children=(1, 8),
        props=frozenset(['state', 'gap', 'align']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'highlight', 'transform', 'compare']),
        summary='承载内容的卡片或面板',
    ),
    'text': Primitive(
        type='text',
        category='content',
        children=(0, 0),
        props=frozenset(['contentRef', 'role', 'align', 'state']),
        motions=frozenset(['reveal', 'fade', 'rise']),
        actions=frozenset(['establish', 'highlight', 'transform', 'compare']),
        summary='显示分镜文本内容',
    ),
    'timeline': Primitive(
        type='timeline',
        category='layout',
        children=(2, 6),
        props=frozenset(['direction', 'state', 'gap']),
        motions=frozenset(['reveal', 'fade', 'rise', 'draw']),
        actions=frozenset(['establish', 'connect', 'transfer', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'loop', 'break', 'restore']),
        summary='按确定方向排列里程碑并画出推进进度',
    ),
}
# <<< generated:registry <<<

def primitive(node_type: str) -> Primitive | None:
    return PRIMITIVE_CATALOG.get(node_type)

def known_types() -> list[str]:
    return sorted(PRIMITIVE_CATALOG)
