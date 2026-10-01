import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { compileStateTracks } from './stateTracksV4';
import { resolveStoryboardV4 } from './timelineV4';
import { worldTreeAtFrame } from './worldTreeV4';
import type { StoryboardV4 } from '@/schema/storyboardV4';

const vector = JSON.parse(readFileSync(resolve(process.cwd(), '../tests/fixtures/storyboard-v4-timeline-vectors.json'), 'utf8')) as {
  storyboard: Record<string, unknown>; stateWorld: Record<string, unknown>;
};

describe('v4 全片唯一 sceneTree 状态投影', () => {
  it('跨阶段保留节点身份，逐帧更新标签、图表数值和可见性而不改源树', () => {
    const source = { ...structuredClone(vector.storyboard), world: structuredClone(vector.stateWorld) } as unknown as StoryboardV4;
    const world = source.world as unknown as Record<string, any>;
    world.data.labels = { current: '再次尝试', next: '快速反馈' };
    world.data.values.chart = [1, 3];
    world.sceneTree.children.push(
      { id: 'headline', type: 'text', contentRef: 'labels.current', role: 'headline' },
      { id: 'chart', type: 'chart', chart: 'bar', contentRef: 'values.chart' },
    );
    world.stateTracks.push(
      { id: 'headline-change', target: 'headline', property: 'contentRef', binding: { stageId: 'middle', phase: 'result' }, to: 'labels.next', interpolation: 'step-end' },
      { id: 'chart-growth', target: 'chart', property: 'value', binding: { stageId: 'middle', phase: 'result' }, to: [3, 9], interpolation: 'linear' },
      { id: 'dart-hide', target: 'dart', property: 'visible', binding: { stageId: 'middle', phase: 'change' }, to: false, interpolation: 'step-end' },
    );
    const timeline = resolveStoryboardV4(source);
    const tracks = compileStateTracks(source, timeline);
    const before = worldTreeAtFrame(source.world, tracks, 0);
    const after = worldTreeAtFrame(source.world, tracks, 192);
    const ids = (tree: { id: string; children?: any[] }): string[] => [tree.id, ...(tree.children ?? []).flatMap(ids)];
    expect(ids(after.sceneTree)).toEqual(ids(before.sceneTree));
    expect(ids(after.sceneTree)).toEqual(['root', 'player', 'dart', 'headline', 'chart']);
    expect(after.sceneTree.children?.find((node) => node.id === 'headline')?.contentRef).toBe('labels.next');
    expect(after.data.values).toMatchObject({ chart: [3, 9] });
    expect(after.hiddenNodeIds.has('dart')).toBe(true);
    expect(before.hiddenNodeIds.has('dart')).toBe(false);
    expect((source.world.sceneTree as any).children[1].id).toBe('dart');
    expect((source.world.data as any).values.chart).toEqual([1, 3]);
  });
});
