/**
 * 纯时间安全的图表组件：折线、面积、迷你趋势与坐标轴。
 *
 * 只做数值映射与静态 SVG；不启动 ECharts、不读帧号或挂钟，
 * 因此可用于 `pure-time` 场景的任意 seek 与并行分块。
 */
import {useId, type CSSProperties, type ReactNode} from 'react';
import {scaleLinear} from 'd3-scale';
import {chartLinePath, chartAreaPath, type ChartCurve} from '../chart-geometry';
export type {ChartCurve} from '../chart-geometry';
import {motionCurve} from '../motion';
import {clampProgress, type Easing} from '../primitives';
import {pathDrawProps} from './paths';

const LINEAR = motionCurve('linear');

export type ChartSeries = {
  values: readonly number[];
  color?: string;
  /** 面积填充色；省略时与描边同色。 */
  fill?: string;
  width?: number;
  dashed?: boolean;
  opacity?: number;
};

export type ChartPadding = {top?: number; right?: number; bottom?: number; left?: number};

function autoYDomain(values: readonly number[], includeZero: boolean): [number, number] {
  let low = Infinity;
  let high = -Infinity;
  for (const value of values) {
    if (!Number.isFinite(value)) continue;
    low = Math.min(low, value);
    high = Math.max(high, value);
  }
  if (!Number.isFinite(low)) return [0, 1];
  if (includeZero) {
    low = Math.min(low, 0);
    high = Math.max(high, 0);
  }
  if (low === high) {
    const pad = Math.abs(low) || 1;
    return [low - pad, high + pad];
  }
  const pad = (high - low) * 0.08;
  return [low - pad, high + pad];
}

function pointsOf(
  values: readonly number[], x: (value: number) => number, y: (value: number) => number,
): [number, number][] {
  const points: [number, number][] = [];
  values.forEach((value, index) => {
    if (Number.isFinite(value)) points.push([x(index), y(value)]);
  });
  return points;
}

export type LinePlotProps = {
  series: readonly ChartSeries[];
  progress: number;
  easing?: Easing;
  width?: number;
  height?: number;
  padding?: ChartPadding;
  xDomain?: readonly [number, number];
  yDomain?: readonly [number, number];
  curve?: ChartCurve;
  /** 同时绘制面积填充；填充按进度从左向右揭示。 */
  area?: boolean;
  areaOpacity?: number;
  color?: string;
  strokeWidth?: number;
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
};

/** 折线/面积图；坐标轴与标注由调用方用 `Axis` 组合到同一个 SVG。 */
export function LinePlot({
  series, progress, easing = LINEAR, width = 960, height = 540, padding = {},
  xDomain, yDomain, curve = 'monotone', area = false, areaOpacity = 0.18,
  color = '#F3EDDC', strokeWidth = 3, children, className, style,
}: LinePlotProps) {
  const rawId = useId();
  const clipId = `m2v-clip-${rawId.replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const pad = {top: 16, right: 16, bottom: 16, left: 16, ...padding};
  const left = pad.left;
  const right = Math.max(left, width - pad.right);
  const top = pad.top;
  const bottom = Math.max(top, height - pad.bottom);
  const maxLength = Math.max(1, ...series.map(item => item.values.length));
  const x = scaleLinear()
    .domain(xDomain ? [...xDomain] : [0, Math.max(1, maxLength - 1)])
    .range([left, right]);
  const autoDomain = autoYDomain(series.flatMap(item => [...item.values]), area);
  const y = scaleLinear().domain(yDomain ? [...yDomain] : autoDomain).range([bottom, top]);
  if (!yDomain) y.nice();
  const eased = easing(clampProgress(progress));
  return (
    <svg className={className} width={width} height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{overflow: 'visible', ...style}}>
      {area ? (
        <defs>
          <clipPath id={clipId}>
            <rect x={left} y={top} width={(right - left) * eased} height={bottom - top}/>
          </clipPath>
        </defs>
      ) : null}
      {series.map((item, index) => {
        const points = pointsOf(item.values, x, y);
        if (points.length < 2) return null;
        const stroke = item.color ?? color;
        const d = chartLinePath(points, curve);
        const seriesArea = chartAreaPath(points, bottom, curve);
        const draw = item.dashed
          ? {strokeDasharray: '8 8'}
          : pathDrawProps(d, eased);
        return (
          <g key={index} opacity={item.opacity ?? 1}>
            {area && seriesArea ? (
              <path d={seriesArea} fill={item.fill ?? stroke} opacity={areaOpacity}
                clipPath={`url(#${clipId})`}/>
            ) : null}
            <path d={d} fill="none" stroke={stroke}
              strokeWidth={item.width ?? strokeWidth}
              strokeLinecap="round" strokeLinejoin="round" {...draw}/>
          </g>
        );
      })}
      {children}
    </svg>
  );
}

