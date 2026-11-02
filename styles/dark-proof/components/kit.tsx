/**
 * 暗场论证组件的共享工具：tokens 类型视图、受控帧号、确定性随机与缓动。
 *
 * 所有随时间变化的取值都来自录制帧号或显式传入的秒数；不使用挂钟、
 * `Math.random`、CSS 动画或组件计时器。组件只提供表现层，不携带题材数学、
 * 文案或事件时刻。
 */
import {hashSeed, seededRandom, useSceneContext} from 'm2v/code-scene';
import {tokens} from 'm2v/style';

export type DarkProofTokens = {
  canvas: {background: string; glow: string; line: string};
  colors: {ink: string; ivory: string; gold: string; ember: string; muted: string; line: string};
  semantics: Record<string, string>;
  layout: {width: number; height: number; marginX: number; subjectTop: number; subjectBottom: number};
  type: {
    hero: number; heroLarge: number; title: number; lead: number; body: number;
    small: number; english: number; micro: number; lineHeight: number;
    fontSans: string; fontLatin: string; tabular: boolean;
  };
  motion: {
    enter: string; inScene: string; dissolveSeconds: number; revealSeconds: number;
    bpm: number; pushScale: number;
  };
  dots: {radius: number; fieldRadius: number; highlightRadius: number};
  light: {
    core: string; gold: string; ivory: string; ember: string;
    trailSamples: number; trailLengthRatio: number; trailWidth: number;
    burstCount: number; burstDistance: number; burstLifetime: number;
    ringCount: number; ringTravel: number; ringThickness: number; ringOpacity: number;
    impact: Record<'shatter' | 'reveal' | 'formula' | 'finale', {
      count: number; reach: number; frames: number; rings: number; ringTravel: number;
      flash: number; bokeh: number;
    }>;
    dust: {count: number; opacity: number; drift: number; size: number};
  };
  subtitleMotion: {
    enterFrames: number; exitFrames: number; risePx: number; driftPx: number;
    englishDelayFrames: number; charStaggerFrames: number; charRevealFrames: number; glow: number;
  };
  subtitles: {zh: number; en: number; lineGap: number};
};

/** 只读 tokens 的带类型视图；字段由 GUIDE 与规格约定，不改变运行时结构。 */
export const T = tokens as unknown as DarkProofTokens;

/** 中文主体与标题；缺字时宿主字体加载会明确失败，不静默回退到系统字体。 */
export const SANS = '"M2V Sans", "M2V Inter", sans-serif';
/** 英文短标签与数字；等宽数字依赖 M2V Inter。 */
export const LATIN = '"M2V Inter", "M2V Sans", sans-serif';
export const NUMERIC = '"M2V Inter", "M2V Sans", sans-serif';

/** 当前录制帧号；显式传入 `frame` 的组件不调用本函数。 */
export function useProofFrame(fps = 30): number {
  const {elapsedSeconds} = useSceneContext();
  return Math.round(elapsedSeconds * fps);
}

export function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

export function lerp(from: number, to: number, progress: number): number {
  return from + (to - from) * clamp01(progress);
}

/** 从 `startFrame` 起、在 `durationFrames` 内完成的 0–1 进度。 */
export function frameProgress(frame: number, startFrame: number, durationFrames: number): number {
  return clamp01((frame - startFrame) / Math.max(1, durationFrames));
}

/** 入场与抵达；与 GUIDE 的运动人格一致，不做过冲。 */
export function easeOutCubic(value: number): number {
  const t = clamp01(value);
  return 1 - Math.pow(1 - t, 3);
}

/** 画面内移动与状态切换。 */
export function easeInOutSine(value: number): number {
  const t = clamp01(value);
  return -(Math.cos(Math.PI * t) - 1) / 2;
}

export function smoothstep(value: number): number {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
}

/** 淡入 → 停留 → 淡出的包络；首末帧保留部分可见度，避免量测帧全透明。 */
export function envelope(frame: number, startFrame: number, endFrame: number, fadeFrames = 6): number {
  const fade = Math.max(1, fadeFrames);
  const inPart = 0.55 + 0.45 * clamp01((frame - startFrame) / fade);
  const outPart = 0.55 + 0.45 * clamp01((endFrame - frame) / fade);
  return Math.min(inPart, outPart, 1);
}

/** 确定性随机序列；同一种子在任何机器、任何次运行都给出同一串数。 */
export function randomFor(seed: string | number): () => number {
  return seededRandom(typeof seed === 'string' ? hashSeed(seed) : seed >>> 0);
}

/** 取色；未登记的颜色回退到米白，避免组件静默写死新语义。 */
export function color(name: keyof DarkProofTokens['colors'], fallback = T.colors.ivory): string {
  return T.colors[name] ?? fallback;
}

function parseHex(hex: string): [number, number, number] {
  return [1, 3, 5].map(at => parseInt(hex.slice(at, at + 2), 16)) as [number, number, number];
}

/** 两色线性混合；用于状态过渡，不替代语义取色。 */
export function mixColor(from: string, to: string, amount: number): string {
  const ratio = clamp01(amount);
  const a = parseHex(from);
  const b = parseHex(to);
  const channel = (index: number) => Math.round(a[index] + (b[index] - a[index]) * ratio)
    .toString(16).padStart(2, '0');
  return `#${channel(0)}${channel(1)}${channel(2)}`;
}

export function formatNumber(value: number, decimals = 0): string {
  return value.toFixed(decimals);
}

/** 数字的等宽字体样式；同一量级的数字保持同一字号。 */
export const NUMERIC_STYLE = {
  fontFamily: NUMERIC,
  fontVariantNumeric: 'tabular-nums' as const,
  fontFeatureSettings: '"tnum" 1',
};
