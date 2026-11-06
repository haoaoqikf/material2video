/**
 * C 夜曲组件的共享工具：字体、帧号、确定性随机与缓动。
 *
 * 所有时间相关的取值都来自受控帧号或 `useSceneContext()` 的录制定时，
 * 不使用挂钟、`Math.random`、CSS 动画或组件计时器。
 */
import {useEffect, useState} from 'react';
import {hashSeed, seededRandom, useSceneContext} from 'm2v/code-scene';
import tokens from '../tokens.json';
import serifUrl from 'm2v/code-scene/serif';

export const SERIF_FAMILY = 'Vibe Night Serif';

export type NightTokens = {
  canvas: {background: string; poolColor: string; poolOpacity: number; vignette: number};
  colors: {
    text: string; gold: string; ice: string; rose: string; violet: string;
    coolWhite: string; muted: string; blood: string; oxygen: string;
  };
  semantics: Record<string, string>;
  layout: {
    width: number; height: number; marginX: number;
    zones: {subject: {top: number; bottom: number}; caption: {top: number; bottom: number}; corner: {top: number; bottom: number}};
  };
  type: {
    title: number; hero: number; small: number; screenSubtitle: number; screenSubtitleMaxChars: number;
    chapterNumber: number; chapterCharacter: number; letterSpacing: string; lineHeight: number;
    baseline: number; captionBaseline: number;
  };
  motion: {
    easing: string; slowPushSeconds: number; revealSeconds: number; closingFadeOutFrames: number;
    flashFrames: number; dipFrames: number; chapterFadeFrames: number; screenSubtitleFadeMs: number;
  };
  glow: {color: string; radius: number; opacity: number};
  backdrop: {stars: number; poolX: number; poolY: number; poolRx: number; poolRy: number; grainDots: number};
  grain: {opacity: number; dotOpacity: number};
};

/** 只读 tokens 的带类型视图；字段由 GUIDE 与规格约定，不改变运行时结构。 */
export const T = tokens as unknown as NightTokens;

let fontPromise: Promise<void> | null = null;

/** 显式加载包内宋体；失败时保持 rejected，调用方不得继续绘制或调用 `ready()`。 */
export function loadNightSerif(): Promise<void> {
  fontPromise ??= (async () => {
    if (typeof document === 'undefined' || typeof FontFace === 'undefined') return;
    const face = new FontFace(SERIF_FAMILY, `url("${serifUrl}") format("truetype")`, {weight: '400', style: 'normal', display: 'block'});
    await face.load();
    document.fonts.add(face);
    await document.fonts.ready;
  })();
  return fontPromise;
}

/** 字体就绪状态；不代替场景发 `ready()`。场景必须在字体与资源就绪后自行调用。 */
export function useNightSerif(): boolean {
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let active = true;
    loadNightSerif().then(() => {
      if (active) setLoaded(true);
    }).catch(() => { /* 保持未就绪，场景的 ready 门不会打开，录制按超时失败。 */ });
    return () => { active = false; };
  }, []);
  return loaded;
}

/** 当前录制帧号；组件显式传入 `frame` 时优先使用显式值。 */
export function useNightFrame(): number {
  const {elapsedSeconds} = useSceneContext();
  const fps = window.__M2V_CODE_CONFIG__?.fps ?? 30;
  return Math.round(elapsedSeconds * fps);
}

export function randomFor(seed: string | number): () => number {
  return seededRandom(typeof seed === 'string' ? hashSeed(seed) : seed >>> 0);
}

export function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

export function lerp(from: number, to: number, progress: number): number {
  return from + (to - from) * clamp01(progress);
}

export function smoothstep(value: number): number {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
}

/** 从 `startFrame` 起、在 `durationFrames` 内完成的 0–1 进度。 */
export function frameProgress(frame: number, startFrame: number, durationFrames: number): number {
  return clamp01((frame - startFrame) / Math.max(1, durationFrames));
}

/** 淡入 → 停留 → 淡出的包络；首末帧保留 0.55 可见度，供按帧文字量测与人眼识别。 */
export function envelope(frame: number, startFrame: number, endFrame: number, fadeFrames: number): number {
  const fade = Math.max(1, fadeFrames);
  const inPart = 0.55 + 0.45 * clamp01((frame - startFrame) / fade);
  const outPart = 0.55 + 0.45 * clamp01((endFrame - frame) / fade);
  return Math.min(inPart, outPart, 1);
}

/** 取色；未登记的颜色回退到近白，避免组件静默写死新语义。 */
export function color(name: keyof NightTokens['colors'], fallback = T.colors.text): string {
  return T.colors[name] ?? fallback;
}
