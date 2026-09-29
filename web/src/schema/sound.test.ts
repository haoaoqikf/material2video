import { expect, it } from 'vitest';
import { narrationSegmentSchema, soundtrackSchema } from './storyboard';

it('speech 范围和未知字段', () => {
  const base = { id: 'n1', text: '说明。', beatId: 'b1' };
  expect(narrationSegmentSchema.safeParse({ ...base, speech: { rate: '-50%', pauseBeforeMs: 2000 } }).success).toBe(true);
  for (const speech of [{ rate: '+51%' }, { rate: '0%' }, { pauseAfterMs: true }, { pauseBeforeMs: 2001 }, { unknown: 0 }]) {
    expect(narrationSegmentSchema.safeParse({ ...base, speech }).success).toBe(false);
  }
});
it('只接受本地素材与受限混音参数', () => {
  expect(soundtrackSchema.safeParse({ music: { sourceRef: 'assets/bed.wav', loop: true }, effects: [] }).success).toBe(true);
  for (const sourceRef of ['../a.wav', 'https://x/a.wav', '/a.wav', 'a\\b.wav']) expect(soundtrackSchema.safeParse({ music: { sourceRef } }).success).toBe(false);
  expect(soundtrackSchema.safeParse({ music: { sourceRef: 'a.wav', gainDb: 1 } }).success).toBe(false);
});
