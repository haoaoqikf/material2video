import {describe, expect, it} from 'vitest';
import {arcPath} from './gauge';

describe('arc gauge geometry', () => {
  it('builds a 180 degree arc and a two-segment full circle', () => {
    expect(arcPath(100, 100, 50, 0, 180)).toContain('A 50 50');
    expect(arcPath(100, 100, 50, 0, 360).match(/A 50 50/g)).toHaveLength(2);
    expect(arcPath(100, 100, 50, 0, 0)).toBe('');
  });
});
