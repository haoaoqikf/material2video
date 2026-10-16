import {useSceneContext, type CodeSceneProps} from 'm2v/code-scene';

export const clamp = (x: number) => Math.max(0, Math.min(1, x));
export const smooth = (x: number) => {const t = clamp(x); return t * t * (3 - 2 * t);};

/** 只在 DOM 渲染器读取旁白时钟，再将数值显式传入 R3F。 */
export function useNarration(config: CodeSceneProps) {
  const context = useSceneContext();
  const windows = Object.values(config.segmentWindows);
  const seconds = context.elapsedSeconds;
  const index = Math.max(0, windows.reduce((last, w, i) => seconds >= w.startFrame / config.fps ? i : last, 0));
  const window = windows[index];
  if (!window) throw new Error('太阳系场景缺少旁白时间窗');
  return {...context, index};
}
