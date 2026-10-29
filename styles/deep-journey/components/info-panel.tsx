/** 左侧信息面板：对象名称、一句印象与必要边界；不堆说明卡。 */
import type {CSSProperties, ReactNode} from 'react';
import {T} from './kit';

export type InfoPanelProps = {
  title: string;
  body: string;
  meta?: string;
  detail?: ReactNode;
  opacity?: number;
  style?: CSSProperties;
  role?: string;
};

export default function InfoPanel({
  title, body, meta, detail, opacity = 1, style, role = 'info-panel',
}: InfoPanelProps) {
  return (
    <div
      data-m2v-role={role}
      style={{
        position: 'absolute',
        left: T.layout.infoPanel.left,
        top: T.layout.infoPanel.top,
        width: T.layout.infoPanel.width,
        opacity, ...style,
      }}
    >
      <div style={{fontSize: T.type.panelTitle, letterSpacing: 2, color: T.colors.text}}>{title}</div>
      <div style={{fontSize: T.type.body, lineHeight: 1.42, color: T.colors.body, marginTop: 16}}>{body}</div>
      {meta && (
        <div style={{fontSize: T.type.panelBody, color: T.colors.muted, marginTop: 18}}>{meta}</div>
      )}
      {detail}
    </div>
  );
}
