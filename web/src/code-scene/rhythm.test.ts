import {describe, expect, it} from 'vitest';
import {beatPhase, beatPulse} from './rhythm';

describe('共享节拍原语', () => {
  it('相位随全片进度循环，重复求值一致', () => {
    expect(beatPhase(0, 60, 120)).toBeCloseTo(0);
    expect(beatPhase(1 / 240, 60, 120)).toBeCloseTo(0.5);
    expect(beatPhase(1 / 120, 60, 120)).toBeCloseTo(0);
    expect(beatPhase(0.5, 60, 120)).toBeCloseTo(beatPhase(0.5, 60, 120));
  });

  it('脉冲在拍点为一，并在衰减窗口后归零', () => {
    expect(beatPulse(0, 60, 120, 0.2)).toBeCloseTo(1);
    expect(beatPulse(0.05 / 60, 60, 120, 0.2)).toBeGreaterThan(0);
    expect(beatPulse(0.2 / 60 * 0.5, 60, 120, 0.2)).toBe(0);
    expect(beatPulse(1 / 120, 60, 120, 0.2)).toBeCloseTo(1);
  });

  it('相位偏移改变重音位置，不改变周期', () => {
    expect(beatPhase(0, 60, 120, 0.25)).toBeCloseTo(0.25);
    expect(beatPhase(0, 60, 120, 1.25)).toBeCloseTo(0.25);
  });

  it('非法参数明确失败', () => {
    expect(() => beatPhase(0.2, 0, 112)).toThrow(RangeError);
    expect(() => beatPulse(0.2, 60, 112, 0)).toThrow(RangeError);
  });
});
