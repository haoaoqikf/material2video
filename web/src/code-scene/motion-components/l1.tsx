/** L1 共享动效：只依赖 progress/easing，不读挂钟、不启动动画。 */
import type {CSSProperties, ReactNode} from 'react';
import {motionCurve} from '../motion';
import {clampProgress, type Easing} from '../primitives';
import {makeTransform, scale, styleAt, translateX, translateY} from './styles';
import {pathDrawProps} from './paths';

const ENTRY_EASING = motionCurve('easeOutCubic');

function dataAttrs(role?: string, state?: string): Record<string, string> {
  return {
    ...(role ? {'data-m2v-role': role} : {}),
    ...(state ? {'data-m2v-state': state} : {}),
  };
}

export type FadeInProps = {
  progress: number;
  from?: number;
  to?: number;
  easing?: Easing;
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
  role?: string;
  state?: string;
};

/** 透明度入场；固定从 0 到 1，可通过 from/to 覆盖。 */
export function FadeIn({
  progress, from = 0, to = 1, easing = ENTRY_EASING, children, className, style, role, state,
}: FadeInProps) {
  const fade = styleAt(progress, {opacity: from}, {opacity: to}, easing);
  return (
    <div {...dataAttrs(role, state)} className={className} style={{...fade, ...style}}>
      {children}
    </div>
  );
}

export type SlideDirection = 'left' | 'right' | 'top' | 'bottom';

export type SlideInProps = {
  progress: number;
  from?: SlideDirection;
  distance?: number;
  easing?: Easing;
  fade?: boolean;
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
  role?: string;
  state?: string;
};

/** 位移入场；fade 为 true 时同时淡入。 */
export function SlideIn({
  progress, from = 'bottom', distance = 24, easing = ENTRY_EASING, fade = false,
  children, className, style, role, state,
}: SlideInProps) {
  const eased = easing(clampProgress(progress));
  const offset = (1 - eased) * distance;
  const transform = from === 'left' ? makeTransform([translateX(-offset)])
    : from === 'right' ? makeTransform([translateX(offset)])
      : from === 'top' ? makeTransform([translateY(-offset)])
        : makeTransform([translateY(offset)]);
  return (
    <div {...dataAttrs(role, state)} className={className}
      style={{transform, ...(fade ? {opacity: eased} : {}), ...style}}>
      {children}
    </div>
  );
}

export type ZoomInProps = {
  progress: number;
  fromScale?: number;
  toScale?: number;
  easing?: Easing;
  fade?: boolean;
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
  role?: string;
  state?: string;
};

/** 缩放入场；transformOrigin 默认中心，可由 style 覆盖。 */
export function ZoomIn({
  progress, fromScale = 0.92, toScale = 1, easing = ENTRY_EASING, fade = false,
  children, className, style, role, state,
}: ZoomInProps) {
  const eased = easing(clampProgress(progress));
  const value = fromScale + (toScale - fromScale) * eased;
  return (
    <div {...dataAttrs(role, state)} className={className}
      style={{transform: makeTransform([scale(value)]), transformOrigin: 'center',
        ...(fade ? {opacity: eased} : {}), ...style}}>
      {children}
    </div>
  );
}

export type BlurProps = {
  progress: number;
  from?: number;
  to?: number;
  easing?: Easing;
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
  role?: string;
  state?: string;
};

/** CSS 模糊；用于 DOM 元素，不用于 Canvas。 */
export function Blur({
  progress, from = 12, to = 0, easing = ENTRY_EASING, children, className, style, role, state,
}: BlurProps) {
  const eased = easing(clampProgress(progress));
  const radius = from + (to - from) * eased;
  return (
    <div {...dataAttrs(role, state)} className={className}
      style={{filter: `blur(${radius}px)`, ...style}}>
      {children}
    </div>
  );
}

export type GlowProps = {
  progress: number;
  from?: number;
  to?: number;
  radius?: number;
  color?: string;
  easing?: Easing;
  mode?: 'filter' | 'textShadow';
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
  role?: string;
  state?: string;
};

/** CSS 辉光；filter 模式用 drop-shadow，textShadow 模式适合文字。 */
export function Glow({
  progress, from = 0, to = 1, radius = 18, color = '#FFFFFF', easing = ENTRY_EASING,
  mode = 'filter', children, className, style, role, state,
}: GlowProps) {
  const eased = easing(clampProgress(progress));
  const amount = from + (to - from) * eased;
  const value = mode === 'textShadow'
    ? {textShadow: `0 0 ${radius * amount}px ${color}`}
    : {filter: `drop-shadow(0 0 ${radius * amount}px ${color})`};
  return (
    <div {...dataAttrs(role, state)} className={className} style={{...value, ...style}}>
      {children}
    </div>
  );
}

export type DrawLineProps = {
  d: string;
  progress: number;
  color?: string;
  strokeWidth?: number;
  dashed?: boolean;
  opacity?: number;
  ghostOffset?: number;
  ghostOpacity?: number;
  ghostWidth?: number;
  linecap?: 'butt' | 'round' | 'square';
  linejoin?: 'miter' | 'round' | 'bevel';
  style?: CSSProperties;
  role?: string;
  state?: string;
};

/**
 * SVG 路径生长；默认返回覆盖父容器的 SVG，路径坐标按父容器像素解释。
 * 虚线默认保持“全显不生长”，与现有 HandDrawnLine/ChartLine 语义一致。
 */
export function DrawLine({
  d, progress, color = '#F3EDDC', strokeWidth = 9, dashed = false, opacity = 1,
  ghostOffset = 0, ghostOpacity = 0.32, ghostWidth, linecap = 'round', linejoin = 'round',
  style, role, state,
}: DrawLineProps) {
  if (!d) return null;
  const draw = dashed
    ? {pathLength: 1, strokeDasharray: '0.014 0.012', strokeDashoffset: 0}
    : pathDrawProps(d, progress);
  const common = {
    fill: 'none', stroke: color, strokeWidth, opacity,
    strokeLinecap: linecap, strokeLinejoin: linejoin,
  };
  return (
    <svg {...dataAttrs(role, state)} width="100%" height="100%"
      style={{position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible',
        pointerEvents: 'none', ...style}}>
      {ghostOffset !== 0 ? (
        <g transform={`translate(${ghostOffset} ${-ghostOffset * 0.6})`} opacity={ghostOpacity}>
          <path d={d} {...common} strokeWidth={ghostWidth ?? Math.max(1, strokeWidth * 0.55)} {...draw}/>
        </g>
      ) : null}
      <path d={d} {...common} {...draw}/>
    </svg>
  );
}
