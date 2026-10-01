import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { compileStateTracks, stateAt } from './stateTracksV4';
import { resolveStoryboardV4 } from './timelineV4';
import type { StoryboardV4 } from '@/schema/storyboardV4';

const vector = JSON.parse(readFileSync(resolve(process.cwd(), '../tests/fixtures/storyboard-v4-timeline-vectors.json'), 'utf8')) as {
  storyboard: Record<string, unknown>; stateWorld: Record<string, unknown>; stateSamples: Record<string, unknown>;
};
const source = () => ({ ...structuredClone(vector.storyboard), world: structuredClone(vector.stateWorld) }) as StoryboardV4;

describe('v4 全局状态轨道', () => {
  it('离散末端提交、数值曲线、空隙保留并支持乱序寻帧', () => {
    const storyboard = source();
    const tracks = compileStateTracks(storyboard, resolveStoryboardV4(storyboard));
    for (const frame of [181, 0, 192, 20, 89, 40, 50]) expect(stateAt(tracks, frame)).toEqual(vector.stateSamples[String(frame)]);
    expect(storyboard.world.stateTracks[2]?.to).toEqual([10, 4]);
  });

  it('同一对象属性的重叠全局区间失败', () => {
    const storyboard = source();
    storyboard.world.stateTracks.push({ id: 'player-overlap', target: 'player', property: 'state',
      binding: { beatId: 'beat-a' }, to: 'muted', interpolation: 'step-end' });
    expect(() => compileStateTracks(storyboard, resolveStoryboardV4(storyboard))).toThrow(/player-focus/);
  });
});
