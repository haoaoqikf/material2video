import { describe, expect, it } from 'vitest';
import { EMPTY_STORYBOARD } from '@/schema/storyboard';
import { transitionStyle } from './transition';

describe('scene transition', () => {
  it('keeps scenes without a transition unchanged', () => {
    expect(transitionStyle(EMPTY_STORYBOARD.scenes[0], 3)).toEqual({});
  });
  it('uses a deterministic transform for transform transitions', () => {
    const scene = { ...EMPTY_STORYBOARD.scenes[0], durationInFrames: 100, transition: { kind: 'transform', meaning: '连续变化' } } as typeof EMPTY_STORYBOARD.scenes[0];
    expect(transitionStyle(scene, 7)).toEqual(transitionStyle(scene, 7));
    expect(transitionStyle(scene, 0).transform).toContain('scale(0.96)');
  });
});
