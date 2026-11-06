import {chartLinePath} from 'm2v/code-scene';
/**
 * 论证图表原语：坐标框、曲线、柱列、箭头与标记。
 *
 * 只画调用方给出的几何，不内置公式、刻度值或题材。线条形变按显式进度生长，
 * 不依赖 CSS 动画；坐标与颜色均来自 props。
 */
import type {CSSProperties} from 'react';
import {pathDrawProps, pathLength, pathTangentAtLength} from 'm2v/code-scene';
import {clamp01, LATIN, T} from './kit';

export type Point = [number, number];

export type ChartFrameProps = {
  x: number;
  y: number;
  width: number;
  height: number;
  xTicks?: number[];
  yTicks?: number[];
  xLabels?: string[];
  yLabels?: string[];
  color?: string;
  tickColor?: string;
  labelColor?: string;
  labelSize?: number;
  opacity?: number;
  showLeftAxis?: boolean;
  showBottomAxis?: boolean;
  style?: CSSProperties;
};

/** 坐标框：左轴与底轴；刻度用 0–1 的相对位置，标签由调用方提供。 */
export function ChartFrame({
  x, y, width, height, xTicks = [], yTicks = [], xLabels = [], yLabels = [],
  color = T.colors.line, tickColor = T.colors.line, labelColor = T.colors.muted,
  labelSize = 22, opacity = 1, showLeftAxis = true, showBottomAxis = true, style,
}: ChartFrameProps) {
  return (
    <svg width={x + width + 120} height={y + height + 80}
      viewBox={`0 0 ${x + width + 120} ${y + height + 80}`}
      style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none', ...style}}
      aria-hidden>
      <g opacity={opacity} fontFamily={LATIN} fontSize={labelSize} fill={labelColor}>
        {showLeftAxis ? (
          <line x1={x} y1={y} x2={x} y2={y + height} stroke={color} strokeWidth={2}/>
        ) : null}
        {showBottomAxis ? (
          <line x1={x} y1={y + height} x2={x + width} y2={y + height} stroke={color} strokeWidth={2}/>
        ) : null}
        {xTicks.map((tick, index) => {
          const tx = x + tick * width;
          return (
            <g key={`x-${index}`}>
              <line x1={tx} y1={y + height} x2={tx} y2={y + height + 8} stroke={tickColor} strokeWidth={1.5}/>
              {xLabels[index] ? (
                <text x={tx} y={y + height + 34} textAnchor="middle">{xLabels[index]}</text>
              ) : null}
            </g>
          );
        })}
        {yTicks.map((tick, index) => {
          const ty = y + height - tick * height;
          return (
            <g key={`y-${index}`}>
              <line x1={x - 8} y1={ty} x2={x} y2={ty} stroke={tickColor} strokeWidth={1.5}/>
              {yLabels[index] ? (
                <text x={x - 16} y={ty + 7} textAnchor="end">{yLabels[index]}</text>
              ) : null}
            </g>
          );
        })}
      </g>
    </svg>
  );
}

export type ChartLineProps = {
  points: Point[];
  color?: string;
  width?: number;
  /** 0–1 生长进度；0 时完全不画。 */
  progress?: number;
  opacity?: number;
  /** 用 Catmull-Rom 转三次贝塞尔；默认折线。 */
  smooth?: boolean;
  dashed?: boolean;
};

/** 把点列转成平滑路径；端点重复以保证首尾切线可控。 */
export function smoothPath(points: Point[]): string {
  return points.length < 2 ? '' : chartLinePath(points, 'catmull-rom');
}

export function ChartLine({
  points, color = T.colors.ivory, width = 4, progress = 1, opacity = 1, smooth = false, dashed = false,
}: ChartLineProps) {
  const path = smooth ? smoothPath(points) : chartLinePath(points);
  const value = clamp01(progress);
  if (!path || value <= 0) return null;
  const draw = dashed
    ? {pathLength: 1, strokeDasharray: '0.02 0.018', strokeDashoffset: 0}
    : pathDrawProps(path, value);
  return (
    <path d={path} fill="none" stroke={color} strokeWidth={width}
      strokeLinecap="round" strokeLinejoin="round" opacity={opacity} {...draw}/>
  );
}

