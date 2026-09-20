/* eslint-disable */
/** 由 sync_catalog.py 从视觉原语注册表生成。 */
export const PRIMITIVE_TYPES = ['chart', 'column', 'connector', 'grid', 'group', 'icon', 'image', 'number', 'overlay', 'radial', 'row', 'shape', 'split', 'stack', 'surface', 'text'] as const;
export type PrimitiveType = (typeof PRIMITIVE_TYPES)[number];
/** 每个原语允许声明的属性（结构性字段 id/type/children 不在此列）。 */
export const PRIMITIVE_PROPS: Readonly<Record<string, readonly string[]>> = {
    'chart': ['contentRef', 'chart', 'schematic', 'state'],
    'column': ['align', 'gap'],
    'connector': ['direction', 'state'],
    'grid': ['columns', 'gap'],
    'group': ['direction', 'gap', 'align'],
    'icon': ['icon', 'state'],
    'image': ['sourceRef', 'state'],
    'number': ['contentRef', 'role', 'schematic', 'state'],
    'overlay': ['align'],
    'radial': [],
    'row': ['align', 'gap'],
    'shape': ['shape', 'state'],
    'split': ['ratio', 'gap'],
    'stack': ['align', 'gap'],
    'surface': ['state', 'gap', 'align'],
    'text': ['contentRef', 'role', 'align', 'state'],
};
/** 每个原语允许绑定的动效配方。 */
export const PRIMITIVE_MOTIONS: Readonly<Record<string, readonly string[]>> = {
    'chart': ['reveal', 'fade', 'rise'],
    'column': ['reveal', 'fade', 'rise'],
    'connector': ['reveal', 'fade', 'draw'],
    'grid': ['reveal', 'fade', 'rise'],
    'group': ['reveal', 'fade', 'rise'],
    'icon': ['reveal', 'fade', 'rise'],
    'image': ['reveal', 'fade', 'rise'],
    'number': ['reveal', 'fade', 'rise', 'count'],
    'overlay': ['reveal', 'fade', 'rise'],
    'radial': ['reveal', 'fade', 'rise'],
    'row': ['reveal', 'fade', 'rise'],
    'shape': ['reveal', 'fade', 'rise', 'draw'],
    'split': ['reveal', 'fade', 'rise'],
    'stack': ['reveal', 'fade', 'rise'],
    'surface': ['reveal', 'fade', 'rise'],
    'text': ['reveal', 'fade', 'rise'],
};
