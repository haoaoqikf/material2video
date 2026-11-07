/** SVG 数值文字：等宽数字，颜色与字号来自 tokens 或显式 props。 */
import type {ReactNode} from 'react';
import {T} from './kit';

export type NumberTextProps = {
  x: number;
  y: number;
  size?: number;
  color?: string;
  opacity?: number;
  anchor?: 'start' | 'middle' | 'end';
  weight?: number;
  children: ReactNode;
};

export default function NumberText({
  x, y, size = T.type.body, color = T.colors.offWhite, opacity = 1,
  anchor = 'start', weight = 500, children, }: NumberTextProps) {
  return (
    <text
      x={x}
      y={y}
      fontSize={size}
      fill={color}
      opacity={opacity}
      textAnchor={anchor}
      fontWeight={weight}
      style={{fontFamily: T.type.fontStack, fontVariantNumeric: 'tabular-nums'}}
    >
      {children}
    </text>
  );
}
