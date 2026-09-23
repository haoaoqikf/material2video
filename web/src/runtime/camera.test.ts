import { describe, expect, it } from 'vitest';
import { cameraSegments, cameraState, cameraStyle } from './camera';
import { EMPTY_STORYBOARD } from '@/schema/storyboard';

describe('scene camera', () => {
  it('uses explicit camera segments bound to phase and settles at the scene tail', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.durationInFrames = 100;
    scene.camera = { shot: 'medium', composition: 'center', depth: 'layered', focus: 'text', segments: [
      { kind: 'hold', phase: 'establish', intensity: 0 },
      { kind: 'push-in', phase: 'change', intensity: 0.5 },
      { kind: 'settle', phase: 'settle', intensity: 0 },
    ] };
    expect(cameraSegments(scene).map((item) => item.kind)).toEqual(['hold', 'push-in', 'settle']);
    expect(cameraState(scene, 99).velocity).toBe(0);
    expect(cameraStyle(scene, 40)).toEqual(cameraStyle(scene, 40));
  });
});
