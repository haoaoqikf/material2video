/** 右上章节进度轨：只显示少量站点与当前进度，不逐站铺满。 */
import type {CSSProperties} from 'react';
import {T, clamp01} from './kit';

export type ChapterItem = {id: string; label: string};
export type ChapterTrackProps = {
  items: ChapterItem[];
  activeIndex: number;
  progress?: number;
  opacity?: number;
  style?: CSSProperties;
  role?: string;
};

export default function ChapterTrack({
  items, activeIndex, progress = 0, opacity = 1, style, role = 'chapter-track',
}: ChapterTrackProps) {
  const safeIndex = Math.max(0, Math.min(items.length - 1, activeIndex));
  return (
    <div
      data-m2v-role={role}
      style={{
        position: 'absolute',
        right: T.layout.chapterTrack.right,
        top: T.layout.chapterTrack.top,
        width: T.layout.chapterTrack.width,
        display: 'flex', justifyContent: 'flex-end', gap: 10,
        opacity, ...style,
      }}
    >
      {items.map((item, index) => {
        const active = index === safeIndex;
        const passed = index < safeIndex;
        return (
          <div key={item.id} style={{
            flex: '0 0 auto', textAlign: 'center',
            color: active ? T.colors.nav : T.colors.muted,
            opacity: active ? 1 : passed ? 0.55 : 0.28,
          }}>
            <div style={{
              width: active ? 28 : 16, height: 2,
              margin: '0 auto 8px',
              background: active ? T.colors.nav : T.colors.line,
              opacity: active ? 0.9 : 0.5,
            }}/>
            <div style={{fontSize: T.type.chapter, letterSpacing: 2, whiteSpace: 'nowrap'}}>{item.label}</div>
          </div>
        );
      })}
      <div style={{
        position: 'absolute', right: 0, bottom: -14, width: '100%', height: 2,
        background: `linear-gradient(90deg, transparent, ${T.colors.nav} ${clamp01(progress) * 100}%, transparent)`,
        opacity: 0.5,
      }}/>
    </div>
  );
}
