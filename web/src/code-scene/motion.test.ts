import { describe, expect, it } from 'vitest';
import { MOTION_CURVES, easeMotion, motionCurve, type MotionCurveName } from './motion';

const NAMES = Object.keys(MOTION_CURVES) as MotionCurveName[];

describe('共享命名缓动', () => {
  it('所有曲线端点精确落在 0 与 1', () => {
    for (const name of NAMES) {
      expect(MOTION_CURVES[name](0)).toBeCloseTo(0, 12);
      expect(MOTION_CURVES[name](1)).toBeCloseTo(1, 12);
    }
  });

  it('方向符合命名', () => {
    expect(MOTION_CURVES.easeInCubic(0.5)).toBeLessThan(0.5);
    expect(MOTION_CURVES.easeOutCubic(0.5)).toBeGreaterThan(0.5);
    expect(MOTION_CURVES.easeInOutCubic(0.5)).toBeCloseTo(0.5, 12);
    expect(MOTION_CURVES.easeInOutSine(0.5)).toBeCloseTo(0.5, 12);
  });

  it('回弹曲线在结束前可以超过 1，并最终收敛', () => {
    expect(MOTION_CURVES.backOut(0.8)).toBeGreaterThan(1);
    expect(MOTION_CURVES.backOut(1)).toBeCloseTo(1, 12);
  });

  it('同一输入重复求值一致，非有限输入按 0 处理', () => {
    for (const name of NAMES) {
      expect(MOTION_CURVES[name](0.37)).toBe(MOTION_CURVES[name](0.37));
      expect(MOTION_CURVES[name](Number.NaN)).toBe(0);
      expect(MOTION_CURVES[name](Infinity)).toBe(0);
    }
  });

  it('按名称取曲线，未命名时使用缓入缓出', () => {
    expect(motionCurve('easeOutCubic')(0.5)).toBe(MOTION_CURVES.easeOutCubic(0.5));
    expect(easeMotion(undefined, 0.5)).toBe(MOTION_CURVES.easeInOutCubic(0.5));
  });
});
