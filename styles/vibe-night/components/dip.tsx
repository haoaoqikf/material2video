/**
 * 暗一下：章与章之间的黑场呼吸；也可在结尾持续压黑（`holdEnd`）。
 * 只改变覆盖层不透明度，不改变画面内容本身。
 */
import {clamp01} from './kit';

export type DipProps = {
  frame: number;
  startFrame: number;
  durationFrames?: number;
  peak?: number;
  color?: string;
  holdEnd?: boolean;
};

export default function Dip({
  frame, startFrame, durationFrames = 18, peak = 1, color: dipColor = '#000000', holdEnd = false,
}: DipProps) {
  const t = clamp01((frame - startFrame) / Math.max(1, durationFrames));
  if (frame < startFrame) return null;
  const eased = t * t * (3 - 2 * t);
  const opacity = holdEnd ? peak * eased : peak * Math.sin(Math.PI * t);
  return (
    <div style={{
      position: 'absolute', inset: 0, background: dipColor, opacity,
      pointerEvents: 'none', willChange: 'opacity',
    }}/>
  );
}
