import type { SceneNode } from '@/schema/storyboard';
import type { StoryboardV4 } from '@/schema/storyboardV4';
import type { CompiledStateTrack } from './stateTracksV4';
import { stateAt } from './stateTracksV4';

export interface V4WorldTreeFrame {
  sceneTree: SceneNode;
  data: Record<string, unknown>;
  hiddenNodeIds: ReadonlySet<string>;
}

function setPath(root: Record<string, unknown>, path: string, value: unknown): void {
  const parts = path.split('.');
  let cursor: Record<string, unknown> = root;
  for (const part of parts.slice(0, -1)) {
    const child = cursor[part];
    if (!child || typeof child !== 'object' || Array.isArray(child)) throw new Error(`轨道数据路径不存在：${path}`);
    cursor = child as Record<string, unknown>;
  }
  const key = parts.at(-1)!;
  if (!(key in cursor)) throw new Error(`轨道数据路径不存在：${path}`);
  cursor[key] = structuredClone(value);
}

/** 将已编译的对象状态投影到全片树与副本数据；id/type/children 永不随帧变化。 */
export function worldTreeAtFrame(
  world: StoryboardV4['world'], tracks: readonly CompiledStateTrack[], frame: number,
): V4WorldTreeFrame {
  if (world.renderer.kind !== 'tree' || !world.sceneTree) throw new Error('worldTreeAtFrame 只接受带全局 sceneTree 的 tree world');
  const values = stateAt(tracks, frame);
  const data = structuredClone(world.data) as Record<string, unknown>;
  const hiddenNodeIds = new Set<string>();
  const copyNode = (node: SceneNode): SceneNode => {
    const copy = { ...node, ...(node.children ? { children: node.children.map(copyNode) } : {}) };
    const state = values[node.id];
    if (!state) return copy;
    for (const [property, value] of Object.entries(state)) {
      if (property === 'visible') {
        if (value === false) hiddenNodeIds.add(node.id);
      } else if (property === 'value') {
        if (!copy.contentRef) throw new Error(`节点 ${node.id} 的 value 轨道缺少 contentRef`);
        setPath(data, copy.contentRef, value);
      } else {
        (copy as unknown as Record<string, unknown>)[property] = structuredClone(value);
      }
    }
    return copy;
  };
  return { sceneTree: copyNode(world.sceneTree as unknown as SceneNode), data, hiddenNodeIds };
}
