/**
 * 可数物证组件的共享工具：色板、帧号、缓动与颜色混合。
 *
 * 本包不随包携带字体，使用宿主已注册的 `M2V Sans`；所有时间输入来自受控帧号，
 * 不使用挂钟、`Math.random`、CSS 动画或组件计时器。
 */
import {useSceneContext} from 'm2v/code-scene';
import {tokens} from 'm2v/style';

export type LedgerTokens = {
  canvas: {background: string; shadow: string; line: string};
  colors: {offWhite: string; gold: string; darkGold: string; muted: string; ink: string};
  semantics: Record<string, string>;
  layout: {
    width: number; height: number; marginX: number;
    subjectTop: number; subjectBottom: number; labelBaseline: number;
  };
  type: {
    title: number; hero: number; body: number; small: number; micro: number;
    fontStack: string; tabular: boolean;
  };
  disc: {
    radius: number; pitch: number; gap: number; highlightWidthRatio: number;
    shadowOffsetX: number; shadowOffsetY: number; shadowOpacity: number;
  };
  motion: {cameraEase: string; stateMixSeconds: number; revealSeconds: number};
};

export const T = tokens as unknown as LedgerTokens;

export type DiscState = 'white' | 'gold' | 'dark';

/** 当前录制帧号；场景显式传入 frame 时优先使用显式值。 */
export function useLedgerFrame(): number {
  const {elapsedSeconds} = useSceneContext();
  const fps = (typeof window === 'undefined' ? undefined : window.__M2V_CODE_CONFIG__?.fps) ?? 30;
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

export function ease(value: number): number {
  return smoothstep(value);
}

/** 从 `startFrame` 起、在 `durationFrames` 内完成的 0–1 进度。 */
export function frameProgress(frame: number, startFrame: number, durationFrames: number): number {
  return clamp01((frame - startFrame) / Math.max(1, durationFrames));
}

/** 三态语义色；未知状态明确失败，避免静默写死第四种状态。 */
export function discFill(state: DiscState): string {
  const fill = state === 'white' ? T.colors.offWhite
    : state === 'gold' ? T.colors.gold
      : state === 'dark' ? T.colors.darkGold : undefined;
  if (!fill) throw new Error(`未登记的可数对象状态：${String(state)}`);
  return fill;
}

/** `#RRGGBB` 之间线性混合；其他格式原样返回。 */
export function mixColor(from: string, to: string, progress: number): string {
  if (!/^#[0-9a-fA-F]{6}$/.test(from) || !/^#[0-9a-fA-F]{6}$/.test(to)) return from;
  const a = parseInt(from.slice(1), 16);
  const b = parseInt(to.slice(1), 16);
  const t = clamp01(progress);
  const channel = (shift: number) => Math.round(((a >> shift) & 255) * (1 - t) + ((b >> shift) & 255) * t);
  return `rgb(${channel(16)},${channel(8)},${channel(0)})`;
}

/** `#RRGGBBaa`；只接受 6 位十六进制，其他格式原样返回。 */
export function alpha(hex: string, value: number): string {
  const cleaned = hex.replace('#', '');
  if (cleaned.length !== 6) return hex;
  const channel = Math.round(clamp01(value) * 255).toString(16).padStart(2, '0');
  return `#${cleaned}${channel}`;
}

export function formatNumber(value: number, digits = 0): string {
  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
