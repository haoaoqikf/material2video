import {describe, expect, it} from 'vitest';
import {
  ACTS, DURATION, actAt, actProgress, cameraAt, finaleAt, pathUAt, unlockAt,
} from '../../examples/five-life-choices/scenes/lifeMath';

describe('five-life-choices continuous life world', () => {
  it('tiles the complete 65-second film with seven continuous chapters', () => {
    expect(DURATION).toBe(65);
    expect(ACTS[0].start).toBe(0);
    expect(ACTS.at(-1)?.end).toBe(65);
    for (let i = 0; i < ACTS.length - 1; i += 1) {
      expect(ACTS[i].end).toBe(ACTS[i + 1].start);
    }
    expect(actAt(0)).toBe('opening');
    expect(actAt(16)).toBe('industry');
    expect(actAt(65)).toBe('finale');
    expect(actProgress(11, 'city')).toBeCloseTo(0.5, 6);
  });

  it('moves the figure forward without resetting between chapters', () => {
    const samples = Array.from({length: 651}, (_, i) => pathUAt(i / 10));
    expect(samples[0]).toBe(0);
    expect(samples.at(-1)).toBe(1);
    for (let i = 1; i < samples.length; i += 1) {
      expect(samples[i]).toBeGreaterThanOrEqual(samples[i - 1]);
    }
    expect(pathUAt(6)).toBeCloseTo(0.09, 6);
    expect(pathUAt(27)).toBeCloseTo(0.44, 6);
  });

  it('keeps one continuous camera path and ends on a full-world pullback', () => {
    const start = cameraAt(0);
    const finale = cameraAt(65);
    expect(start.pos[1]).toBeLessThan(10);
    expect(finale.pos[1]).toBeGreaterThan(150);
    expect(cameraAt(0)).toEqual(cameraAt(0));
    for (let t = 0; t < 65; t += 0.1) {
      const a = cameraAt(t);
      const b = cameraAt(t + 0.1);
      const moved = Math.hypot(b.pos[0] - a.pos[0], b.pos[1] - a.pos[1], b.pos[2] - a.pos[2]);
      expect(moved).toBeLessThan(12);
    }
  });

  it('locks learning unlocks and the finale reveal to declared windows', () => {
    expect(unlockAt(48, 0)).toBe(0);
    expect(unlockAt(50.5, 0)).toBeGreaterThan(0.9);
    expect(unlockAt(56.4, 3)).toBeGreaterThan(0.9);
    expect(finaleAt(57)).toBe(0);
    expect(finaleAt(63)).toBe(1);
  });
});
