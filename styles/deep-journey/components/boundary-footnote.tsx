/** 边界脚注：小字、次要位置，说明示意、推测结构或事实边界。 */
import type {CSSProperties} from 'react';
import {T} from './kit';

export type BoundaryFootnoteProps = {
  text: string;
  opacity?: number;
  style?: CSSProperties;
  role?: string;
};

export default function BoundaryFootnote({text, opacity = 0.78, style, role = 'note'}: BoundaryFootnoteProps) {
  return (
    <div
      data-m2v-role={role}
      style={{
        position: 'absolute',
        left: T.layout.footnote.left,
        bottom: T.layout.footnote.bottom,
        maxWidth: T.layout.footnote.maxWidth,
        fontSize: T.type.footnote,
        lineHeight: 1.5,
        letterSpacing: 1,
        color: T.colors.footnote,
        opacity,
        ...style,
      }}
    >
      {text}
    </div>
  );
}
