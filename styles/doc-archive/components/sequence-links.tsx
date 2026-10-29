/** 序列连接：成对的左右节点与曲线连接；表示编码、配对或序列关系。 */
import type {CSSProperties} from 'react';
import {T, alpha, clamp01} from './kit';

export type SequenceLinksProps = {
  rows?: number;
  width?: number;
  height?: number;
  accent?: string;
  progress?: number;
  style?: CSSProperties;
  role?: string;
};

export default function SequenceLinks({
  rows = 25, width = 820, height = 390, accent = T.colors.copper,
  progress = 0, style, role = 'sequence',
}: SequenceLinksProps) {
  const travel = clamp01(progress);
  return (
    <svg
      data-m2v-role={role}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{position: 'absolute', overflow: 'visible', ...style}}
    >
      {Array.from({length: rows}, (_, index) => {
        const y = 22 + index * 14;
        const swing = Math.sin((index / Math.max(1, rows)) * Math.PI * 2 + travel * Math.PI * 2) * 95;
        const left = 270 + swing;
        const right = 270 - swing;
        const opacity = 0.22 + 0.5 * clamp01(travel * 2 - index / rows);
        return (
          <g key={index} opacity={opacity}>
            <path
              d={`M${left} ${y} Q500 ${y} ${right} ${y}`}
              fill="none"
              stroke={index % 2 ? accent : T.colors.copper}
              strokeWidth={2}
            />
            <circle cx={left} cy={y} r={4} fill={accent}/>
            <circle cx={right} cy={y} r={4} fill={alpha(T.colors.copper, 0.8)}/>
          </g>
        );
      })}
    </svg>
  );
}
