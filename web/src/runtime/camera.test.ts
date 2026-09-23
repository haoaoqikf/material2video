import { describe, expect, it } from 'vitest';
import { cameraStyle } from './camera';
import { EMPTY_STORYBOARD } from '@/schema/storyboard';

describe('scene camera', () => {
  it('keeps legacy scenes unchanged', () => {
    expect(cameraStyle(EMPTY_STORYBOARD.scenes[0], 10)).toEqual({});
  });
  it('derives deterministic push-in transform from frame', () => {
    const scene = { ...EMPTY_STORYBOARD.scenes[0], durationInFrames: 100, camera: { shot: 'medium', composition: 'center', depth: 'layered', focus: 'text', movement: 'push-in' } } as typeof EMPTY_STORYBOARD.scenes[0];
    expect(cameraStyle(scene, 40)).toEqual(cameraStyle(scene, 40));
    expect(cameraStyle(scene, 0).transform).toContain('scale(1)');
  });
});
