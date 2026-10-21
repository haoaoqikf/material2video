/**
 * 场景共用时钟：把本幕的旁白时间窗换算成秒，画面按真实口播推进。
 *
 * 所有运动都由录制帧与 `segmentWindows` 驱动，不使用挂钟、随机数或 CSS 动画，
 * 因此同一帧在任何一次录制里都一致。
 */
import { useEffect, useRef } from 'react';
import { useSceneContext, type CodeSceneProps } from 'm2v/code-scene';

export function useReady(): void {
  const { ready } = useSceneContext();
  const announced = useRef(false);
  useEffect(() => {
    if (announced.current) return;
    announced.current = true;
    ready();
  }, [ready]);
}

export function useNarration(props: CodeSceneProps) {
  const { running, elapsedSeconds } = useSceneContext();
  const windowOf = (segmentId: string) => {
    const window = props.segmentWindows[segmentId];
    if (!window) throw new Error(`未知旁白时间窗：${segmentId}`);
    return { from: window.startFrame / props.fps, to: window.endFrame / props.fps };
  };
  return {
    elapsedSeconds,
    running,
    spoken: (segmentId: string, delaySeconds = 0) =>
      running && elapsedSeconds >= windowOf(segmentId).from + delaySeconds,
    progress: (segmentId: string) => {
      const { from, to } = windowOf(segmentId);
      return Math.max(0, Math.min(1, (elapsedSeconds - from) / Math.max(0.001, to - from)));
    },
  };
}

export const mix = (from: number, to: number, t: number): number =>
  from + (to - from) * Math.max(0, Math.min(1, t));
