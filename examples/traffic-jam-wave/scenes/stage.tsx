/**
 * 竖屏实验台：浅色桌面、深色车辆、红色制动灯与蓝色传播标记。
 *
 * 视觉依据见 `DESIGN.md`。画面分「标题带 / 演示区 / 结论带」三段：演示区下边界等于
 * 共享字幕安全区上沿再留 24px，作品不把要读的内容放进字幕层。
 */
import {useEffect, useRef, type ReactNode} from 'react';
import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

export const COLOR = {
  bg: '#f2efe8',
  paper: '#fbf9f4',
  road: '#d9d3c5',
  roadLine: '#f7f4ec',
  edge: '#b8b0a0',
  ink: '#20252b',
  muted: '#6d675c',
  car: '#2f3a45',
  carLight: '#46525f',
  glass: '#8fa3b4',
  brake: '#e4572e',
  accent: '#2f6db3',
  accentSoft: '#cfe0f2',
  dangerSoft: '#f6d9cf',
  rule: '#ddd5c6',
};
export const SIZE = {title: 58, lead: 34, body: 28, note: 22, number: 14};
export const INSET = 96;

export const contentBottom = (props: CodeSceneProps): number => props.subtitleSafeArea.y - 24;

/** 条件就绪后再调用 `ready()`。 */
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

/** 旁白时钟：把本幕的旁白时间窗换算成秒，画面按真实口播推进。 */
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

export const mix = (from: number, to: number, t: number): number =>
  from + (to - from) * Math.max(0, Math.min(1, t));

export function Stage({props, title, lead, badge = '示意', children}: {
  props: CodeSceneProps;
  title: string;
  lead?: string;
  badge?: string;
  children: ReactNode;
}) {
  return (
    <div style={{width: props.width, height: props.height, position: 'relative', overflow: 'hidden',
      background: COLOR.bg, color: COLOR.ink}}>
      {/* 桌面上极淡的网格，帮助读数但不抢主体。 */}
      <div style={{position: 'absolute', inset: 0, backgroundImage:
        `linear-gradient(${COLOR.rule} 1px, transparent 1px), linear-gradient(90deg, ${COLOR.rule} 1px, transparent 1px)`,
        backgroundSize: '96px 96px', opacity: 0.18}}/>
      <div style={{position: 'absolute', left: INSET, top: 92, right: INSET + 104}}>
        <div style={{fontSize: SIZE.title, fontWeight: 700, lineHeight: 1.22, letterSpacing: 1}}>{title}</div>
        {lead && <div style={{fontSize: SIZE.lead, color: COLOR.muted, marginTop: 18, lineHeight: 1.4}}>{lead}</div>}
      </div>
      <div style={{position: 'absolute', right: INSET, top: 98, fontSize: SIZE.note, color: COLOR.muted,
        border: `2px solid ${COLOR.rule}`, borderRadius: 999, padding: '6px 16px', background: COLOR.paper}}>
        {badge}
      </div>
      {children}
    </div>
  );
}

export function Panel({left, top, width, height, children, tone = COLOR.paper}: {
  left: number; top: number; width: number; height: number; children: ReactNode; tone?: string;
}) {
  return (
    <div style={{position: 'absolute', left, top, width, height, borderRadius: 18, background: tone,
      border: `2px solid ${COLOR.rule}`, overflow: 'hidden'}}>{children}</div>
  );
}

/** 结论带：一句话主结论 + 一行限定说明。 */
export function Conclusion({props, headline, note}: {props: CodeSceneProps; headline: string; note: string}) {
  return (
    <>
      <div style={{position: 'absolute', left: INSET, top: contentBottom(props) - 128, right: INSET,
        fontSize: 36, fontWeight: 700, lineHeight: 1.35}}>{headline}</div>
      <div style={{position: 'absolute', left: INSET, top: contentBottom(props) - 62, right: INSET,
        fontSize: SIZE.note, lineHeight: 1.5, color: COLOR.muted}}>{note}</div>
    </>
  );
}
