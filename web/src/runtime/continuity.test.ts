import { describe, expect, it } from 'vitest';
import { EMPTY_STORYBOARD } from '@/schema/storyboard';
import { continuityFor } from './continuity';

describe('scene continuity', () => {
  it('does not infer continuity for the first scene', () => {
    expect(continuityFor(EMPTY_STORYBOARD, 0)).toBeNull();
  });
  it('reads only the explicit adjacent transition', () => {
    const storyboard = structuredClone(EMPTY_STORYBOARD);
    storyboard.scenes.push({ ...structuredClone(EMPTY_STORYBOARD.scenes[0]), id: 'next', transition: { kind: 'transform', source: 'text', target: 'text', meaning: '文字变成路径' } });
    expect(continuityFor(storyboard, 1)).toMatchObject({ kind: 'transform', previousSceneId: 'placeholder', source: 'text', target: 'text' });
  });
});
