/** 圆弧仪表与环形进度：SVG 路径长度归一化，进度由调用方给出。 */
import type {CSSProperties, ReactNode} from 'react';
import {clampProgress, type Easing} from '../primitives';
import {dataAttrs} from './internal';

const IDENTITY: Easing = value => value;

export type ArcPoint = {x: number; y: number};

/** 0° 在正上方、顺时针；整圆用两段半圆避免起终点重合退化。 */
export function arcPath(
  cx: number, cy: number, radius: number, startAngle: number, endAngle: number,
): string {
  if (radius <= 0) return '';
  if (endAngle - startAngle >= 360) {
    return `M ${cx} ${cy - radius} A ${radius} ${radius} 0 1 1 ${cx} ${cy + radius} `
      + `A ${radius} ${radius} 0 1 1 ${cx} ${cy - radius}`;
  }
  if (endAngle <= startAngle) return '';
  const pointAt = (angle: number): ArcPoint => {
    const radians = ((angle - 90) * Math.PI) / 180;
    return {x: cx + radius * Math.cos(radians), y: cy + radius * Math.sin(radians)};
  };
  const start = pointAt(startAngle);
  const end = pointAt(endAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

export type ArcGaugeProps = {
  /** 0–1 的进度；提供 value/min/max 时以数值换算。 */
  progress?: number;
  value?: number;
  min?: number;
  max?: number;
  size?: number;
  thickness?: number;
  startAngle?: number;
  endAngle?: number;
  color?: string;
  trackColor?: string;
  cap?: 'butt' | 'round' | 'square';
  easing?: Easing;
  className?: string;
  style?: CSSProperties;
  role?: string;
  state?: string;
};

/** 单弧仪表；轨道与进度弧使用同一路径，避免两个坐标系对不齐。 */
export function ArcGauge({
  progress = 0, value, min = 0, max = 100, size = 240, thickness = 18,
  startAngle = -135, endAngle = 135, color = '#F8D893',
  trackColor = 'rgba(255, 255, 255, 0.12)', cap = 'round', easing = IDENTITY,
  className, style, role, state,
}: ArcGaugeProps) {
  const ratio = value === undefined ? progress : (value - min) / (max - min);
  const eased = easing(clampProgress(Number.isFinite(ratio) ? ratio : 0));
  const radius = Math.max(0, (size - thickness) / 2);
  const d = arcPath(size / 2, size / 2, radius, startAngle, endAngle);
  if (!d) return null;
  return (
    <svg {...dataAttrs(role, state)} className={className} width={size} height={size}
      viewBox={`0 0 ${size} ${size}`}
      style={{overflow: 'visible', ...style}}>
      <path d={d} fill="none" stroke={trackColor} strokeWidth={thickness} strokeLinecap={cap}/>
      {eased > 0 ? (
        <path d={d} fill="none" stroke={color} strokeWidth={thickness} strokeLinecap={cap}
          pathLength={1} strokeDasharray="1" strokeDashoffset={1 - eased}/>
      ) : null}
    </svg>
  );
}

export type ProgressRingProps = Omit<ArcGaugeProps, 'startAngle' | 'endAngle'> & {
  children?: ReactNode;
};

/** 整圆进度环；children 居中放在环内，用于数字或图标。 */
export function ProgressRing({
  progress = 0, value, min, max, size = 240, thickness = 18, color, trackColor, cap, easing,
  className, style, role, state, children,
}: ProgressRingProps) {
  return (
    <div {...dataAttrs(role, state)} className={className}
      style={{position: 'relative', width: size, height: size, ...style}}>
      <ArcGauge progress={progress} value={value} min={min} max={max} size={size}
        thickness={thickness} startAngle={0} endAngle={360} color={color}
        trackColor={trackColor} cap={cap} easing={easing}/>
      {children ? (
        <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
          justifyContent: 'center'}}>{children}</div>
      ) : null}
    </div>
  );
}
