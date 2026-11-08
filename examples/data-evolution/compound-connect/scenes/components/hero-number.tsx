/**
 * 巨型数字：一个画面只承担一个数字或结论。
 *
 * 字号由调用方按 tokens 的三级字阶选择（巨型 220–320 px）；数字使用等宽数字
 * 与紧行高。缩放只围绕自身中心，不改变布局坐标；显隐由调用方传入的 opacity
 * 与 scale 驱动，组件不自行计时。
 */
import type {CSSProperties} from 'react';
import {makeTransform, scale as scaleTransform} from '../../src/code-scene/motion-components/styles';
import {NUMERIC_STYLE, T} from './kit';

export type HeroNumberProps = {
  value: string;
  x: number;
  y: number;
  size?: number;
  color?: string;
  opacity?: number;
  scale?: number;
  /** 数值后的单位或小字，和小字差一个层级。 */
  suffix?: string;
  suffixSize?: number;
  align?: 'center' | 'left' | 'right';
  weight?: number;
  style?: CSSProperties;
};

export default function HeroNumber({
  value, x, y, size = T.type.hero, color = T.colors.ivory, opacity = 1, scale = 1,
  suffix, suffixSize = Math.round(size * 0.2), align = 'center', weight = 300, style,
}: HeroNumberProps) {
  const translate = align === 'center' ? '-50%' : align === 'right' ? '-100%' : '0';
  return (
    <div
      style={{
        position: 'absolute', left: x, top: y,
        transform: `translate(${translate}, -50%) ${makeTransform([scaleTransform(scale)])}`,
        transformOrigin: align === 'center' ? 'center' : align === 'right' ? 'right center' : 'left center',
        ...NUMERIC_STYLE, fontSize: size, lineHeight: 0.9,
        letterSpacing: '-0.035em', color, opacity, whiteSpace: 'nowrap',
        display: 'flex', alignItems: 'baseline', gap: Math.round(size * 0.06), ...style,
      }}
    >
      <span style={{fontWeight: weight}}>{value}</span>
      {suffix ? (
        <span style={{fontSize: suffixSize, fontWeight: 400, letterSpacing: '0.02em', opacity: 0.85}}>
          {suffix}
        </span>
      ) : null}
    </div>
  );
}
