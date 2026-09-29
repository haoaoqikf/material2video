import { describe, expect, it } from 'vitest';
import { beatActionProgress, compilePath, compileReservoir, decomposeObjects } from './objectMotion';

describe('对象动画', () => {
  it('节拍前后与提前完成', () => {
    const plan = [{ id: 'a', startFrame: 10, endFrame: 30, action: 'transfer', targets: ['x'], meaning: '流动' }];
    expect([0, 15, 20, 40].map((f) => beatActionProgress(plan, 'a', f, .5))).toEqual([0, .5, 1, 1]);
    expect(() => beatActionProgress(plan, 'missing', 0)).toThrow();
  });
  it('按弧长走折线路径和固定相位', () => {
    const path = compilePath([{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 20 }]);
    expect(path(.5)).toEqual({ x: 10, y: 5 }); expect(path(1)).toEqual({ x: 10, y: 20 });
    expect(path(.8, .4).x).toBeCloseTo(path(.2).x);
  });
  it('积累、溢出、空箱和守恒，随机寻帧无需重放', () => {
    const state = compileReservoir(10, 2, [{ duration: 5, inflow: 5, outflow: 1 }, { duration: 10, inflow: 0, outflow: 2 }]);
    for (const t of [8, 2, 12, 0, 5, 8]) { const s = state(t); expect(s.level).toBeGreaterThanOrEqual(0); expect(s.level).toBeLessThanOrEqual(10); expect(s.level + s.overflow + s.drained).toBeCloseTo(2 + s.input); }
    expect(state(5).overflow).toBe(12); expect(state(15).level).toBe(0); expect(state(8)).toEqual(state(8));
  });
  it('拆解复原和重复 ID 失败', () => {
    const objects = [{ id: 'x', from: { x: 0, y: 1 }, to: { x: 10, y: 11 } }];
    expect(decomposeObjects(objects, 1, true)).toEqual([{ id: 'x', x: 0, y: 1 }]);
    expect(decomposeObjects(objects, .5)[0]).toEqual({ id: 'x', x: 5, y: 6 });
    expect(() => decomposeObjects([...objects, ...objects], 0)).toThrow();
  });
});
