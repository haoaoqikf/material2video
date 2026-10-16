/**
 * 讲解画面的视觉主题：颜色、排版、取形、间距、构图、字阶与动效。
 * composition 与代码场景录制页共用同一份真源。
 *
 * 数据放在 `themes.json` 而不是这里，是因为 Python 侧也要读同一份：准备阶段要用主题的
 * 动效帧数编译时间轴（`m2v.engine.themes`）。两处各写一份的话，「改主题」只会改到画面
 * 那一半，判据那一半留在 Python 里不跟着动。
 */
import spec from './themes.json';

export type Palette = {bg: string; ink: string; muted: string; panel: string; border: string; accent: string};
export type Typography = {
  titleWeight: number;
  titleTracking: string;
  titleTransform: 'none' | 'uppercase';
  bodyLineHeight: number;
};
/** 取形：圆角与描边宽度。近直角是某些风格的签名，因此逐角色给值，不给刻度。 */
export type Shape = {
  panelRadius: number;
  cardRadius: number;
  nodeRadius: number;
  mediaRadius: number;
  panelRule: number;
  cardRule: number;
  arrowWidth: number;
};
/** 间距与图形尺寸。逐角色给值：现有取值不构成任何干净的刻度，硬套档位会改变既有画面。 */
export type Layout = {
  sceneTop: number;
  sceneBottom: number;
  titleGap: number;
  panelPadding: number;
  columnGap: number;
  columnPadding: number;
  columnLabelGap: number;
  columnItemGap: number;
  cardGap: number;
  cardPaddingX: number;
  cardPaddingY: number;
  numberGap: number;
  nodeGap: number;
  nodePaddingX: number;
  nodePaddingY: number;
  captionGap: number;
  figureWidth: number;
  causeHeight: number;
  causeLabelTop: number;
  mediaHeight: number;
  codeHeight: number;
};
export type TypeScale = {title: number; lead: number; body: number; note: number; small: number; micro: number};
export type Align = 'start' | 'center';
export type Composition = {align: Align; verticalAlign: Align};
/** 主题动效以**帧数**表达：画面仅由帧号驱动，CSS 动画会被源码闸门拒绝。
 *  `transitionFrames` 缺省表示不覆盖分镜声明，转场时长仍由每幕自己决定。
 *  `entranceEasing` 是三次贝塞尔控制点，`[0,0,1,1]` 即线性。 */
export type Motion = {
  entranceFrames: number;
  holdFrames: number;
  transitionFrames?: number;
  entranceEasing: [number, number, number, number];
};
export type ThemeSpec = {
  colors: Palette;
  typography: Typography;
  shape: Shape;
  layout: Layout;
  typeScale: TypeScale;
  composition: Composition;
  motion: Motion;
};
export type Theme = keyof typeof spec.themes;

/** 每个类别必须齐全的字段。缺一类就明确失败，不用内置默认值补齐。 */
const REQUIRED: Record<string, readonly string[]> = {
  colors: ['bg', 'ink', 'muted', 'panel', 'border', 'accent'],
  typography: ['titleWeight', 'titleTracking', 'titleTransform', 'bodyLineHeight'],
  shape: ['panelRadius', 'cardRadius', 'nodeRadius', 'mediaRadius', 'panelRule', 'cardRule', 'arrowWidth'],
  layout: ['sceneTop', 'sceneBottom', 'titleGap', 'panelPadding', 'columnGap', 'columnPadding', 'columnLabelGap',
    'columnItemGap', 'cardGap', 'cardPaddingX', 'cardPaddingY', 'numberGap', 'nodeGap', 'nodePaddingX',
    'nodePaddingY', 'captionGap', 'figureWidth', 'causeHeight', 'causeLabelTop', 'mediaHeight', 'codeHeight'],
  typeScale: ['title', 'lead', 'body', 'note', 'small', 'micro'],
  composition: ['align', 'verticalAlign'],
  motion: ['entranceFrames', 'holdFrames', 'entranceEasing'],
};

