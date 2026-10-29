/** 闪光环：克制的扩散圆环；表示闪光、冲击或事件，不表示真实能量数据。 */
import type {CSSProperties} from 'react';
import {T, alpha, clamp01} from './kit';

export type FlashRingsProps = {
  cx?: number;
  cy?: number;
  baseRadius?: number;
  step?: number;
  count?: number;
  accent?: string;
  progress?: number;
  style?: CSSProperties;
  role?: string;
};

export default function FlashRings({
  cx = 350, cy = 350, baseRadius = 95, step = 90, count = 4,
  accent = T.colors.copper, progress = 0, style, role = 'flash',
}: FlashRingsProps) {
  const travel = clamp01(progress);
  return (
    <svg
      data-m2v-role={role}
      width={700}
      height={700}
      viewBox="0 0 700 700"
      style={{position: 'absolute', overflow: 'visible', ...style}}
    >
      {Array.from({length: count}, (_, index) => {
        const radius = baseRadius + index * step + travel * step * 0.5;
        const opacity = Math.max(0, 0.35 - index * 0.045) * (0.4 + 0.6 * travel);
        return (
          <circle
            key={index}
            cx={cx} cy={cy} r={radius}
            fill="none"
            stroke={index % 2 ? accent : T.colors.text}
            strokeWidth={2}
            opacity={opacity}
          />
        );
      })}
      <circle cx={cx} cy={cy} r={12} fill={alpha(accent, 0.9)}/>
    </svg>
  );
}
