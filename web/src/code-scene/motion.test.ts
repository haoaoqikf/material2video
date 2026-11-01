import { describe, expect, it } from 'vitest';
import { MOTION_CURVES, easeMotion, motionCurve, oscillate, pingPong, waveMotion, type MotionCurveName } from './motion';

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

  it('往返波在 0/0.25/0.5/0.75/1 形成 0→1→0', () => {
    expect(pingPong(0)).toBe(0);
    expect(pingPong(0.25)).toBe(0.5);
    expect(pingPong(0.5)).toBe(1);
    expect(pingPong(0.75)).toBe(0.5);
    expect(pingPong(1)).toBe(0);
    expect(waveMotion('easeInOutSine', 0)).toBe(0);
    expect(waveMotion('easeInOutSine', 0.5)).toBe(1);
    expect(waveMotion('easeInOutSine', 1)).toBe(0);
    expect(oscillate('easeInOutSine', 0.5)).toBe(1);
    expect(oscillate('easeInOutSine', 0)).toBe(-1);
    expect(pingPong(Number.NaN)).toBe(0);
    expect(waveMotion('linear', Infinity)).toBe(0);
  });
});
