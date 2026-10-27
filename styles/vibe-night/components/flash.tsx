/**
 * 闪：短促的白场覆盖，用于强调一次发现或一次切章。
 * 亮度由帧号与窗口决定，不触发 CSS 动画。
 */
import {clamp01} from './kit';

export type FlashProps = {
  frame: number;
  startFrame: number;
  durationFrames?: number;
  peak?: number;
  color?: string;
  holdEnd?: boolean;
};

export default function Flash({
  frame, startFrame, durationFrames = 6, peak = 0.8, color: flashColor = '#FFFFFF', holdEnd = false,
}: FlashProps) {
  const t = clamp01((frame - startFrame) / Math.max(1, durationFrames));
  if (frame < startFrame) return null;
  const opacity = holdEnd ? peak * Math.min(1, t * 2) : peak * Math.sin(Math.PI * t);
  return (
    <div style={{
      position: 'absolute', inset: 0, background: flashColor, opacity,
      pointerEvents: 'none', willChange: 'opacity',
    }}/>
  );
}
