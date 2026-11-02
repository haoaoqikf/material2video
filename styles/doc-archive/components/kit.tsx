/**
 * 档案纪录片组件的共享工具：色板、帧号、缓动与档案渐变。
 *
 * 本包不随包携带字体，使用宿主已注册的 `M2V Sans`；所有时间输入来自受控帧号，
 * 不使用挂钟、`Math.random`、CSS 动画或组件计时器。
 */
import {hashSeed, makeTransform, scale as scaleTransform, seededRandom, translate3d, useSceneContext} from 'm2v/code-scene';
import {tokens} from 'm2v/style';

export type ChapterPosition = 'lower' | 'upper' | 'upperNarrow' | 'right' | 'vertical';

export type ArchiveTokens = {
  canvas: {background: string; backgroundAlt: string; vignette: string; line: string};
  colors: {
    text: string; body: string; copper: string; coldCyan: string;
    muted: string; credit: string; shadow: string;
  };
  semantics: Record<string, string>;
  layout: {
    width: number; height: number; marginX: number;
    chapter: Record<ChapterPosition, {
      left?: number; right?: number; top?: number; bottom?: number;
      maxWidth?: number; width?: number;
    }>;
    creditPaddingX: number;
  };
  type: {
    title: number; hero: number; caption: number; year: number;
    alias: number; small: number; fontStack: string;
  };
  motion: {
    chapterRiseSeconds: number; chapterDelaySeconds: number;
    sourceScale: number; sourceScaleGrowth: number; sourceDriftPx: number;
    sourceSaturate: number; sourceContrast: number;
  };
};

export const T = tokens as unknown as ArchiveTokens;

/** 当前录制帧号；场景显式传入 frame 时优先使用显式值。 */
export function useArchiveFrame(): number {
  const {elapsedSeconds} = useSceneContext();
  const fps = (typeof window === 'undefined' ? undefined : window.__M2V_CODE_CONFIG__?.fps) ?? 60;
  return Math.round(elapsedSeconds * fps);
}

export function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

export function ease(value: number): number {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
}

export function lerp(from: number, to: number, progress: number): number {
  return from + (to - from) * clamp01(progress);
}

/** 档案层：轻微缩放 + 横向漂移 + 去饱和/对比；保留素材原生光比。 */
export function archiveGradient(progress: number): {
  transform: string; filter: string;
} {
  const scaleValue = T.motion.sourceScale + T.motion.sourceScaleGrowth * clamp01(progress);
  const drift = T.motion.sourceDriftPx * clamp01(progress);
  return {
    transform: makeTransform([scaleTransform(scaleValue), translate3d(-drift, 0, 0)]),
    filter: `saturate(${T.motion.sourceSaturate}) contrast(${T.motion.sourceContrast})`,
  };
}

/** 章节文字进入：延迟后上浮淡入，由秒数换算。 */
export function chapterReveal(seconds: number): {opacity: number; translateY: number} {
  const progress = ease((seconds - T.motion.chapterDelaySeconds) / T.motion.chapterRiseSeconds);
  return {opacity: progress, translateY: (1 - progress) * 20};
}

/** 确定性随机；只用于装饰纹理，不决定语义。 */
export function randomFor(seed: string | number): () => number {
  return seededRandom(typeof seed === 'string' ? hashSeed(seed) : seed >>> 0);
}

export function color(name: keyof ArchiveTokens['colors']): string {
  return T.colors[name];
}

/** `#RRGGBBaa`；只接受 6 位十六进制，其他格式原样返回。 */
export function alpha(hex: string, value: number): string {
  const cleaned = hex.replace('#', '');
  if (cleaned.length !== 6) return hex;
  const channel = Math.round(clamp01(value) * 255).toString(16).padStart(2, '0');
  return `#${cleaned}${channel}`;
}
