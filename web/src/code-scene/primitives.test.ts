import { describe, expect, it } from 'vitest';
import {
  clampProgress, growSeries, interpolateState, particleField, rollNumber, scrollList,
} from './primitives';

const linear = (t: number) => t;
const square = (t: number) => t * t;

describe('共享动效原语', () => {
  it('进度限制在 0–1，非有限值按 0 处理', () => {
    expect(clampProgress(-1)).toBe(0);
    expect(clampProgress(0.4)).toBe(0.4);
    expect(clampProgress(2)).toBe(1);
    expect(clampProgress(Number.NaN)).toBe(0);
  });

  describe('数字滚动', () => {
    it('0 与 1 精确落在端点，缓动由调用方传入', () => {
      expect(rollNumber({ from: 10, to: 95, progress: 0, easing: linear }).value).toBe(10);
      expect(rollNumber({ from: 10, to: 95, progress: 1, easing: linear }).value).toBe(95);
      expect(rollNumber({ from: 0, to: 100, progress: 0.5, easing: square }).value).toBe(25);
      expect(rollNumber({ from: 10, to: 95, progress: 1.5, easing: linear }).value).toBe(95);
      expect(rollNumber({ from: 10, to: 95, progress: -1, easing: linear }).value).toBe(10);
    });

    it('文本由小数位与可选的千位分隔决定，不依赖运行环境', () => {
      expect(rollNumber({ from: 0, to: 1234.5, progress: 1, decimals: 1, easing: linear }).text).toBe('1234.5');
      expect(rollNumber({ from: 0, to: 1234.5, progress: 1, decimals: 1, group: true, easing: linear }).text).toBe('1,234.5');
      expect(rollNumber({ from: -1234567, to: -1234567, progress: 0, group: true, easing: linear }).text).toBe('-1,234,567');
    });

    it('同一进度与参数重复求值一致', () => {
      const once = rollNumber({ from: 3, to: 17, progress: 0.37, decimals: 2, easing: square });
      const twice = rollNumber({ from: 3, to: 17, progress: 0.37, decimals: 2, easing: square });
      expect(twice).toEqual(once);
    });

    it('未传入缓动时明确失败', () => {
      expect(() => rollNumber({ from: 0, to: 1, progress: 0.5 } as never)).toThrow('easing');
    });
  });

  describe('数据曲线与柱状生长', () => {
    it('同步生长时所有点使用同一比例，端点精确', () => {
      const start = growSeries({ values: [10, 20, 30], progress: 0, easing: linear });
      expect(start.ratios).toEqual([0, 0, 0]);
      expect(start.values).toEqual([0, 0, 0]);
      const end = growSeries({ values: [10, 20, 30], progress: 1, easing: linear });
      expect(end.ratios).toEqual([1, 1, 1]);
      expect(end.values).toEqual([10, 20, 30]);
      const half = growSeries({ values: [10, 20, 30], progress: 0.5, easing: linear });
      expect(half.values).toEqual([5, 10, 15]);
    });

    it('基础值由调用方给出，扣除基础值后生长', () => {
      expect(growSeries({ values: [10, 20], progress: 0, floor: 5, easing: linear }).values).toEqual([5, 5]);
      expect(growSeries({ values: [10, 20], progress: 0.5, floor: 5, easing: linear }).values).toEqual([7.5, 12.5]);
    });

    it('stagger 让数据点依次展开，但仍只由进度决定', () => {
      const early = growSeries({ values: [10, 20, 30], progress: 0.5, stagger: 0.5, easing: linear });
      expect(early.ratios[0]).toBe(1);
      expect(early.ratios[1]).toBeCloseTo(0.5);
      expect(early.ratios[2]).toBe(0);
      const direct = growSeries({ values: [10, 20, 30], progress: 0.5, stagger: 0.5, easing: linear });
      expect(direct).toEqual(early);
    });

    it('空序列返回空结果，不报错', () => {
      expect(growSeries({ values: [], progress: 0.5, easing: linear })).toEqual({ values: [], ratios: [] });
    });
  });

  describe('列表滚屏', () => {
    const params = { count: 10, rowExtent: 100, viewport: 400, overscan: 1, easing: linear };

    it('起点偏移为 0，终点停在最后一行的底部', () => {
      const start = scrollList({ ...params, progress: 0 });
      expect(start.offset).toBe(0);
      expect(start.rows[0]).toEqual({ index: 0, y: 0 });
      const end = scrollList({ ...params, progress: 1 });
      expect(end.offset).toBe(600);
      expect(end.rows[end.rows.length - 1]).toEqual({ index: 9, y: 300 });
    });

    it('可视行包含边缘行并可按 overscan 扩展', () => {
      const middle = scrollList({ ...params, progress: 0.5 });
      expect(middle.offset).toBe(300);
      expect(middle.rows.map(row => row.index)).toEqual([2, 3, 4, 5, 6, 7]);
      const noOverscan = scrollList({ ...params, progress: 0.5, overscan: 0 });
      expect(noOverscan.rows.map(row => row.index)).toEqual([3, 4, 5, 6]);
    });

    it('内容不足以滚动时维持原位', () => {
      const short = scrollList({ count: 2, rowExtent: 100, viewport: 400, progress: 1, easing: linear });
      expect(short.offset).toBe(0);
      expect(short.rows.map(row => row.index)).toEqual([0, 1]);
    });

    it('同一进度与参数重复求值一致', () => {
      expect(scrollList({ ...params, progress: 0.42 })).toEqual(scrollList({ ...params, progress: 0.42 }));
    });
  });

  describe('主体状态插值', () => {
    const states = [{ length: 0, count: 1, date: 1990 }, { length: 50, count: 5, date: 2000 }, { length: 100, count: 9, date: 2020 }];

    it('端点精确返回首末状态', () => {
      expect(interpolateState({ states, progress: 0, easing: linear })).toEqual(states[0]);
      expect(interpolateState({ states, progress: 1, easing: linear })).toEqual(states[2]);
    });

    it('多段关键帧按等距线性插值', () => {
      expect(interpolateState({ states, progress: 0.25, easing: linear })).toEqual({ length: 25, count: 3, date: 1995 });
      expect(interpolateState({ states, progress: 0.75, easing: linear })).toEqual({ length: 75, count: 7, date: 2010 });
    });

    it('缓动只作用于进度，不改变端点', () => {
      const eased = interpolateState({ states, progress: 0.5, easing: square });
      expect(eased).toEqual({ length: 25, count: 3, date: 1995 });
    });

    it('字段不一致或非有限值明确报错', () => {
      expect(() => interpolateState({ states: [{ a: 0 }, { b: 1 }] as never, progress: 0.5, easing: linear })).toThrow('字段不一致');
      expect(() => interpolateState({ states: [{ a: 0 }, { a: Number.NaN }], progress: 0.5, easing: linear })).toThrow('有限数值');
      expect(() => interpolateState({ states: [], progress: 0.5, easing: linear })).toThrow('至少需要一个状态');
    });

    it('单个状态在任意进度都返回该状态', () => {
      expect(interpolateState({ states: [{ value: 7 }], progress: 0.63, easing: linear })).toEqual({ value: 7 });
    });
  });

  describe('签名粒子', () => {
    const params = { count: 40, progress: 0.5, distance: 120, lifetime: 0.7, size: 4, easing: linear };

    it('同一进度与参数重复求值一致', () => {
      expect(particleField(params)).toEqual(particleField(params));
    });

    it('进度 0 与 1 完全透明', () => {
      expect(particleField({ ...params, progress: 0 }).every(particle => particle.opacity === 0)).toBe(true);
      expect(particleField({ ...params, progress: 1 }).every(particle => particle.opacity === 0)).toBe(true);
    });

    it('粒子数量固定，位置与大小有限', () => {
      const particles = particleField(params);
      expect(particles).toHaveLength(40);
      expect(particles.every(particle => Number.isFinite(particle.x) && Number.isFinite(particle.y)
        && Number.isFinite(particle.size))).toBe(true);
    });

    it('种子决定形态：同种子一致，不同种子不同', () => {
      expect(particleField({ ...params, seed: 'a' })).toEqual(particleField({ ...params, seed: 'a' }));
      expect(particleField({ ...params, seed: 'a' })).not.toEqual(particleField({ ...params, seed: 'b' }));
      expect(particleField(params)).toEqual(particleField({ ...params }));
    });

    it('跳帧采样与逐帧推进到同一进度一致', () => {
      let last = particleField({ ...params, progress: 0 });
      for (let frame = 1; frame <= 80; frame += 1) {
        last = particleField({ ...params, progress: frame / 100 });
      }
      expect(particleField({ ...params, progress: 0.8 })).toEqual(last);
    });

    it('参数非法时明确报错', () => {
      expect(() => particleField({ ...params, count: 1.5 })).toThrow('非负整数');
      expect(() => particleField({ ...params, lifetime: 0 })).toThrow('lifetime');
    });
  });

  it('跳帧采样与逐帧推进对生长序列给出同一结果', () => {
    let last = growSeries({ values: [10, 20, 30], progress: 0, stagger: 0.6, easing: linear });
    for (let frame = 1; frame <= 80; frame += 1) {
      last = growSeries({ values: [10, 20, 30], progress: frame / 100, stagger: 0.6, easing: linear });
    }
    expect(growSeries({ values: [10, 20, 30], progress: 0.8, stagger: 0.6, easing: linear })).toEqual(last);
  });

  it('返回结果只含数值与几何，不携带颜色、字体或线宽', () => {
    const number = rollNumber({ from: 0, to: 1, progress: 0.5, easing: linear });
    expect(Object.keys(number).sort()).toEqual(['text', 'value']);
    const particle = particleField({ count: 1, progress: 0.5, easing: linear })[0];
    expect(Object.keys(particle).sort()).toEqual(['index', 'opacity', 'size', 'x', 'y']);
  });
});
