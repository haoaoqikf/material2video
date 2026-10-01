import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { storyboardV4Schema } from './storyboardV4';

const vectors = JSON.parse(readFileSync(resolve(process.cwd(), '../tests/fixtures/storyboard-v4-vectors.json'), 'utf8')) as {
  valid: Record<string, unknown>;
  invalid: Array<{ name: string; mutation: string }>;
};

function mutate(name: string): Record<string, unknown> {
  const value = structuredClone(vectors.valid) as any;
  if (name === 'version-v3') Object.assign(value, { version: 3, schemaVersion: 3 });
  else if (name === 'duplicate-stage') value.stages.push(structuredClone(value.stages[0]));
  else if (name === 'unknown-root') value.legacyField = true;
  else if (name === 'stage-renderer') value.stages[0].renderer = { kind: 'tree' };
  else if (name === 'stage-transition') value.stages[0].transition = { kind: 'inherit' };
  else if (name === 'duplicate-beat') value.stages[0].beats.push(structuredClone(value.stages[0].beats[0]));
  else if (name === 'missing-track-baseline') value.world.stateTracks = [{ id: 'track-a', target: 'player', property: 'state', binding: { beatId: 'throw-1' }, to: 'focus', interpolation: 'step-end' }];
  else if (name === 'track-target-type') value.world.stateTracks = [{ id: 'track-a', target: 'dart', property: 'value', binding: { beatId: 'throw-1' }, to: 1, interpolation: 'linear' }];
  else if (name === 'invalid-track-beat') value.world.stateTracks = [{ id: 'track-a', target: 'player', property: 'state', binding: { beatId: 'absent' }, to: 'focus', interpolation: 'step-end' }];
  else if (name === 'overlapping-track' || name === 'illegal-interpolation') {
    value.world.sceneTree.children[0].state = 'rest';
    const track = { id: 'track-a', target: 'player', property: 'state', binding: { beatId: 'throw-1' }, to: 'focus', interpolation: 'step-end' };
    value.world.stateTracks = name === 'overlapping-track' ? [track, { ...track, id: 'track-b', to: 'done' }] : [{ ...track, interpolation: 'linear' }];
  }
  else if (name === 'length-171') { value.stages[0].durationInFrames = 1200; value.stages[0].narrationSegments[0].text = '甲'.repeat(171); }
  else if (name === 'duration-short') value.stages[0].durationInFrames = 34 * value.fps;
  else if (name === 'duration-long') value.stages[0].durationInFrames = 46 * value.fps;
  else if (name === 'silent-only') { delete value.stages[0].narrationSegments; delete value.stages[0].beats; }
  return value;
}

describe('storyboard v4 world/stages contract', () => {
  it('accepts the shared valid vector', () => {
    const parsed = storyboardV4Schema.safeParse(vectors.valid);
    expect(parsed.success, parsed.success ? '' : JSON.stringify(parsed.error.issues)).toBe(true);
  });

  it('accepts both declared duration boundaries', () => {
    for (const seconds of [35, 45]) {
      const value = structuredClone(vectors.valid) as any;
      value.stages[0].durationInFrames = seconds * value.fps;
      expect(storyboardV4Schema.safeParse(value).success).toBe(true);
    }
  });

  it.each(vectors.invalid)('rejects $name', ({ mutation }) => {
    expect(storyboardV4Schema.safeParse(mutate(mutation)).success).toBe(false);
  });
});
