/** 片尾署名块：集中、简短、只出现一次；完整来源与许可留在作品材料中。 */
import type {CSSProperties} from 'react';
import {T} from './kit';

export type CreditBlockProps = {
  lines: string[];
  style?: CSSProperties;
  role?: string;
};

export default function CreditBlock({lines, style}: CreditBlockProps) {
  return (
    <div
      style={{
        position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
        justifyContent: 'center', padding: `0 ${T.layout.creditPaddingX}px`,
        background: `radial-gradient(ellipse at 75% 30%, ${T.canvas.backgroundAlt} 0%, ${T.canvas.background} 62%)`,
        ...style,
      }}
    >
      <div style={{width: '100%', textAlign: 'center', textShadow: '0 2px 16px #000'}}>
        {lines.map((line, index) => (
          <div key={index} style={{
            fontSize: T.type.caption, lineHeight: 1.55, fontWeight: 500,
            color: index % 2 ? T.colors.credit : T.colors.body,
          }}>{line}</div>
        ))}
      </div>
    </div>
  );
}
