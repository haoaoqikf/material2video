/**
 * 深空旅程组件的共享工具：色板、帧号、缓动与透明度。
 *
 * 本包不随包携带字体，使用宿主已注册的 `M2V Sans`；时间输入来自受控帧号或
 * R3F 受控时钟，不使用挂钟、`Math.random`、CSS 动画或组件计时器。
 */
import {useSceneContext} from '../../src/code-scene/context';
import tokens from '../tokens.json';

export type JourneyTokens = {
  canvas: {background: string; backgroundAlt: string; starColor: string; starOpacity: number; vignette: number};
  colors: {
    text: string; body: string; nav: string; muted: string;
    line: string; warning: string; footnote: string;
  };
  semantics: Record<string, string>;
  layout: {
    width: number; height: number; marginX: number;
    status: {left: number; top: number};
    chapterTrack: {right: number; top: number; width: number};
    infoPanel: {left: number; top: number; width: number};
    subtitleScrim: {height: number; bottom: number};
    footnote: {left: number; bottom: number; maxWidth: number};
  };
  type: {
    title: number; body: number; panelTitle: number; panelBody: number;
    status: number; chapter: number; footnote: number; fontStack: string;
  };
  motion: {
    fov: number; openingFov: number; cameraEase: string;
    scrimFadeSeconds: number; trackFadeSeconds: number;
  };
};

export const T = tokens as unknown as JourneyTokens;

export function useJourneyFrame(): number {
  const {elapsedSeconds} = useSceneContext();
  const fps = (typeof window === 'undefined' ? undefined : window.__M2V_CODE_CONFIG__?.fps) ?? 60;
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

/** `#RRGGBBaa`；只接受 6 位十六进制，其他格式原样返回。 */
export function alpha(hex: string, value: number): string {
  const cleaned = hex.replace('#', '');
  if (cleaned.length !== 6) return hex;
  const channel = Math.round(clamp01(value) * 255).toString(16).padStart(2, '0');
  return `#${cleaned}${channel}`;
}

export function color(name: keyof JourneyTokens['colors']): string {
  return T.colors[name];
}
