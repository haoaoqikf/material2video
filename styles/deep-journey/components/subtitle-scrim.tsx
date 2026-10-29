/** 底部字幕 scrim：只提供对比，不替代共享字幕层，不遮挡主体关键动作。 */
import type {CSSProperties} from 'react';
import {T, alpha, clamp01} from './kit';

export type SubtitleScrimProps = {
  height?: number;
  opacity?: number;
  color?: string;
  style?: CSSProperties;
  role?: string;
};

export default function SubtitleScrim({
  height = T.layout.subtitleScrim.height, opacity = 1,
  color = T.canvas.background, style, role = 'scrim',
}: SubtitleScrimProps) {
  return (
    <div
      data-m2v-role={role}
      style={{
        position: 'absolute', left: 0, right: 0, bottom: 0, height,
        background: `linear-gradient(0deg, ${alpha(color, 0.92 * clamp01(opacity))}, transparent)`,
        pointerEvents: 'none', ...style,
      }}
    />
  );
}
