import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it, vi } from 'vitest';
import { createContract, type M2VContractV4 } from './bridge';
import type { StoryboardV4 } from '@/schema/storyboardV4';

const vectors = JSON.parse(readFileSync(resolve(process.cwd(), '../tests/fixtures/storyboard-v4-vectors.json'), 'utf8')) as { valid: StoryboardV4 };

describe('v4 window.__M2V__ 探针', () => {
  it('暴露同帧 world、stage、object state、camera 与 beat 状态', () => {
    const dataset = {
      m2vWorldId: 'dart-world', m2vWorldRenderer: 'tree',
      m2vWorldObjects: JSON.stringify([{ id: 'player' }, { id: 'target' }]),
      m2vWorldObjectStates: JSON.stringify({ player: { state: 'focus' } }),
      m2vStageId: 'opening', m2vStageStart: '0', m2vStageEnd: '1050',
      m2vCameraKind: 'push-in', m2vCameraFocus: 'target', m2vCameraX: '3', m2vCameraY: '4',
      m2vCameraScale: '1.2', m2vCameraVelocity: '0.01',
      m2vBeatCurrent: 'throw-1', m2vBeatCompleted: '', m2vBeatPlan: 'throw-1', m2vBeatEstimated: '1',
    };
    vi.stubGlobal('document', { querySelector: () => ({ dataset }) });
    const player = { getCurrentFrame: () => 20 } as any;
    const contract = createContract({ player, storyboard: vectors.valid }) as M2VContractV4;
    expect(contract.version).toBe(4);
    expect(contract.world()).toEqual({ id: 'dart-world', renderer: 'tree', objectIds: ['player', 'target'] });
    expect(contract.stage()).toEqual({ id: 'opening', startFrame: 0, endFrame: 1050 });
    expect(contract.objectStates()).toEqual({ player: { state: 'focus' } });
    expect(contract.camera()).toEqual({ kind: 'push-in', focus: 'target', x: 3, y: 4, scale: 1.2, velocity: .01 });
    expect(contract.beats()).toEqual({ current: 'throw-1', completed: [], plan: ['throw-1'], estimated: true });
    vi.unstubAllGlobals();
  });

  it('关键 v4 探针缺失时明确失败', () => {
    vi.stubGlobal('document', { querySelector: () => null });
    const contract = createContract({ player: { getCurrentFrame: () => 0 } as any, storyboard: vectors.valid }) as M2VContractV4;
    expect(() => contract.world()).toThrow(/world 探针未挂载/);
    expect(() => contract.camera()).toThrow(/camera 探针缺失/);
    vi.unstubAllGlobals();
  });

  it('契约时长采用媒体派生的全局 stage 轴', () => {
    const stage = vectors.valid.stages[0]!;
    const player = { getCurrentFrame: () => 0 } as any;
    const contract = createContract({ player, storyboard: {
      ...vectors.valid,
      mediaTimeline: {
        stages: [{ id: stage.id, durationInFrames: stage.durationInFrames + 15, audio: 'opening.wav' }],
        resolvedBeats: [{ id: 'throw-1', stageId: stage.id, action: stage.beats![0]!.action,
          targets: stage.beats![0]!.targets, meaning: stage.beats![0]!.meaning,
          startFrame: 0, endFrame: stage.durationInFrames - 12 }],
      },
    } }) as M2VContractV4;
    expect(contract.durationInFrames).toBe(stage.durationInFrames + 15);
  });
});
