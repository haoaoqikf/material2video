import type { CSSProperties } from 'react';
import type { Scene, SceneNode, Storyboard } from '@/schema/storyboard';
import { stylePackDefinition } from '@/registry';

export type ContinuityKind = 'inherit' | 'transform' | 'decompose' | 'recompose' | 'dissolve' | 'break';

export interface SceneContinuity {
  kind: ContinuityKind;
  previousSceneId: string;
  sceneId: string;
  sourceIds: readonly string[];
  targetIds: readonly string[];
  meaning: string;
  span: number;
}

export interface ContinuityRenderState {
  relation: SceneContinuity;
  phase: 'source' | 'target';
  frame: number;
}

/** 只解析显式声明的相邻幕关系；不根据相似节点自动猜测连续性。 */
export function continuityFor(storyboard: Storyboard, index: number): SceneContinuity | null {
  if (index <= 0) return null;
  const scene: Scene | undefined = storyboard.scenes[index];
  const previous = storyboard.scenes[index - 1];
  const transition = scene?.transition;
  if (!scene || !previous || !transition) return null;
  const sourceIds = transition.sources ?? (transition.source ? [transition.source] : []);
  const targetIds = transition.targets ?? (transition.target ? [transition.target] : []);
  return {
    kind: transition.kind,
    previousSceneId: previous.id,
    sceneId: scene.id,
    sourceIds,
    targetIds,
    meaning: transition.meaning,
    span: Math.min(stylePackDefinition(storyboard.directingBrief?.stylePack).transitionSpan, Math.max(1, Math.floor(scene.durationInFrames / 5))),
  };
}

export function isContinuityActive(relation: SceneContinuity | null, frame: number): boolean {
  return Boolean(relation && relation.kind !== 'dissolve' && relation.sourceIds.length > 0 && frame < relation.span);
}

function progress(state: ContinuityRenderState): number {
  const linear = Math.min(1, Math.max(0, state.frame / state.relation.span));
  return 1 - (1 - linear) ** 3;
}

function selectedIds(state: ContinuityRenderState): readonly string[] {
  return state.phase === 'source' ? state.relation.sourceIds : state.relation.targetIds;
}

/** 返回映射节点及其祖先；源幕只渲染这棵最小布局骨架，避免整幕重叠。 */
export function continuityVisibleIds(tree: SceneNode | undefined, state?: ContinuityRenderState): ReadonlySet<string> | null {
  if (!tree || !state || state.phase === 'target') return null;
  const selected = new Set(selectedIds(state));
  const visible = new Set<string>();
  const walk = (node: SceneNode): boolean => {
    const keep = selected.has(node.id) || Boolean(node.children?.some(walk));
    if (keep) visible.add(node.id);
    return keep;
  };
  walk(tree);
  return visible;
}

/** 五类连续关系的受控逐帧样式；不使用 DOM 测量、时钟、随机数或 CSS transition。 */
export function continuityNodeStyle(nodeId: string, state?: ContinuityRenderState): CSSProperties {
  if (!state || !selectedIds(state).includes(nodeId)) return {};
  const p = progress(state);
  const entering = state.phase === 'target';
  const amount = entering ? p : 1 - p;
  const index = selectedIds(state).indexOf(nodeId);
  switch (state.relation.kind) {
    case 'inherit': return { opacity: amount };
    case 'transform': return { opacity: amount, transform: `scale(${entering ? 0.88 + p * 0.12 : 1 - p * 0.12})` };
    case 'decompose': {
      if (!entering) return { opacity: amount, transform: `scale(${1 - p * 0.35})` };
      const offset = (index - (state.relation.targetIds.length - 1) / 2) * 28;
      return { opacity: amount, transform: `translate(${(1 - p) * offset}px, ${(1 - p) * 24}px) scale(${0.72 + p * 0.28})` };
    }
    case 'recompose': {
      if (!entering) {
        const offset = (index - (state.relation.sourceIds.length - 1) / 2) * 28;
        return { opacity: amount, transform: `translate(${p * -offset}px, ${p * -20}px) scale(${1 - p * 0.28})` };
      }
      return { opacity: amount, transform: `scale(${0.72 + p * 0.28})` };
    }
    case 'break': return { opacity: amount, transform: `translateY(${-p * 36}px) rotate(${p * 4}deg)` };
    case 'dissolve': return {};
  }
}
