import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { cameraStateV4, compileCameraV4 } from './cameraV4';
import { resolveStoryboardV4 } from './timelineV4';
import { compileStateTracks } from './stateTracksV4';
import type { StoryboardV4 } from '@/schema/storyboardV4';

const vector = JSON.parse(readFileSync(resolve(process.cwd(), '../tests/fixtures/storyboard-v4-timeline-vectors.json'), 'utf8')) as {
  storyboard: Record<string, unknown>; stateWorld: Record<string, unknown>;
};

function cameraStoryboard(): StoryboardV4 {
  const world = structuredClone(vector.stateWorld) as Record<string, any>;
  world.sceneTree.children.push({ id: 'target', type: 'shape', shape: 'ring' });
  return {
    ...structuredClone(vector.storyboard), width: 1080, height: 1920,
    world: {
      ...world,
      objects: [
        { id: 'player', role: 'primary', description: '投掷者' },
        { id: 'dart', role: 'supporting', description: '飞镖' },
        { id: 'target', role: 'supporting', description: '靶' },
      ],
      camera: { shot: 'medium', composition: 'center', depth: 'layered', focus: 'player', segments: [
        { id: 'push', kind: 'push-in', binding: { beatId: 'beat-a' }, focus: 'player', intensity: .5 },
        { id: 'pan', kind: 'pan', binding: { stageId: 'middle', phase: 'change' }, focus: 'target', direction: 'right', intensity: .5 },
        { id: 'reframe-target', kind: 'reframe', binding: { stageId: 'ending', phase: 'establish' }, focus: 'target', intensity: .2 },
        { id: 'hold-final', kind: 'hold', binding: { stageId: 'ending', phase: 'settle' }, focus: 'target', intensity: 0 },
      ] },
    },
  } as unknown as StoryboardV4;
}

describe('v4 全局连续镜头轨迹', () => {
  it('跨阶段延续终态，绑定空档自动 hold，稳定窗内保持不漂移', () => {
    const storyboard = cameraStoryboard();
    const timeline = resolveStoryboardV4(storyboard);
    const camera = compileCameraV4(storyboard, timeline);
    expect(camera.segments.map(({ startFrame, endFrame }) => [startFrame, endFrame])).toEqual([[0, 40], [132, 169], [204, 236], [298, 310]]);
    expect(cameraStateV4(camera, 20)).toMatchObject({ scale: 1.0525, x: 0 });
    expect(cameraStateV4(camera, 50)).toMatchObject({ scale: 1.06, x: 0 });
    expect(cameraStateV4(camera, 101)).toMatchObject({ scale: 1.06, x: 0 });
    expect(cameraStateV4(camera, 180)).toMatchObject({ scale: 1.06, x: 28 });
    expect(cameraStateV4(camera, 220)).toMatchObject({ kind: 'reframe', focus: 'target' });
    expect(cameraStateV4(camera, 309)).toMatchObject({ scale: 1.06, x: 28 });
  });

  it('拒绝重叠镜头段、未知焦点与进入稳定窗的主要运动', () => {
    const overlap = cameraStoryboard();
    overlap.world.camera.segments.push({ ...overlap.world.camera.segments[0]!, id: 'overlap' });
    expect(() => compileCameraV4(overlap, resolveStoryboardV4(overlap))).toThrow(/重叠/);

    const invalidFocus = cameraStoryboard();
    invalidFocus.world.camera.segments[0]!.focus = 'missing';
    expect(() => compileCameraV4(invalidFocus, resolveStoryboardV4(invalidFocus))).toThrow(/未知焦点/);

    const drift = cameraStoryboard();
    drift.world.camera.segments[0]!.binding = { stageId: 'opening', phase: 'settle' };
    expect(() => compileCameraV4(drift, resolveStoryboardV4(drift))).toThrow(/稳定阅读窗/);
  });

  it('拒绝镜头绑定期间不可见的焦点对象', () => {
    const storyboard = cameraStoryboard();
    (storyboard.world.sceneTree!.children![0] as unknown as Record<string, unknown>).visible = false;
    const timeline = resolveStoryboardV4(storyboard);
    const stateTracks = compileStateTracks(storyboard, timeline);
    expect(() => compileCameraV4(storyboard, timeline, stateTracks)).toThrow(/基础状态中不可见/);

    const hiddenDuring = cameraStoryboard();
    hiddenDuring.world.stateTracks.push({ id: 'hide-player', target: 'player', property: 'visible',
      binding: { beatId: 'beat-a' }, to: false, interpolation: 'step-end' });
    hiddenDuring.world.camera.segments.splice(1, 0, { id: 'focus-hidden-player', kind: 'hold',
      binding: { beatId: 'beat-b' }, focus: 'player', intensity: 0 });
    const hiddenTimeline = resolveStoryboardV4(hiddenDuring);
    expect(() => compileCameraV4(hiddenDuring, hiddenTimeline, compileStateTracks(hiddenDuring, hiddenTimeline))).toThrow(/绑定期间不可见/);
  });

  it('reframe 消费布局预检提供的实测节点边界', () => {
    const storyboard = cameraStoryboard();
    const timeline = resolveStoryboardV4(storyboard);
    const geometry = new Map([['target', { x: .1, y: .2, width: .2, height: .1, radius: .1 }]]);
    const camera = compileCameraV4(storyboard, timeline, [], geometry);
    expect(camera.segments.find(({ id }) => id === 'reframe-target')?.to.x).toBeCloseTo(92.8);
  });
});
