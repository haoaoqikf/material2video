import {describe, expect, it} from 'vitest';
import {keyframeAt} from './keyframes';

describe('数值关键帧轨道', () => {
  const keys = [{at: 0, value: 0}, {at: 2, value: 10}, {at: 5, value: 20}] as const;
  it('不等间距线性插值且端点外保持', () => {
    expect(keyframeAt(keys, -1)).toBe(0);
    expect(keyframeAt(keys, 1)).toBe(5);
    expect(keyframeAt(keys, 3.5)).toBe(15);
    expect(keyframeAt(keys, 8)).toBe(20);
  });
  it('保持模式直到下一关键帧', () => expect(keyframeAt(keys, 1.99, 'hold')).toBe(0));
  it('平滑模式穿过锚点且左右连续', () => {
    const smooth = (at: number) => keyframeAt(keys, at, 'smooth');
    expect(smooth(2)).toBe(10);
    expect(smooth(2 - 1e-6)).toBeCloseTo(smooth(2 + 1e-6), 4);
  });
  it('拒绝越序、重复时间及非有限值', () => {
    expect(() => keyframeAt([{at: 1, value: 0}, {at: 0, value: 1}], .5)).toThrow(/递增/);
    expect(() => keyframeAt([{at: 1, value: 0}, {at: 1, value: 1}], .5)).toThrow(/递增/);
    expect(() => keyframeAt([{at: 0, value: Number.NaN}], 0)).toThrow(/有限数/);
    expect(() => keyframeAt(keys, Number.POSITIVE_INFINITY)).toThrow(/有限数/);
    expect(() => keyframeAt(keys, -1, 'cubic' as never)).toThrow(/插值/);
  });
});
