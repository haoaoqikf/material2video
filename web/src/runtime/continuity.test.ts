import { describe, expect, it } from 'vitest';
import { EMPTY_STORYBOARD } from '@/schema/storyboard';
import { continuityFor, continuityNodeStyle, continuityVisibleIds, isContinuityActive, type SceneContinuity } from './continuity';

describe('scene continuity', () => {
  it('does not infer continuity for the first scene', () => {
    expect(continuityFor(EMPTY_STORYBOARD, 0)).toBeNull();
  });
  it('reads only the explicit adjacent transition', () => {
    const storyboard = structuredClone(EMPTY_STORYBOARD);
    storyboard.scenes.push({ ...structuredClone(EMPTY_STORYBOARD.scenes[0]), id: 'next', transition: { kind: 'transform', source: 'text', target: 'text', meaning: '文字变成路径' } });
    expect(continuityFor(storyboard, 1)).toMatchObject({ kind: 'transform', previousSceneId: 'placeholder', sourceIds: ['text'], targetIds: ['text'] });
    expect(continuityFor(storyboard, 1)!.sourceGeometry!.get('text')).toBeDefined();
  });
  it('builds explicit one-to-many and many-to-one mappings', () => {
    const storyboard = structuredClone(EMPTY_STORYBOARD);
    const next = { ...structuredClone(EMPTY_STORYBOARD.scenes[0]), id: 'next', transition: { kind: 'decompose' as const, source: 'text', targets: ['part-a', 'part-b'], meaning: '拆成两个部分' } };
    next.sceneTree!.children = [
      { id: 'part-a', type: 'shape', shape: 'circle' },
      { id: 'part-b', type: 'shape', shape: 'rect' },
    ];
    storyboard.scenes.push(next);
    expect(continuityFor(storyboard, 1)).toMatchObject({ sourceIds: ['text'], targetIds: ['part-a', 'part-b'] });
  });
  it('derives deterministic source and target styles from frame only', () => {
    const relation: SceneContinuity = { kind: 'recompose', previousSceneId: 'a', sceneId: 'b', sourceIds: ['a', 'b'], targetIds: ['c'], meaning: '聚合', span: 20 };
    const source = { relation, phase: 'source' as const, frame: 10 };
    const target = { relation, phase: 'target' as const, frame: 10 };
    expect(continuityNodeStyle('a', source)).toEqual(continuityNodeStyle('a', source));
    expect(continuityNodeStyle('a', source).opacity).toBeLessThan(1);
    expect(continuityNodeStyle('c', target).transform).toContain('scale(');
    expect(isContinuityActive(relation, 19)).toBe(true);
    expect(isContinuityActive(relation, 20)).toBe(false);
  });
  it('keeps only a mapped source and its layout ancestors', () => {
    const relation: SceneContinuity = { kind: 'break', previousSceneId: 'a', sceneId: 'b', sourceIds: ['keep'], targetIds: [], meaning: '断开', span: 12 };
    const visible = continuityVisibleIds({ id: 'root', type: 'stack', children: [{ id: 'keep', type: 'shape' }, { id: 'drop', type: 'shape' }] }, { relation, phase: 'source', frame: 0 });
    expect([...visible!].sort()).toEqual(['keep', 'root']);
  });
});
