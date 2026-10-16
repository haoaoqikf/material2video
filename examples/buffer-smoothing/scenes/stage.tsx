/**
 * 横屏舞台：这个作品自己的配色、栅格与旁白时钟。
 *
 * 视觉依据见 `DESIGN.md`：深海蓝底 + 细栅格 + 青蓝主色 + 琥珀警示色，构图像一张
 * 仪器读数台。文字与图形的下边界取字幕安全区上沿再留 24px 余量——共享字幕层会
 * 盖在安全区里，作品不能把要读的内容放进去。
 */
import {useEffect, useRef, type ReactNode} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

export const COLOR = {
  bg: '#0a1524',
  grid: '#152741',
  panel: '#10203a',
  rule: '#22405f',
  ink: '#eaf2fb',
  muted: '#8fa6c2',
  accent: '#4cc9f0',
  warn: '#f4a261',
};
export const SIZE = {title: 62, lead: 38, body: 28, note: 22};

/** 画面内容的下边界：字幕安全区上沿再留一点余量。 */
export const contentBottom = (props: CodeSceneProps): number => props.subtitleSafeArea.y - 24;

/** 挂载时调用一次 `ready()`：字体没就绪就录制，会录到回退字体的那一帧。 */
export function useReady(): void {
  const {ready} = useSceneContext();
  const announced = useRef(false);
  useEffect(() => {
    if (announced.current) return;
    announced.current = true;
    ready();
  }, [ready]);
}

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
    /** 该段旁白是否已经开口（可加一点延迟把入场错开）。 */
    spoken: (segmentId: string, delaySeconds = 0) =>
      running && elapsedSeconds >= windowOf(segmentId).from + delaySeconds,
    /** 该段旁白已经说了多少（0～1），用于把关键动画绑在真实口播上。 */
    progress: (segmentId: string) => {
      const {from, to} = windowOf(segmentId);
      return Math.max(0, Math.min(1, (elapsedSeconds - from) / Math.max(0.001, to - from)));
    },
  };
}

/** 线性插值：把「已经说了多少」换成画面上的连续量。 */
export const mix = (from: number, to: number, t: number): number => from + (to - from) * Math.max(0, Math.min(1, t));

export function Stage({props, title, note, children}: {
  props: CodeSceneProps;
  title: string;
  note?: string;
  children: ReactNode;
}) {
  return (
    <div style={{width: props.width, height: props.height, position: 'relative', overflow: 'hidden',
      background: COLOR.bg, color: COLOR.ink}}>
      <Grid width={props.width} height={props.height}/>
      <div style={{position: 'absolute', left: 96, top: 64, right: 96}}>
        <div style={{fontSize: SIZE.title, fontWeight: 700, lineHeight: 1.2}}>{title}</div>
        {note && <div style={{fontSize: SIZE.note, color: COLOR.muted, marginTop: 10}}>{note}</div>}
      </div>
      <div style={{position: 'absolute', right: 96, top: 68, fontSize: SIZE.note, color: COLOR.muted}}>示意数据</div>
      {children}
    </div>
  );
}

function Grid({width, height}: {width: number; height: number}) {
  const rows = Array.from({length: Math.floor(height / 90)}, (_, index) => (index + 1) * 90);
  const columns = Array.from({length: Math.floor(width / 120)}, (_, index) => (index + 1) * 120);
  return (
    <svg width={width} height={height} style={{position: 'absolute', inset: 0}} aria-hidden>
      {rows.map(y => <line key={`r${y}`} x1={0} x2={width} y1={y} y2={y} stroke={COLOR.grid} strokeWidth={1}/>)}
      {columns.map(x => <line key={`c${x}`} x1={x} x2={x} y1={0} y2={height} stroke={COLOR.grid} strokeWidth={1}/>)}
    </svg>
  );
}
