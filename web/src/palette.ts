/**
 * 讲解画面的视觉主题：颜色、排版与动效。composition 与代码场景录制页共用同一份真源。
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
/** 主题动效以**帧数**表达：画面仅由帧号驱动，CSS 动画会被源码闸门拒绝。
 *  `transitionFrames` 缺省表示不覆盖分镜声明，转场时长仍由每幕自己决定。 */
export type Motion = {entranceFrames: number; holdFrames: number; transitionFrames?: number};
export type Theme = keyof typeof spec.themes;
type ThemeSpec = {colors: Palette; typography: Typography; motion: Motion};

/** JSON 表达不了 `'none' | 'uppercase'` 这样的字面量联合，在这里收一次口。 */
const THEMES = spec.themes as unknown as Record<Theme, ThemeSpec>;

export const THEME_NAMES = Object.keys(THEMES) as Theme[];
export const typography = (theme: Theme): Typography => THEMES[theme].typography;
export const motion = (theme: Theme): Motion => THEMES[theme].motion;

/** 颜色按主题取用：composition 与录制页都读它。 */
export const palettes: Record<Theme, Palette> = {
  dark: THEMES.dark.colors,
  light: THEMES.light.colors,
  velvet: THEMES.velvet.colors,
};
