/** 波形：由确定性正弦叠加生成的轻量折线；表示声音、电信号或连续变化，不表示实测数据。 */
import type {CSSProperties} from 'react';
import {T, alpha} from './kit';

export type WaveformProps = {
  width?: number;
  height?: number;
  accent?: string;
  progress?: number;
  samples?: number;
  amplitude?: number;
  style?: CSSProperties;
  role?: string;
};

function pointsFor(width: number, height: number, count: number, amplitude: number): string {
  const mid = height / 2;
  return Array.from({length: count}, (_, index) => {
    const x = (index / Math.max(1, count - 1)) * width;
    const y = mid + Math.sin(index * 0.37) * (0.3 + Math.sin(index * 0.11) ** 2 * 0.55) * amplitude;
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(' ');
}

export default function Waveform({
  width = 1050, height = 360, accent = T.colors.copper,
  progress = 0, samples = 80, amplitude = height * 0.42, style, role = 'waveform',
}: WaveformProps) {
  const path = pointsFor(width, height, samples, amplitude);
  const scan = Math.min(1, Math.max(0, progress)) * width;
  return (
    <svg
      data-m2v-role={role}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{position: 'absolute', overflow: 'visible', ...style}}
    >
      <path d={path} fill="none" stroke={alpha(accent, 0.55)} strokeWidth={2}/>
      <line x1={0} y1={height / 2} x2={width} y2={height / 2} stroke={alpha(T.colors.line, 0.18)} strokeWidth={1}/>
      <line x1={scan} y1={0} x2={scan} y2={height} stroke={accent} strokeWidth={2} opacity={0.7}/>
    </svg>
  );
}
