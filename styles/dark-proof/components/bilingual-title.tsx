/**
 * 双语标题：中文主讲在上，英文短标签在下；英文只做纹理，不逐字直译。
 *
 * 三级字阶中的“中文标题与主讲”由调用方选择 60–112 px；英文小字取 20–28 px。
 * 金色短线只作为标题的落点，不承载结论色；显隐由调用方传入的 opacity 控制。
 */
import type {CSSProperties} from 'react';
import {LATIN, SANS, T} from './kit';

export type BilingualTitleProps = {
  zh: string;
  en?: string;
  x: number;
  y: number;
  size?: number;
  enSize?: number;
  color?: string;
  enColor?: string;
  opacity?: number;
  align?: 'left' | 'center' | 'right';
  /** 标题上方的金色短线；0 时不画。 */
  ruleWidth?: number;
  ruleProgress?: number;
  lineHeight?: number;
  style?: CSSProperties;
};

export default function BilingualTitle({
  zh, en, x, y, size = T.type.title, enSize = T.type.english, color = T.colors.ivory,
  enColor = T.colors.muted, opacity = 1, align = 'left', ruleWidth = 72, ruleProgress = 1,
  lineHeight = 1.18, style,
}: BilingualTitleProps) {
  const translate = align === 'center' ? '-50%' : align === 'right' ? '-100%' : '0';
  return (
    <div
      data-m2v-role="bilingual-title"
      style={{
        position: 'absolute', left: x, top: y, transform: `translate(${translate}, -50%)`,
        opacity, textAlign: align, whiteSpace: 'nowrap', ...style,
      }}
    >
      {ruleWidth > 0 ? (
        <div style={{
          width: ruleWidth * Math.max(0, Math.min(1, ruleProgress)), height: 3,
          background: T.colors.gold, opacity: 0.9,
          marginLeft: align === 'center' ? 'auto' : align === 'right' ? 'auto' : 0,
          marginRight: align === 'center' ? 'auto' : align === 'right' ? 0 : 'auto',
          marginBottom: Math.round(size * 0.16),
        }}/>
      ) : null}
      <div style={{
        fontFamily: SANS, fontSize: size, lineHeight, letterSpacing: '0.02em',
        color, fontWeight: 400,
      }}>{zh}</div>
      {en ? (
        <div style={{
          fontFamily: LATIN, fontSize: enSize, lineHeight: 1.4, letterSpacing: '0.2em',
          textTransform: 'uppercase', color: enColor, marginTop: Math.round(size * 0.14),
        }}>{en}</div>
      ) : null}
    </div>
  );
}
