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
  return value;
}

describe('storyboard v4 world/stages contract', () => {
  it('accepts the shared valid vector', () => {
    expect(storyboardV4Schema.safeParse(vectors.valid).success).toBe(true);
  });

  it.each(vectors.invalid)('rejects $name', ({ mutation }) => {
    expect(storyboardV4Schema.safeParse(mutate(mutation)).success).toBe(false);
  });
});
