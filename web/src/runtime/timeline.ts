/**
 * 时间轴：把绝对帧号解析为「这是第几幕、幕内第几帧」。
 *
 * 这是渲染层最基础的一条推导，必须满足两条既有契约：
 *
 * 1. 幕的起点由前面所有幕的 `durationInFrames` **累加**得到，不手写——
 *    分镜里没有起始帧字段，因此不存在两处数据不一致；
 * 2. 纯函数：同一个帧号永远解析到同一幕、同一个幕内帧号，与调用顺序无关。
 *    渲染是随机访问帧（第 900 帧可能先于第 10 帧被渲染），因此这里不许有缓存状态。
 */
import type { Scene, Storyboard } from '@/schema/storyboard';

export interface SceneSpan {
  scene: Scene;
  /** 幕在 `scenes` 里的下标。 */
  index: number;
  /** 该幕的起始绝对帧号（含）。 */
  startFrame: number;
  /** 该幕的结束绝对帧号（不含）。 */
  endFrame: number;
  /** 幕内相对帧号，从 0 开始。 */
  localFrame: number;
}

/** 每一幕的起始绝对帧号；长度与 `scenes` 相同。 */
export function sceneStartFrames(storyboard: Storyboard): number[] {
  const starts: number[] = [];
  let cursor = 0;
  for (const scene of storyboard.scenes) {
    starts.push(cursor);
    cursor += scene.durationInFrames;
  }
  return starts;
}

/** 总帧数：所有幕的时长之和。契约里的 `durationInFrames` 就是这个值。 */
export function totalFrames(storyboard: Storyboard): number {
  return storyboard.scenes.reduce((sum, scene) => sum + scene.durationInFrames, 0);
}

/**
 * 解析某一帧属于哪一幕。
 *
 * `frame` 会被夹到 `[0, totalFrames - 1]`：渲染器只会请求合法帧号，
 * 但体检与抽帧工具可能越界，夹住比抛错更有用，也不会掩盖真实缺陷
 * （画面仍然由帧号唯一决定）。
 */
export function sceneAt(storyboard: Storyboard, frame: number): SceneSpan {
  const starts = sceneStartFrames(storyboard);
  const total = totalFrames(storyboard);
  const clamped = Math.min(Math.max(Math.floor(frame), 0), Math.max(total - 1, 0));

  let index = 0;
  for (let i = starts.length - 1; i >= 0; i -= 1) {
    if (clamped >= starts[i]!) {
      index = i;
      break;
    }
  }

  const scene = storyboard.scenes[index]!;
  const startFrame = starts[index]!;
  return {
    scene,
    index,
    startFrame,
    endFrame: startFrame + scene.durationInFrames,
    localFrame: clamped - startFrame,
  };
}