export type ChartBar = {x: number; y: number; width: number; height: number; color?: string; opacity?: number};

export function ChartBars({bars, opacity = 1}: {bars: ChartBar[]; opacity?: number}) {
  return (
    <svg width={T.layout.width} height={T.layout.height} viewBox={`0 0 ${T.layout.width} ${T.layout.height}`}
      style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none'}} aria-hidden>
      <g opacity={opacity}>
        {bars.map((bar, index) => (
          <rect key={index} x={bar.x} y={bar.y} width={bar.width} height={bar.height}
            fill={bar.color ?? T.colors.ivory} opacity={bar.opacity ?? 1}/>
        ))}
      </g>
    </svg>
  );
}

export type ChartArrowProps = {
  from: Point;
  to: Point;
  /** 控制点相对弦中点的垂直偏移，正负决定弯曲方向。 */
  bend?: number;
  color?: string;
  width?: number;
  progress?: number;
  opacity?: number;
  head?: number;
};

/** 二次曲线箭头；箭头只在生长接近完成时出现。 */
export function ChartArrow({
  from, to, bend = 0, color = T.colors.ivory, width = 5, progress = 1, opacity = 1, head = 14,
}: ChartArrowProps) {
  const value = clamp01(progress);
  const mx = (from[0] + to[0]) / 2;
  const my = (from[1] + to[1]) / 2;
  const dx = to[0] - from[0];
  const dy = to[1] - from[1];
  const length = Math.hypot(dx, dy) || 1;
  const cx = mx - (dy / length) * bend;
  const cy = my + (dx / length) * bend;
  const path = `M${from[0].toFixed(2)} ${from[1].toFixed(2)} Q${cx.toFixed(2)} ${cy.toFixed(2)} `
    + `${to[0].toFixed(2)} ${to[1].toFixed(2)}`;
  const tangent = pathTangentAtLength(path, Math.max(0, pathLength(path) - 0.001))
    ?? {x: to[0] - cx, y: to[1] - cy};
  const angle = Math.atan2(tangent.y, tangent.x);
  const left = angle + Math.PI * 0.82;
  const right = angle - Math.PI * 0.82;
  const headOpacity = clamp01((value - 0.82) / 0.18);
  const draw = pathDrawProps(path, value);
  return (
    <g opacity={opacity}>
      <path d={path} fill="none" stroke={color} strokeWidth={width} strokeLinecap="round"
        {...draw}/>
      {headOpacity > 0 ? (
        <path
          d={`M${(to[0] + Math.cos(left) * head).toFixed(2)} ${(to[1] + Math.sin(left) * head).toFixed(2)} `
            + `L${to[0].toFixed(2)} ${to[1].toFixed(2)} `
            + `L${(to[0] + Math.cos(right) * head).toFixed(2)} ${(to[1] + Math.sin(right) * head).toFixed(2)}`}
          fill="none" stroke={color} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round"
          opacity={headOpacity}/>
      ) : null}
    </g>
  );
}

export type ChartMarkerProps = {
  x: number;
  y: number;
  radius?: number;
  color?: string;
  halo?: boolean;
  opacity?: number;
  label?: string;
  labelColor?: string;
  labelSize?: number;
  labelX?: number;
  labelY?: number;
  align?: 'start' | 'middle' | 'end';
};

/** 数据点标记；标签是调用方传入的短文本，不是组件内置的题材。 */
export function ChartMarker({
  x, y, radius = 9, color = T.colors.gold, halo = false, opacity = 1, label,
  labelColor = T.colors.ivory, labelSize = 26, labelX, labelY, align = 'middle',
}: ChartMarkerProps) {
  return (
    <g opacity={opacity}>
      {halo ? (
        <circle cx={x} cy={y} r={radius * 2.4} fill="none" stroke={color} strokeWidth={1.4} opacity={0.3}/>
      ) : null}
      <circle cx={x} cy={y} r={radius} fill={color}/>
      {label ? (
        <text x={labelX ?? x} y={labelY ?? y - radius - 18} textAnchor={align}
          fontFamily={LATIN} fontSize={labelSize} fill={labelColor} style={{fontVariantNumeric: 'tabular-nums'}}>
          {label}
        </text>
      ) : null}
    </g>
  );
}
