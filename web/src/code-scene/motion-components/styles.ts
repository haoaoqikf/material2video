/** `@remotion/animation-utils` 的薄封装：只用于 CSS 样式，不用于 SVG 数值属性。 */
import type {CSSProperties} from 'react';
import {
  interpolateStyles, makeTransform, matrix, matrix3d, perspective, rotate, rotate3d, rotateX,
  rotateY, rotateZ, scale, scale3d, scaleX, scaleY, scaleZ, skew, skewX, skewY, translate,
  translate3d, translateX, translateY, translateZ,
} from '@remotion/animation-utils';
import {clampProgress, type Easing} from '../primitives';

export function styleAt(
  progress: number, from: CSSProperties, to: CSSProperties, easing?: Easing,
): CSSProperties {
  const input = clampProgress(progress);
  const options = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
  return interpolateStyles(input, [0, 1], [from, to],
    easing ? {...options, easing} : options);
}

export {
  makeTransform, matrix, matrix3d, perspective, rotate, rotate3d, rotateX, rotateY, rotateZ,
  scale, scale3d, scaleX, scaleY, scaleZ, skew, skewX, skewY, translate, translate3d, translateX,
  translateY, translateZ,
};
