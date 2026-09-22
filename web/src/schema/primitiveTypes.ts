/* eslint-disable */
/** 由 sync_catalog.py 从视觉原语注册表生成。 */
/** 受控语义动作全集：beat.action 只能取这些值。 */
export const SEMANTIC_ACTIONS = ['establish', 'connect', 'transfer', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'loop', 'break', 'restore'] as const;
export type SemanticAction = (typeof SEMANTIC_ACTIONS)[number];
/** 中性动作：只让对象出现或更醒目，不改变状态与关系。 */
export const NEUTRAL_ACTIONS: readonly string[] = ['establish', 'highlight'];
/** 改变对象状态或关系的动作，与 NEUTRAL_ACTIONS 互补。 */
export const CHANGE_ACTIONS: readonly string[] = ['connect', 'transfer', 'accumulate', 'deplete', 'transform', 'compare', 'loop', 'break', 'restore'];
/** 动作的中文人读说明：报告与文档共用同一份措辞。 */
export const ACTION_LABELS: Readonly<Record<string, string>> = {
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
    'restore': '回到先前状态',
};
/** 受控图标名白名单：icon/pictogram 只能引用这些名字。 */
export const ICON_NAMES = ['arrow', 'check', 'cross', 'spark', 'up', 'down', 'users', 'clock', 'target', 'alert', 'lock', 'link', 'database', 'coin'] as const;
export type IconName = (typeof ICON_NAMES)[number];
export const PRIMITIVE_TYPES = ['chart', 'column', 'connector', 'cycle', 'flow', 'gauge', 'grid', 'group', 'icon', 'image', 'number', 'overlay', 'pictogram', 'radial', 'row', 'shape', 'split', 'stack', 'surface', 'text', 'timeline'] as const;
export type PrimitiveType = (typeof PRIMITIVE_TYPES)[number];
/** 每个原语允许声明的属性（结构性字段 id/type/children 不在此列）。 */
export const PRIMITIVE_PROPS: Readonly<Record<string, readonly string[]>> = {
    'chart': ['contentRef', 'chart', 'schematic', 'state'],
    'column': ['align', 'gap'],
    'connector': ['direction', 'state'],
    'cycle': ['direction', 'state', 'gap'],
    'flow': ['direction', 'state', 'gap'],
    'gauge': ['contentRef', 'schematic', 'state'],
    'grid': ['columns', 'gap'],
    'group': ['direction', 'gap', 'align'],
    'icon': ['icon', 'state'],
    'image': ['sourceRef', 'state'],
    'number': ['contentRef', 'role', 'schematic', 'state'],
    'overlay': ['align'],
    'pictogram': ['contentRef', 'icon', 'schematic', 'state'],
    'radial': [],
    'row': ['align', 'gap'],
    'shape': ['shape', 'state'],
    'split': ['ratio', 'gap'],
    'stack': ['align', 'gap'],
    'surface': ['state', 'gap', 'align'],
    'text': ['contentRef', 'role', 'align', 'state'],
    'timeline': ['direction', 'state', 'gap'],
};
/** 每个原语允许绑定的动效配方。 */
export const PRIMITIVE_MOTIONS: Readonly<Record<string, readonly string[]>> = {
    'chart': ['reveal', 'fade', 'rise'],
    'column': ['reveal', 'fade', 'rise'],
    'connector': ['reveal', 'fade', 'draw'],
    'cycle': ['reveal', 'fade', 'rise', 'draw'],
    'flow': ['reveal', 'fade', 'rise', 'draw'],
    'gauge': ['reveal', 'fade', 'rise', 'count', 'draw'],
    'grid': ['reveal', 'fade', 'rise'],
    'group': ['reveal', 'fade', 'rise'],
    'icon': ['reveal', 'fade', 'rise'],
    'image': ['reveal', 'fade', 'rise'],
    'number': ['reveal', 'fade', 'rise', 'count'],
    'overlay': ['reveal', 'fade', 'rise'],
    'pictogram': ['reveal', 'fade', 'rise', 'count'],
    'radial': ['reveal', 'fade', 'rise'],
    'row': ['reveal', 'fade', 'rise'],
    'shape': ['reveal', 'fade', 'rise', 'draw'],
    'split': ['reveal', 'fade', 'rise'],
    'stack': ['reveal', 'fade', 'rise'],
    'surface': ['reveal', 'fade', 'rise'],
    'text': ['reveal', 'fade', 'rise'],
    'timeline': ['reveal', 'fade', 'rise', 'draw'],
};
/** 每个原语支持的受控语义动作（beat 的 action 必须落在目标原语的清单里）。 */
export const PRIMITIVE_ACTIONS: Readonly<Record<string, readonly string[]>> = {
    'chart': ['establish', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'restore'],
    'column': ['establish', 'highlight', 'transform'],
    'connector': ['establish', 'connect', 'break', 'highlight', 'transform', 'restore'],
    'cycle': ['establish', 'connect', 'transfer', 'accumulate', 'deplete', 'transform', 'highlight', 'loop', 'break', 'restore'],
    'flow': ['establish', 'connect', 'transfer', 'accumulate', 'deplete', 'transform', 'highlight', 'loop', 'break', 'restore'],
    'gauge': ['establish', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'restore'],
    'grid': ['establish', 'highlight', 'transform', 'compare'],
    'group': ['establish', 'connect', 'highlight', 'transform', 'compare'],
    'icon': ['establish', 'highlight', 'transform'],
    'image': ['establish', 'highlight', 'transform', 'compare'],
    'number': ['establish', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'restore'],
    'overlay': ['establish', 'highlight', 'transform'],
    'pictogram': ['establish', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'restore'],
    'radial': ['establish', 'connect', 'compare', 'highlight', 'transform'],
    'row': ['establish', 'highlight', 'transform'],
    'shape': ['establish', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'restore'],
    'split': ['establish', 'highlight', 'transform', 'compare'],
    'stack': ['establish', 'highlight', 'transform'],
    'surface': ['establish', 'highlight', 'transform', 'compare'],
    'text': ['establish', 'highlight', 'transform', 'compare'],
    'timeline': ['establish', 'connect', 'transfer', 'accumulate', 'deplete', 'transform', 'compare', 'highlight', 'loop', 'break', 'restore'],
};
