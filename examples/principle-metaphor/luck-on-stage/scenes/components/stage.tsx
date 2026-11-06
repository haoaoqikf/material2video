/**
 * 近黑舞台：不透明底色、静态柔和暗角与安全边距。
 *
 * 背景只承担负形，不参与叙事：没有动画噪点、没有持续推拉。主体由作品显式
 * 叠放在舞台之上；组件不会自动换肤。
 */
import type {CSSProperties, ReactNode} from 'react';
import {T} from './kit';

export type StageProps = {
  width?: number;
  height?: number;
  children?: ReactNode;
  /** 背景光池的位置与半径，用画布比例表示；默认居中偏上。 */
  glowX?: number;
  glowY?: number;
  glowRadius?: number;
  style?: CSSProperties;
};

export default function Stage({
  width = T.layout.width, height = T.layout.height, children,
  glowX = 0.5, glowY = 0.42, glowRadius = 0.62, style,
}: StageProps) {
  return (
    <div style={{
      position: 'absolute', inset: 0, width, height, overflow: 'hidden',
      background: T.canvas.background, ...style,
    }}>
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: `radial-gradient(${Math.round(glowRadius * 100)}% ${Math.round(glowRadius * 62)}% at `
          + `${Math.round(glowX * 100)}% ${Math.round(glowY * 100)}%, ${T.canvas.glow} 0%, `
          + `${T.canvas.background} 68%)`,
      }}/>
      {children}
    </div>
  );
}
