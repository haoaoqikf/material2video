import { describe, expect, it } from 'vitest';
import catalog from './catalog.json';
import { cssAnimationTime } from './FrameSyncedCssAnimation';

describe('CSS 动画帧同步', () => {
  it('同一帧重复求值完全一致，随机访问只依赖帧号', () => {
    expect(cssAnimationTime(75, 30)).toBe(cssAnimationTime(75, 30));
    expect(cssAnimationTime(75, 30)).toBe(2.5);
  });

  it('相邻帧连续推进而不是阶跃到最终态', () => {
    expect(cssAnimationTime(76, 30) - cssAnimationTime(75, 30)).toBeCloseTo(1 / 30);
  });

  it('分类表覆盖三类，并且只有一个正式代表组件', () => {
    expect(new Set(catalog.map((item) => item.classification))).toEqual(
      new Set(['static', 'css-keyframes', 'clock']),
    );
    expect(catalog.filter((item) => item.status === 'representative')).toHaveLength(1);
  });
});
