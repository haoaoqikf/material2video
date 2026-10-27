/**
 * 数轴：带刻度的水平轴，可带一个数值标记。作品用它把时间、年龄或数量
 * 变成当场可读的尺度；`numberLineX` 提供同一套数值到坐标的映射。
 */
import {T, clamp01, color, frameProgress} from './kit';

export type NumberLineProps = {
  x: number;
  y: number;
  width: number;
  min: number;
  max: number;
  ticks?: number;
  labels?: string[];
  marker?: number;
  markerLabel?: string;
  color?: string;
  labelColor?: string;
  markerColor?: string;
  fontSize?: number;
  frame?: number;
  startFrame?: number;
  revealFrames?: number;
  markerStartFrame?: number;
  markerRevealFrames?: number;
  role?: string;
  state?: string;
};

export function numberLineX(
  value: number,
  geometry: {x: number; width: number; min: number; max: number},
): number {
  const span = geometry.max - geometry.min;
  const ratio = span === 0 ? 0 : (value - geometry.min) / span;
  return geometry.x + geometry.width * clamp01(ratio);
}

function defaultLabel(value: number): string {
  if (Math.abs(value) >= 100000000) return `${Number((value / 100000000).toFixed(1))}亿`;
  if (Math.abs(value) >= 10000) return `${Number((value / 10000).toFixed(1))}万`;
  return String(Number(value.toFixed(2)));
}

export default function NumberLine({
  x, y, width, min, max, ticks = 5, labels, marker, markerLabel,
  color: lineColor = color('muted'), labelColor = color('muted'),
  markerColor = color('gold'), fontSize = T.type.small * 0.55,
  frame, startFrame = 0, revealFrames = 0, markerStartFrame, markerRevealFrames, role, state,
}: NumberLineProps) {
  const progress = revealFrames > 0 && frame !== undefined ? frameProgress(frame, startFrame, revealFrames) : 1;
  const markerVisible = markerRevealFrames && markerRevealFrames > 0 && frame !== undefined
    ? frameProgress(frame, markerStartFrame ?? startFrame, markerRevealFrames)
    : revealFrames > 0 && frame !== undefined
      ? clamp01((progress - 0.82) / 0.18)
      : 1;
  const height = Math.max(70, fontSize * 3.2);
  const geometry = {x, width, min, max};
  return (
    <div data-m2v-role={role} data-m2v-state={state} style={{position: 'absolute', left: x, top: y - height * 0.55, width, height, fontSize, pointerEvents: 'none'}}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{overflow: 'visible'}}>
        <line x1={0} y1={height * 0.55} x2={width * progress} y2={height * 0.55}
          stroke={lineColor} strokeWidth={1.2} opacity={0.72}/>
        {Array.from({length: ticks + 1}, (_, index) => {
          const ratio = index / Math.max(1, ticks);
          const value = min + (max - min) * ratio;
          const tickX = width * ratio;
          const visible = tickX <= width * progress + 0.5;
          const label = labels?.[index] ?? defaultLabel(value);
          return (
            <g key={index} opacity={visible ? 1 : 0}>
              <line x1={tickX} y1={height * 0.55 - 6} x2={tickX} y2={height * 0.55 + 6}
                stroke={lineColor} strokeWidth={1} opacity={0.7}/>
              <text x={tickX} y={height * 0.55 + fontSize * 1.7} fill={labelColor}
                fontFamily={'"Vibe Night Serif", "Noto Serif SC", serif'} fontSize={fontSize}
                textAnchor="middle" letterSpacing="0.08em">{label}</text>
            </g>
          );
        })}
        {marker !== undefined && progress > 0 ? (
          <g opacity={markerVisible}>
            <circle cx={numberLineX(marker, geometry) - x} cy={height * 0.55} r={5}
              fill={markerColor} opacity={0.9}/>
            <circle cx={numberLineX(marker, geometry) - x} cy={height * 0.55} r={12}
              fill="none" stroke={markerColor} strokeWidth={1} opacity={0.35}/>
            {markerLabel ? (
              <text x={numberLineX(marker, geometry) - x} y={height * 0.55 - fontSize * 1.5}
                fill={markerColor} fontFamily={'"Vibe Night Serif", "Noto Serif SC", serif'}
                fontSize={fontSize * 1.05} textAnchor="middle" letterSpacing="0.08em">{markerLabel}</text>
            ) : null}
          </g>
        ) : null}
      </svg>
    </div>
  );
}
