/** 有机漂移：由 `@remotion/noise` 的种子噪声生成，不读时间源。 */
import type {CSSProperties, ReactNode} from 'react';
import {noise2D} from '@remotion/noise';
import {clampProgress} from '../primitives';
import {makeTransform, rotate, scale, translateX, translateY} from './styles';

export type NoiseSeed = string | number;

/** 二维种子噪声，返回 -1–1；相同 seed 与坐标永远相同。 */
export function noiseAt(seed: NoiseSeed, x: number, y = 0): number {
  return noise2D(seed, x, y);
}

export type NoiseDriftOptions = {
  seed?: NoiseSeed;
  progress: number;
  /** 位移振幅（像素）。 */
  amount?: number;
  /** 进度换算到噪声坐标的倍率；越大抖动越密。 */
  frequency?: number;
  /** 旋转振幅（度）。 */
  rotateAmount?: number;
  /** 缩放振幅；0.02 表示 ±2%。 */
  scaleAmount?: number;
};

export type NoiseDriftValue = {x: number; y: number; rotate: number; scale: number};

/** 把进度映射成位移、旋转与缩放；四个通道使用不同噪声偏移，避免同相抖动。 */
export function noiseDrift({
  seed = 'default', progress, amount = 6, frequency = 1, rotateAmount = 0.4,
  scaleAmount = 0,
}: NoiseDriftOptions): NoiseDriftValue {
  const t = clampProgress(progress) * frequency;
  return {
    x: noise2D(seed, t, 0) * amount,
    y: noise2D(seed, t, 1000) * amount,
    rotate: noise2D(seed, t, 2000) * rotateAmount,
    scale: 1 + noise2D(seed, t, 3000) * scaleAmount,
  };
}

export type NoiseDriftProps = NoiseDriftOptions & {
  children?: ReactNode;
  className?: string;
  style?: CSSProperties;
};

/** 手持感/呼吸感包装；只施加静态 transform，不做 CSS 动画。 */
export function NoiseDrift({
  seed = 'default', progress, amount = 6, frequency = 1, rotateAmount = 0.4,
  scaleAmount = 0, children, className, style,
}: NoiseDriftProps) {
  const drift = noiseDrift({seed, progress, amount, frequency, rotateAmount, scaleAmount});
  const transform = makeTransform([
    translateX(drift.x), translateY(drift.y), rotate(drift.rotate), scale(drift.scale),
  ]);
  return (
    <div className={className} style={{transform, ...style}}>
      {children}
    </div>
  );
}
