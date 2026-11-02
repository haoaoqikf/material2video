import {describe, expect, it} from 'vitest';
import {
  arcPath, noiseAt, noiseDrift, pathBox, pathMorphAt, pathWarped, pathNormalized,
  pathReversed, pathScaled, pathTranslated,
} from './index';

describe('path helpers', () => {
  it('morphs between two paths deterministically', () => {
    const from = 'M0 0 L100 0';
    const to = 'M0 0 L0 100';
    expect(pathMorphAt(0.5, from, to)).toEqual(pathMorphAt(0.5, from, to));
    expect(pathMorphAt(0, from, to)).not.toEqual(pathMorphAt(1, from, to));
    expect(pathMorphAt(0.2, '', to)).toEqual(to);
  });

  it('reports bounds and transforms paths without touching the source', () => {
    expect(pathBox('M0 0 L100 50')).toEqual({x: 0, y: 0, width: 100, height: 50});
    expect(pathWarped('M0 0 L10 0', point => ({x: point.x + 5, y: point.y}))).not.toEqual('M0 0 L10 0');
    expect(pathScaled('M0 0 L10 0', 2)).not.toEqual('M0 0 L10 0');
    expect(pathTranslated('M0 0 L10 0', 5, 0)).not.toEqual('M0 0 L10 0');
    expect(pathNormalized('M0 0 L10 0')).toContain('M');
    expect(pathReversed('M0 0 L10 0')).not.toEqual('M0 0 L10 0');
  });
});

describe('arc gauge geometry', () => {
  it('builds a 180 degree arc and a two-segment full circle', () => {
    expect(arcPath(100, 100, 50, 0, 180)).toContain('A 50 50');
    expect(arcPath(100, 100, 50, 0, 360).match(/A 50 50/g)).toHaveLength(2);
    expect(arcPath(100, 100, 50, 0, 0)).toBe('');
  });
});

describe('seeded noise', () => {
  it('returns the same drift for the same seed and progress', () => {
    const options = {seed: 'handheld', progress: 0.42, amount: 8, frequency: 2};
    expect(noiseDrift(options)).toEqual(noiseDrift(options));
    expect(noiseDrift({...options, progress: 0.9})).not.toEqual(noiseDrift(options));
  });

  it('keeps noise in the documented range', () => {
    for (const x of [0, 0.25, 0.5, 1, 10]) {
      expect(Math.abs(noiseAt('seed', x))).toBeLessThanOrEqual(1);
    }
  });
});
