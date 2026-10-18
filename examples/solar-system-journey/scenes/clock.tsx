import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

export const clamp = (x: number) => Math.max(0, Math.min(1, x));
export const smooth = (x: number) => {const t = clamp(x); return t * t * (3 - 2 * t);};

type Window = {startFrame: number; endFrame: number};

export type NarrationPosition = {
  /** 当前（或刚结束的）旁白段在 segmentWindows 中的序号。 */
  index: number;
  id: string;
  window: Window;
  /** 帧号是否落在发声窗口内；静默窗与开场返回 false。 */
  speaking: boolean;
};

/**
 * 单幕一镜到底的时间轴：旁白段之间可能隔着 holdFrames 静默。
 * 静默期间 `index` 保持在前一段，`speaking` 为 false，供面板与状态文案区分。
 */
export function narrationAt(config: CodeSceneProps, seconds: number): NarrationPosition {
  const entries = Object.entries(config.segmentWindows) as [string, Window][];
  if (!entries.length) throw new Error('太阳系场景缺少旁白时间窗');
  const frame = seconds * config.fps;
  let index = 0;
  for (let position = 0; position < entries.length; position += 1) {
    if (frame >= entries[position][1].startFrame) index = position;
  }
  const [id, window] = entries[index];
  return {index, id, window,
    speaking: frame >= window.startFrame && frame < window.endFrame};
}

/** 只在 DOM 渲染器读取旁白时钟，再将数值显式传入 R3F。 */
export function useNarration(config: CodeSceneProps) {
  const context = useSceneContext();
  return {...context, ...narrationAt(config, context.elapsedSeconds)};
}
