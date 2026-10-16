/**
 * 竖屏舞台：这个作品自己的配色、卡片与旁白时钟。
 *
 * 视觉依据见 `DESIGN.md`：深棕黑底 + 靶金主色 + 陶土红警示色，竖屏分成「标题带 /
 * 演示区 / 结论带」三段。演示区下边界 = 字幕安全区上沿再留 24px——共享字幕层盖在
 * 安全区里，作品不能把要读的内容放进去。
 */
import {useEffect, useRef, type ReactNode} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

export const COLOR = {
  bg: '#16120e',
  card: '#221b15',
  rule: '#3b2f24',
  ink: '#f6efe4',
  muted: '#b9a58c',
  accent: '#e8a33d',
  danger: '#d9603c',
};
export const SIZE = {title: 66, lead: 44, body: 32, note: 26};
/** 竖屏常用内边距：与字幕安全区左右内缩一致，画面上下对齐。 */
export const INSET = 108;

export const contentBottom = (props: CodeSceneProps): number => props.subtitleSafeArea.y - 24;

/** 条件就绪后再调用 `ready()`；带素材的场景要等素材真的可用了才允许开录。 */
export function useReadyWhen(satisfied: boolean): void {
  const {ready} = useSceneContext();
  const announced = useRef(false);
  useEffect(() => {
    if (announced.current || !satisfied) return;
    announced.current = true;
    ready();
  }, [ready, satisfied]);
}
export const useReady = (): void => useReadyWhen(true);

/** 旁白时钟：把本幕的旁白时间窗换算成秒，画面按真实口播推进而不是靠猜。 */
export function useNarration(props: CodeSceneProps) {
  const {running, elapsedSeconds} = useSceneContext();
  const windowOf = (segmentId: string) => {
    const window = props.segmentWindows[segmentId];
    if (!window) throw new Error(`未知旁白时间窗：${segmentId}`);
    return {from: window.startFrame / props.fps, to: window.endFrame / props.fps};
  };
  return {
    elapsedSeconds,
    running,
    spoken: (segmentId: string, delaySeconds = 0) =>
      running && elapsedSeconds >= windowOf(segmentId).from + delaySeconds,
    progress: (segmentId: string) => {
      const {from, to} = windowOf(segmentId);
      return Math.max(0, Math.min(1, (elapsedSeconds - from) / Math.max(0.001, to - from)));
    },
  };
}

export const mix = (from: number, to: number, t: number): number => from + (to - from) * Math.max(0, Math.min(1, t));

export function Stage({props, title, lead, children}: {
  props: CodeSceneProps;
  title: string;
  lead?: string;
  children: ReactNode;
}) {
  return (
    <div style={{width: props.width, height: props.height, position: 'relative', overflow: 'hidden',
      background: COLOR.bg, color: COLOR.ink}}>
      <div style={{position: 'absolute', left: INSET, top: 132, right: INSET}}>
        <div style={{fontSize: SIZE.title, fontWeight: 700, lineHeight: 1.25}}>{title}</div>
        {lead && <div style={{fontSize: SIZE.lead, color: COLOR.muted, marginTop: 22}}>{lead}</div>}
      </div>
      <div style={{position: 'absolute', right: INSET, top: 140, fontSize: SIZE.note, color: COLOR.muted}}>
        示意
      </div>
      {children}
    </div>
  );
}

/** 演示区卡片：演示内容统一放在这一段里，不与标题带和结论带抢位置。 */
export function Panel({left, top, width, height, children}: {
  left: number; top: number; width: number; height: number; children: ReactNode;
}) {
  return (
    <div style={{position: 'absolute', left, top, width, height, borderRadius: 20, background: COLOR.card,
      border: `2px solid ${COLOR.rule}`, overflow: 'hidden'}}>{children}</div>
  );
}
