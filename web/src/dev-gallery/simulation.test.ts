import {describe, expect, it} from 'vitest';
import {createMonteCarlo} from './simulation';

describe('固定种子可回放模拟', () => {
  it('同种子复算点集和计数一致', () => {
    const first = createMonteCarlo(42, 1000), second = createMonteCarlo(42, 1000);
    expect(first.points).toEqual(second.points);
    expect(first.at(.63)).toEqual(second.at(.63));
  });
  it('乱序与重复读取不累积上一时刻状态', () => {
    const model = createMonteCarlo(9, 500);
    const later = model.at(.8), earlier = model.at(.2);
    expect(model.at(.8)).toEqual(later);
    expect(model.at(.2)).toEqual(earlier);
  });
  it('计数与估算曲线末点来自同一累计样本', () => {
    const model = createMonteCarlo(2026, 1200), state = model.at(.57), curve = model.curve(.57);
    expect(curve.at(-1)).toEqual({progress: state.n / model.points.length, value: state.estimate});
    expect(curve.length).toBeLessThanOrEqual(82);
  });
  it('限制非法种子、样本数和时间输入', () => {
    expect(() => createMonteCarlo(1, 0)).toThrow(/样本数/);
    expect(() => createMonteCarlo(1.5, 10)).toThrow(/整数/);
    const model = createMonteCarlo(1, 10);
    expect(() => model.at(Number.NaN)).toThrow(/有限数/);
  });
});
