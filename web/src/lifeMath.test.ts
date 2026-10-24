import {describe, expect, it} from 'vitest';
import {ACTS, DURATION, actAt, smooth01} from '../../examples/five-life-choices/scenes/lifeMath';

describe('five-life-choices 30-second paper-cut timeline', () => {
  it('tiles 900 frames into seven consecutive chapters', () => {
    expect(DURATION).toBe(30);
    expect(ACTS[0].start).toBe(0);
    expect(ACTS.at(-1)?.end).toBe(30);
    for (let i = 0; i < ACTS.length - 1; i += 1) {
      expect(ACTS[i].end).toBe(ACTS[i + 1].start);
    }
    expect(actAt(0)).toBe('opening');
    expect(actAt(8)).toBe('industry');
    expect(actAt(30)).toBe('finale');
  });

  it('uses deterministic eased progress bounded to the interval', () => {
    expect(smooth01(-1)).toBe(0);
    expect(smooth01(0)).toBe(0);
    expect(smooth01(.5)).toBeCloseTo(.5, 6);
    expect(smooth01(1)).toBe(1);
    expect(smooth01(2)).toBe(1);
  });
});
