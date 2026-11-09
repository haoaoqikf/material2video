import {expect, it} from 'vitest';
import {designFrame} from './capital-state';
import {DIRECTIONS, directionFrame} from './typography-themes';

it('字体背景选案不改变金额、状态或两组内部的物理单位', () => {
  const baseline = designFrame(2);
  for (let index = 0; index < DIRECTIONS.length; index++) {
    const frame = directionFrame(index);
    expect(frame.tokens.map(({id, units, tone}) => ({id, units, tone}))).toEqual(
      baseline.tokens.map(({id, units, tone}) => ({id, units, tone})));
    for (const prefix of ['l-', 'r-']) {
      const current = frame.tokens.filter(item => item.id.startsWith(prefix));
      const original = baseline.tokens.filter(item => item.id.startsWith(prefix));
      for (let i = 0; i < current.length; i++) {
        expect(current[i].x - current[0].x).toBeCloseTo(original[i].x - original[0].x);
        expect(current[i].y).toBe(original[i].y);
        expect(current[i].z).toBe(original[i].z);
      }
    }
  }
});
