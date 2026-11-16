/** 章节文字：年份、标题、别名与一句贡献；五种位置变体，进入由秒数换算。 */
import type {CSSProperties} from 'react';
import {makeTransform, translateY} from '../../src/code-scene/motion-components/styles';
import {T, chapterReveal, type ChapterPosition} from './kit';

export type ChapterTextProps = {
  year: string;
  title: string;
  caption: string;
  alias?: string;
  accent?: string;
  textColor?: string;
  position?: ChapterPosition;
  seconds?: number;
  style?: CSSProperties;
};

export default function ChapterText({
  year, title, caption, alias, accent = T.colors.copper, textColor,
  position = 'lower', seconds, style, }: ChapterTextProps) {
  const reveal = seconds === undefined ? {opacity: 1, translateY: 0} : chapterReveal(seconds);
  return (
    <div
      style={{
        position: 'absolute',
        ...T.layout.chapter[position],
        opacity: reveal.opacity,
        transform: makeTransform([translateY(reveal.translateY)]),
        textShadow: '0 3px 22px #000',
        ...style,
      }}
    >
      <div style={{fontSize: 39, letterSpacing: 4, color: accent, marginBottom: 12}}>{year}</div>
      <h1 style={{
        fontSize: title.length > 9 ? 68 : T.type.hero,
        lineHeight: 1.12, fontWeight: 620, letterSpacing: 1, margin: '0 0 12px',
        color: textColor ?? T.colors.text,
      }}>{title}</h1>
      {alias && (
        <div style={{fontSize: T.type.alias, letterSpacing: 3, color: T.colors.muted, margin: '-8px 0 12px'}}>
          {alias}
        </div>
      )}
      <p style={{fontSize: T.type.caption, lineHeight: 1.45, fontWeight: 400, color: textColor ?? T.colors.body, margin: 0}}>
        {caption}
      </p>
    </div>
  );
}
