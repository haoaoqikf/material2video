/**
 * B 寓言组件的共享工具：颜色、帧号派生、缓动与亚像素工具。
 *
 * 与 C 夜曲不同，本包不随包携带字体：B 寓言用无衬线，直接使用宿主已注册的
 * `M2V Sans` / `M2V Inter`，因此不存在额外的字体恢复步骤。
 * 所有时间输入都来自受控帧号，不使用挂钟、`Math.random`、CSS 动画或组件计时器。
 */
import {hashSeed, seededRandom, useSceneContext} from 'm2v/code-scene';
import tokens from '../tokens.json';

export type ScenePalette = {sky: [string, string]; ground: string; accent: string};

export type FableTokens = {
  canvas: {background: string; vignette: number; vignetteColor: string; glow: number};
  colors: {
    ink: string; gold: string; goldHigh: string; red: string; paper: string;
    paperInk: string; dim: string; mute: string; panel: string;
  };
  semantics: Record<string, string>;
  scenePalette: Record<string, ScenePalette>;
  layout: {
    width: number; height: number; marginX: number; marginY: number;
    gauge: {x: number; y: number; width: number; height: number};
    sceneNote: {x: number; y: number};
    topLine: {y: number};
    counter: {y: number; height: number};
  };
  type: {
    subtitle: number; subtitleTrack: number; subtitleBaseline: number;
    topLine: number; topLineTrack: number; sceneYear: number; scenePlace: number;
    gaugeReadout: number; gaugeObject: number; counterLabel: number; counterNumber: number;
    callout: number; cardTitle: number; cardBody: number; cardTiltDegrees: number;
    title: number; fontStack: string;
  };
  motion: {
    subtitleStaggerSeconds: number; subtitleRiseSeconds: number;
    parallax: {far: number; character: number; near: number};
    slowPushSeconds: number; cardInFrames: number;
  };
  gauge: {min: number; max: number; redFrom: number; ticks: number[]; label: string; overLabel: string};
};

/** 只读 tokens 的带类型视图；字段由 GUIDE 定义，不改变运行时结构。 */
export const T = tokens as unknown as FableTokens;

/** 当前录制帧号；组件显式传入 `frame` 时优先使用显式值。 */
export function useFableFrame(): number {
  const {elapsedSeconds} = useSceneContext();
  const fps = window.__M2V_CODE_CONFIG__?.fps ?? 30;
  return Math.round(elapsedSeconds * fps);
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

export function randomFor(seed: string | number): () => number {
  return seededRandom(typeof seed === 'string' ? hashSeed(seed) : seed >>> 0);
}

/** 取色；未登记的颜色回退到暖白，避免组件静默写死新语义。 */
export function color(name: keyof FableTokens['colors'], fallback = T.colors.ink): string {
  return T.colors[name] ?? fallback;
}

/** 场景配色；未知场景名明确失败，避免静默退回同一种天空。 */
export function palette(scene: string): ScenePalette {
  const found = T.scenePalette[scene];
  if (!found) throw new Error(`未登记的场景配色：${scene}`);
  return found;
}

/** `#RRGGBBaa` 形式；只接受 6 位十六进制，其他格式原样返回。 */
export function alpha(hex: string, value: number): string {
  const cleaned = hex.replace('#', '');
  if (cleaned.length !== 6) return hex;
  const channel = Math.round(clamp01(value) * 255).toString(16).padStart(2, '0');
  return `#${cleaned}${channel}`;
}