const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

function group(record: Record<string, unknown>, name: string): Record<string, unknown> {
  const value = record[name];
  if (typeof value !== 'object' || value === null) throw new Error(`主题缺少类别 ${name}`);
  return value as Record<string, unknown>;
}

/** 加载即校验：类别缺失或取值非法都在这里失败，不留给画面静默回落。 */
export function assertTheme(name: string, candidate: unknown): ThemeSpec {
  if (typeof candidate !== 'object' || candidate === null) throw new Error(`主题 ${name} 不是对象`);
  const record = candidate as Record<string, unknown>;
  for (const [category, keys] of Object.entries(REQUIRED)) {
    const fields = group(record, category);
    for (const key of keys) {
      if (!(key in fields)) throw new Error(`主题 ${name} 的 ${category} 缺少 ${key}`);
    }
  }
  for (const category of ['shape', 'layout', 'typeScale'] as const) {
    for (const [key, value] of Object.entries(group(record, category))) {
      if (!finite(value) || value < 0) {
        throw new Error(`主题 ${name} 的 ${category}.${key} 必须是非负有限数，实际是 ${String(value)}`);
      }
    }
  }
  const text = group(record, 'typography');
  if (!finite(text.titleWeight) || !finite(text.bodyLineHeight)) {
    throw new Error(`主题 ${name} 的 typography 字重与行高必须是有限数`);
  }
  if (typeof text.titleTracking !== 'string') throw new Error(`主题 ${name} 的 typography.titleTracking 必须是字符串`);
  if (text.titleTransform !== 'none' && text.titleTransform !== 'uppercase') {
    throw new Error(`主题 ${name} 的 typography.titleTransform 只能是 none 或 uppercase`);
  }
  const where = group(record, 'composition');
  for (const key of ['align', 'verticalAlign'] as const) {
    if (where[key] !== 'start' && where[key] !== 'center') {
      throw new Error(`主题 ${name} 的 composition.${key} 只能是 start 或 center`);
    }
  }
  const frames = group(record, 'motion');
  for (const key of ['entranceFrames', 'holdFrames'] as const) {
    if (!finite(frames[key]) || !Number.isInteger(frames[key]) || (frames[key] as number) < 1) {
      throw new Error(`主题 ${name} 的 motion.${key} 必须是正整数`);
    }
  }
  if (frames.transitionFrames !== undefined
      && (!finite(frames.transitionFrames) || !Number.isInteger(frames.transitionFrames) || frames.transitionFrames < 1)) {
    throw new Error(`主题 ${name} 的 motion.transitionFrames 必须是正整数`);
  }
  const easing = frames.entranceEasing;
  if (!Array.isArray(easing) || easing.length !== 4 || !easing.every(finite)) {
    throw new Error(`主题 ${name} 的 motion.entranceEasing 必须是四个有限数`);
  }
  return candidate as ThemeSpec;
}

const THEMES = Object.fromEntries(
  Object.entries(spec.themes as Record<string, unknown>).map(([name, value]) => [name, assertTheme(name, value)]),
) as Record<Theme, ThemeSpec>;

export const THEME_NAMES = Object.keys(THEMES) as Theme[];
export const themeSpec = (theme: Theme): ThemeSpec => THEMES[theme];
export const typography = (theme: Theme): Typography => THEMES[theme].typography;
export const shape = (theme: Theme): Shape => THEMES[theme].shape;
export const layout = (theme: Theme): Layout => THEMES[theme].layout;
export const typeScale = (theme: Theme): TypeScale => THEMES[theme].typeScale;
export const composition = (theme: Theme): Composition => THEMES[theme].composition;
export const motion = (theme: Theme): Motion => THEMES[theme].motion;

/** 颜色按主题取用：composition 与录制页都读它。 */
export const palettes: Record<Theme, Palette> = {
  dark: THEMES.dark.colors,
  light: THEMES.light.colors,
  velvet: THEMES.velvet.colors,
};
