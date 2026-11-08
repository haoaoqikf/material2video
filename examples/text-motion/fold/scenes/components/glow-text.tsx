/**
 * 辉光文字：宋体主体大字，字自身发光，不使用 WebGL 后期。
 * `x`、`y` 是文字中心；调用方负责把文字放在主体区、避开共享字幕安全区。
 */
import type {CSSProperties} from 'react';
import {T, color, useNightSerif} from './kit';

export type GlowTextProps = {
  text: string;
  x: number;
  y: number;
  size?: number;
  color?: string;
  glowColor?: string;
  glow?: number;
  opacity?: number;
  letterSpacing?: string;
  weight?: number;
  align?: 'left' | 'center' | 'right';
  nowrap?: boolean;
};

function alpha(hex: string, value: number): string {
  const cleaned = hex.replace('#', '');
  if (cleaned.length !== 6) return hex;
  const channel = Math.round(Math.min(1, Math.max(0, value)) * 255).toString(16).padStart(2, '0');
  return `#${cleaned}${channel}`;
}

export default function GlowText({
  text, x, y, size = T.type.hero, color: textColor = color('text'),
  glowColor = T.glow.color, glow = 1, opacity = 1,
  letterSpacing = T.type.letterSpacing, weight = 400, align = 'center', nowrap = true,
}: GlowTextProps) {
  useNightSerif();
  const transform = align === 'left' ? 'translate(0, -50%)' : align === 'right' ? 'translate(-100%, -50%)' : 'translate(-50%, -50%)';
  const style: CSSProperties = {
    position: 'absolute', left: x, top: y, transform,
    fontFamily: `"Vibe Night Serif", "Noto Serif SC", serif`,
    fontSize: size, fontWeight: weight, lineHeight: T.type.lineHeight,
    letterSpacing, color: textColor, opacity, whiteSpace: nowrap ? 'nowrap' : 'normal',
    textAlign: align, pointerEvents: 'none',
    textShadow: glow > 0 ? [
      `0 0 ${Math.round(size * 0.12)}px ${alpha(glowColor, 0.55 * glow * opacity)}`,
      `0 0 ${Math.round(size * 0.3)}px ${alpha(glowColor, 0.3 * glow * opacity)}`,
      `0 0 ${Math.round(size * 0.62)}px ${alpha(glowColor, 0.16 * glow * opacity)}`,
    ].join(', ') : 'none',
  };
  return <div style={style}>{text}</div>;
}
