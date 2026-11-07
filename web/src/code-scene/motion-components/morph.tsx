/** 路径形变与遮罩揭示：几何只由 progress 决定。 */
import type {CSSProperties, ReactNode} from 'react';
import {motionCurve} from '../motion';
import {clampProgress, type Easing} from '../primitives';
import {pathMorphAt} from './paths';

const LINEAR = motionCurve('linear');

export type PathMorphProps = {
  from: string;
  to: string;
  progress: number;
  easing?: Easing;
  color?: string;
  fill?: string;
  strokeWidth?: number;
  opacity?: number;
  width?: number | string;
  height?: number | string;
  viewBox?: string;
  className?: string;
  style?: CSSProperties;
};

/**
 * 两条同结构路径之间的形变；不做拓扑匹配，需要对应点时应先自行重采样。
 * 省略 viewBox 时路径坐标按像素解释，适合与父容器同尺寸。
 */
export function PathMorph({
  from, to, progress, easing = LINEAR, color = '#F3EDDC', fill = 'none',
  strokeWidth = 6, opacity = 1, width = '100%', height = '100%', viewBox, className, style,
}: PathMorphProps) {
  const d = pathMorphAt(easing(clampProgress(progress)), from, to);
  if (!d) return null;
  return (
    <svg
      className={className}
      width={width}
      height={height}
      viewBox={viewBox}
      style={{position: 'absolute', inset: 0, overflow: 'visible', pointerEvents: 'none',
        ...style}}
    >
      <path d={d} fill={fill} stroke={color} strokeWidth={strokeWidth} opacity={opacity}
        strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

export type MaskRevealMode = 'wipe' | 'iris';
export type WipeDirection = 'left' | 'right' | 'top' | 'bottom';

export type MaskRevealProps = {
  progress: number;
  easing?: Easing;
  mode?: MaskRevealMode;
  /** wipe 的揭示方向；right 表示从左向右展开。 */
  direction?: WipeDirection;
  /** iris 的中心与最大半径；省略半径时按 width/height 四角最远点计算。 */
  at?: {x: number; y: number};
  radius?: number;
  width?: number;
  height?: number;
  /** 完全自定义：接收已缓动的 0–1 进度，返回 CSS clip-path 值。 */
  clip?: (progress: number) => string;
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
};

/** 用静态 `clip-path` 揭示内容；不写 CSS transition，逐帧值由调用方计算。 */
export function MaskReveal({
  progress, easing = motionCurve('easeOutCubic'), mode = 'wipe', direction = 'right',
  at = {x: 0, y: 0}, radius, width = 1920, height = 1080, clip, children, className, style,
}: MaskRevealProps) {
  const eased = easing(clampProgress(progress));
  let clipPath: string;
  if (clip) {
    clipPath = clip(eased);
  } else if (mode === 'iris') {
    const reach = radius ?? Math.hypot(
      Math.max(at.x, width - at.x), Math.max(at.y, height - at.y),
    );
    clipPath = `circle(${eased * reach}px at ${at.x}px ${at.y}px)`;
  } else {
    const hidden = (1 - eased) * 100;
    clipPath = direction === 'right' ? `inset(0 ${hidden}% 0 0)`
      : direction === 'left' ? `inset(0 0 0 ${hidden}%)`
        : direction === 'bottom' ? `inset(${hidden}% 0 0 0)`
          : `inset(0 0 ${hidden}% 0)`;
  }
  return (
    <div className={className}
      style={{clipPath, WebkitClipPath: clipPath, ...style}}>
      {children}
    </div>
  );
}
