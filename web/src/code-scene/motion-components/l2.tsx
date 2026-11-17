/** L2 共享动效组件：复用 rollNumber/growSeries；所有动画只由 progress 驱动。 */
import {useMemo, type CSSProperties} from 'react';
import rough from 'roughjs';
import {motionCurve} from '../motion';
import {clampProgress, growSeries, rollNumber, type Easing} from '../primitives';
import {pathDrawProps} from './paths';

const LINEAR = motionCurve('linear');

export type RollingNumberProps = {
  from: number;
  to: number;
  progress: number;
  decimals?: number;
  group?: boolean;
  easing?: Easing;
  prefix?: string;
  suffix?: string;
  className?: string;
  style?: CSSProperties;
};

/** 数字滚动：复用 primitives.rollNumber，不引入时间驱动库。 */
export function RollingNumber({
  from, to, progress, decimals = 0, group = false, easing = LINEAR, prefix = '', suffix = '',
  className, style,
}: RollingNumberProps) {
  const {text} = rollNumber({from, to, progress, decimals, easing, group});
  return (
    <span className={className}
      style={{fontVariantNumeric: 'tabular-nums', ...style}}>
      {prefix}{text}{suffix}
    </span>
  );
}

export type BarGrowthProps = {
  values: readonly number[];
  progress: number;
  easing?: Easing;
  stagger?: number;
  floor?: number;
  width?: number;
  height?: number;
  gap?: number;
  color?: string;
  colors?: readonly string[];
  className?: string;
  style?: CSSProperties;
};

/** 柱状生长：复用 primitives.growSeries，直接渲染 SVG rect。 */
export function BarGrowth({
  values, progress, easing = LINEAR, stagger = 0, floor = 0,
  width = 640, height = 360, gap = 8, color = '#F1EBDF', colors,
  className, style,
}: BarGrowthProps) {
  const grown = growSeries({values, progress, floor, easing, stagger}).values;
  const low = Math.min(floor, 0, ...values);
  const high = Math.max(floor, 0, ...values, 1);
  const span = high - low || 1;
  const count = grown.length;
  const barWidth = Math.max(0, (width - gap * Math.max(0, count - 1)) / Math.max(1, count));
  const zeroY = height - ((0 - low) / span) * height;
  return (
    <svg className={className} width={width} height={height}
      viewBox={`0 0 ${width} ${height}`} style={{overflow: 'visible', ...style}}>
      {grown.map((value, index) => {
        const y = height - ((value - low) / span) * height;
        const top = Math.min(y, zeroY);
        const barHeight = Math.abs(y - zeroY);
        return <rect key={index} x={index * (barWidth + gap)} y={top} width={barWidth}
          height={barHeight} fill={colors?.[index] ?? color}/>;
      })}
    </svg>
  );
}

export type MarkerHighlightProps = {
  progress: number;
  box?: {x: number; y: number; width: number; height: number};
  path?: string;
  color?: string;
  strokeWidth?: number;
  seed?: number;
  roughness?: number;
  opacity?: number;
  width?: number;
  height?: number;
  className?: string;
  style?: CSSProperties;
};

/**
 * 手绘高亮：roughjs 生成几何，@remotion/paths 驱动生长。
 * v1 只接受显式 box/path，不做自动 DOM 文本测量；seed 必须显式传入。
 */
export function MarkerHighlight({
  progress, box, path, color = '#F8D893', strokeWidth = 6, seed = 20261102,
  roughness = 1.4, opacity = 1, width = 1920, height = 1080,
  className, style,
}: MarkerHighlightProps) {
  const paths = useMemo(() => {
    if (!box && !path) return [];
    const generator = rough.generator();
    const options = {seed, roughness, stroke: color, strokeWidth, fill: 'none'};
    const drawable = box
      ? generator.rectangle(box.x, box.y, box.width, box.height, options)
      : generator.path(path!, options);
    return generator.toPaths(drawable).map(item => item.d);
  }, [box?.x, box?.y, box?.width, box?.height, path, seed, roughness, color, strokeWidth]);
  if (!paths.length) return null;
  return (
    <svg className={className} width={width} height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none', ...style}}>
      <g opacity={opacity}>
        {paths.map((d, index) => (
          <path key={index} d={d} fill="none" stroke={color} strokeWidth={strokeWidth}
            strokeLinecap="round" strokeLinejoin="round" {...pathDrawProps(d, progress)}/>
        ))}
      </g>
    </svg>
  );
}

export type CalloutProps = {
  text: string;
  at: {x: number; y: number};
  label: {x: number; y: number};
  progress?: number;
  easing?: Easing;
  align?: 'left' | 'right';
  color?: string;
  textColor?: string;
  opacity?: number;
  fontSize?: number;
  fontFamily?: string;
  textShadow?: string;
  className?: string;
  style?: CSSProperties;
};

/** 引线标注：引线按进度生长，文字布局由组件负责。 */
export function Callout({
  text, at, label, progress = 1, easing = LINEAR,
  align = label.x >= at.x ? 'left' : 'right', color = '#FFFFFF', textColor = '#FFFFFF',
  opacity = 1, fontSize = 24, fontFamily = 'system-ui, sans-serif', textShadow,
  className, style,
}: CalloutProps) {
  const path = `M${at.x} ${at.y} L${label.x} ${label.y}`;
  const eased = easing(clampProgress(progress));
  return (
    <div className={className}
      style={{position: 'absolute', inset: 0, opacity, pointerEvents: 'none', ...style}}>
      <svg width="100%" height="100%" style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round"
          {...pathDrawProps(path, eased)}/>
        <circle cx={at.x} cy={at.y} r={5} fill={color}/>
      </svg>
      <div style={{
        position: 'absolute', left: label.x, top: label.y,
        transform: align === 'left' ? 'translate(0, -50%)' : 'translate(-100%, -50%)',
        marginLeft: align === 'left' ? 14 : -14,
        fontFamily, fontSize, color: textColor, whiteSpace: 'nowrap', textShadow,
      }}>{text}</div>
    </div>
  );
}
