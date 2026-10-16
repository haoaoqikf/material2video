/**
 * 横屏舞台：这个作品自己的配色、栅格与旁白时钟。
 *
 * 视觉依据见 `DESIGN.md`：近黑蓝底 + 窄体字阶 + 金色主色 + 蓝色次要色。构图像一张
 * 桌面俯视图：候选方案铺在左，判断依据立在右。内容下边界取字幕安全区上沿再留 24px。
 */
import {useEffect, useRef, type ReactNode} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

export const COLOR = {
  bg: '#0d1015',
  panel: '#151b23',
  rule: '#26313d',
  ink: '#eef2f7',
  muted: '#93a1b1',
  accent: '#d9b26a',
  alt: '#6ea8fe',
};
export const SIZE = {title: 60, lead: 36, body: 27, note: 21};

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

export function Stage({props, title, note, children}: {
  props: CodeSceneProps;
  title: string;
  note?: string;
  children: ReactNode;
}) {
  const columns = Array.from({length: Math.floor(props.width / 160)}, (_, index) => (index + 1) * 160);
  return (
    <div style={{width: props.width, height: props.height, position: 'relative', overflow: 'hidden',
      background: COLOR.bg, color: COLOR.ink}}>
      <svg width={props.width} height={props.height} style={{position: 'absolute', inset: 0, opacity: 0.5}}
        aria-hidden>
        {columns.map(x => <line key={x} x1={x} x2={x} y1={0} y2={props.height} stroke={COLOR.rule} strokeWidth={1}/>)}
      </svg>
      <div style={{position: 'absolute', left: 110, top: 66, right: 110}}>
        <div style={{fontSize: SIZE.title, fontWeight: 300, letterSpacing: '0.02em', lineHeight: 1.2}}>{title}</div>
        {note && <div style={{fontSize: SIZE.note, color: COLOR.muted, marginTop: 12}}>{note}</div>}
      </div>
      <div style={{position: 'absolute', right: 110, top: 70, fontSize: SIZE.note, color: COLOR.muted}}>示意</div>
      {children}
    </div>
  );
}