export type AreaPlotProps = Omit<LinePlotProps, 'area'>;

/** 面积图：`LinePlot` 的 `area` 预设。 */
export function AreaPlot(props: AreaPlotProps) {
  return <LinePlot {...props} area/>;
}

export type SparklineProps = {
  values: readonly number[];
  progress?: number;
  easing?: Easing;
  width?: number;
  height?: number;
  color?: string;
  strokeWidth?: number;
  fill?: string;
  curve?: ChartCurve;
  className?: string;
  style?: CSSProperties;
};

/** 迷你趋势线：无坐标轴，按容器尺寸直接铺满。 */
export function Sparkline({
  values, progress = 1, easing = LINEAR, width = 320, height = 72, color = '#F3EDDC',
  strokeWidth = 2, fill, curve = 'monotone', className, style,
}: SparklineProps) {
  return (
    <LinePlot series={[{values, color, fill, width: strokeWidth}]} progress={progress}
      easing={easing} width={width} height={height}
      padding={{top: 2, right: 2, bottom: 2, left: 2}} curve={curve}
      area={Boolean(fill)} areaOpacity={1} className={className} style={style}/>
  );
}

export type AxisOrientation = 'x' | 'y';

export type AxisProps = {
  orientation: AxisOrientation;
  domain: readonly [number, number];
  range: readonly [number, number];
  /** 轴线在垂直方向上的坐标；x 轴为 y，y 轴为 x。 */
  at?: number;
  ticks?: number;
  tickFormat?: (value: number) => string;
  tickSize?: number;
  lineWidth?: number;
  color?: string;
  labelColor?: string;
  fontSize?: number;
  fontFamily?: string;
  progress?: number;
  className?: string;
  style?: CSSProperties;
};

/** 坐标轴以 `<g>` 返回，放进 `LinePlot` 的 children 或其他 SVG 中。 */
export function Axis({
  orientation, domain, range, at = 0, ticks = 5, tickFormat = String, tickSize = 6,
  lineWidth = 1, color = 'rgba(255, 255, 255, 0.45)', labelColor = '#F3EDDC',
  fontSize = 18, fontFamily = 'M2V Sans, sans-serif', progress = 1, className, style,
}: AxisProps) {
  const scale = scaleLinear().domain([...domain]).range([...range]);
  const eased = clampProgress(progress);
  const start = range[0];
  const end = start + (range[1] - start) * eased;
  const values = scale.ticks(ticks);
  const span = range[1] - range[0] || 1;
  return (
    <g className={className} style={style}>
      {orientation === 'x' ? (
        <line x1={start} x2={end} y1={at} y2={at} stroke={color} strokeWidth={lineWidth}/>
      ) : (
        <line x1={at} x2={at} y1={start} y2={end} stroke={color} strokeWidth={lineWidth}/>
      )}
      {values.map(value => {
        const position = scale(value);
        const visible = (position - range[0]) / span <= eased + 1e-9;
        if (!visible) return null;
        const label = tickFormat(value);
        return orientation === 'x' ? (
          <g key={value}>
            <line x1={position} x2={position} y1={at} y2={at + tickSize} stroke={color}
              strokeWidth={lineWidth}/>
            <text x={position} y={at + tickSize + fontSize} fill={labelColor}
              fontFamily={fontFamily} fontSize={fontSize} textAnchor="middle">{label}</text>
          </g>
        ) : (
          <g key={value}>
            <line x1={at - tickSize} x2={at} y1={position} y2={position} stroke={color}
              strokeWidth={lineWidth}/>
            <text x={at - tickSize - 4} y={position + fontSize * 0.35} fill={labelColor}
              fontFamily={fontFamily} fontSize={fontSize} textAnchor="end">{label}</text>
          </g>
        );
      })}
    </g>
  );
}
