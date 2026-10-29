/** 示意标注：小字、次要位置，标出代码解释与真实档案的边界。 */
import type {CSSProperties} from 'react';
import {T} from './kit';

export type SchematicBadgeProps = {
  text?: string;
  style?: CSSProperties;
  role?: string;
};

export default function SchematicBadge({
  text = '示意', style, role = 'note',
}: SchematicBadgeProps) {
  return (
    <div
      data-m2v-role={role}
      style={{
        position: 'absolute',
        fontSize: T.type.small,
        letterSpacing: 2,
        color: T.colors.muted,
        opacity: 0.72,
        ...style,
      }}
    >
      {text}
    </div>
  );
}
