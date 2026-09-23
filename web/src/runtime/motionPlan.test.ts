import { describe, expect, it } from 'vitest';
import { EMPTY_STORYBOARD } from '@/schema/storyboard';
import { EMPTY_BEAT_TIMELINE } from './beats';
import { sceneMotionPlan, staggerOrder, visualMix } from './motionPlan';

describe('cinematic motion plan', () => {
  it('keeps a stable reading tail for legacy motions', () => { const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]); scene.durationInFrames = 60; scene.motions = [{ target: 'text', recipe: 'rise', startFrame: 0 }]; const plan = sceneMotionPlan(scene, EMPTY_BEAT_TIMELINE); expect(plan.settleStart).toBe(48); expect(plan.motions[0]!.endFrame).toBeLessThanOrEqual(48); });
  it('orders every stagger strategy deterministically', () => { expect(staggerOrder(['a','b','c'], 'forward')).toEqual(['a','b','c']); expect(staggerOrder(['a','b','c'], 'reverse')).toEqual(['c','b','a']); expect(staggerOrder(['a','b','c'], 'center')).toEqual(['b','a','c']); expect(staggerOrder(['a','b','c'], 'path', ['c','a','b'])).toEqual(['c','a','b']); });
  it('makes visual state interpolation repeatable', () => expect(visualMix('focus', .5)).toEqual(visualMix('focus', .5)));
});
