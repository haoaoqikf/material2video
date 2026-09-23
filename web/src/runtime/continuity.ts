import type { Scene, Storyboard } from '@/schema/storyboard';

export interface SceneContinuity {
  kind: 'inherit' | 'transform' | 'dissolve' | 'break';
  previousSceneId?: string;
  source?: string;
  target?: string;
  meaning?: string;
}

/** 只解析显式声明的相邻幕关系；不根据相似节点自动猜测连续性。 */
export function continuityFor(storyboard: Storyboard, index: number): SceneContinuity | null {
  if (index <= 0) return null;
  const scene: Scene | undefined = storyboard.scenes[index];
  const previous = storyboard.scenes[index - 1];
  const transition = scene?.transition;
  if (!scene || !previous || !transition) return null;
  return { ...transition, previousSceneId: previous.id };
}
