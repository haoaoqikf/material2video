/** 信号线：沿路径传播的亮段；表示信号、传播或连接，不表示真实数据。 */
import type {CSSProperties} from 'react';
import {T, alpha} from './kit';

export type SignalLineProps = {
  path: string;
  width?: number;
  height?: number;
  accent?: string;
  progress?: number;
  strokeWidth?: number;
  style?: CSSProperties;
  role?: string;
};

export default function SignalLine({
  path, width = 920, height = 260, accent = T.colors.copper,
  progress = 0, strokeWidth = 3, style, role = 'signal',
}: SignalLineProps) {
  const travel = Math.min(1, Math.max(0, progress));
  return (
    <svg
      data-m2v-role={role}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{position: 'absolute', overflow: 'visible', ...style}}
    >
      <path d={path} fill="none" stroke={alpha(accent, 0.36)} strokeWidth={Math.max(1, strokeWidth * 0.66)}/>
      <path
        d={path}
        fill="none"
        stroke={accent}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray="34 1200"
        strokeDashoffset={-travel * 1200}
        opacity={0.9}
      />
      <path d={path} fill="none" stroke={alpha(T.colors.line, 0.16)} strokeWidth={1}/>
    </svg>
  );
}
