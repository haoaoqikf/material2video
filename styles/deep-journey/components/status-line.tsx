/** 左上状态行：当前站点、方向或观察状态；只承担导航，不承担结论。 */
import type {CSSProperties} from 'react';
import {T} from './kit';

export type StatusLineProps = {
  text: string;
  subtext?: string;
  opacity?: number;
  style?: CSSProperties;
  role?: string;
};

export default function StatusLine({text, subtext, opacity = 1, style, role = 'status'}: StatusLineProps) {
  return (
    <div
      data-m2v-role={role}
      style={{
        position: 'absolute',
        left: T.layout.status.left,
        top: T.layout.status.top,
        opacity, ...style,
      }}
    >
      <div style={{fontSize: T.type.status, letterSpacing: 4, color: T.colors.nav}}>{text}</div>
      {subtext && (
        <div style={{fontSize: T.type.panelBody, letterSpacing: 2, color: T.colors.muted, marginTop: 10}}>
          {subtext}
        </div>
      )}
    </div>
  );
}
