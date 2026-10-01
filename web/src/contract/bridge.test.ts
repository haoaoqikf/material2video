import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it, vi } from 'vitest';
import { createContract, type A2VContractV4 } from './bridge';
import type { StoryboardV4 } from '@/schema/storyboardV4';

const vectors = JSON.parse(readFileSync(resolve(process.cwd(), '../tests/fixtures/storyboard-v4-vectors.json'), 'utf8')) as { valid: StoryboardV4 };

describe('v4 window.__A2V__ 探针', () => {
  it('暴露同帧 world、stage、object state、camera 与 beat 状态', () => {
    const dataset = {
      a2vWorldId: 'dart-world', a2vWorldRenderer: 'tree',
      a2vWorldObjects: JSON.stringify([{ id: 'player' }, { id: 'target' }]),
      a2vWorldObjectStates: JSON.stringify({ player: { state: 'focus' } }),
      a2vStageId: 'opening', a2vStageStart: '0', a2vStageEnd: '1050',
      a2vCameraKind: 'push-in', a2vCameraFocus: 'target', a2vCameraX: '3', a2vCameraY: '4',
      a2vCameraScale: '1.2', a2vCameraVelocity: '0.01',
      a2vBeatCurrent: 'throw-1', a2vBeatCompleted: '', a2vBeatPlan: 'throw-1', a2vBeatEstimated: '1',
    };
    vi.stubGlobal('document', { querySelector: () => ({ dataset }) });
    const player = { getCurrentFrame: () => 20 } as any;
    const contract = createContract({ player, storyboard: vectors.valid }) as A2VContractV4;
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
    const contract = createContract({ player: { getCurrentFrame: () => 0 } as any, storyboard: vectors.valid }) as A2VContractV4;
    expect(() => contract.world()).toThrow(/world 探针未挂载/);
    expect(() => contract.camera()).toThrow(/camera 探针缺失/);
    vi.unstubAllGlobals();
  });
});
