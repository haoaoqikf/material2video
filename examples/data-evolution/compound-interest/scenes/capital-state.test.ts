import {describe, expect, it} from 'vitest';
import {designFrame} from './capital-state';
import {yearState} from './compoundMath';
import {CAPITAL_STYLE} from './capital-style';

describe('原生静态选案的金额、投影与物理基线', () => {
  it('开场两组等量资本，核心图区分原资本和去年收益的产出', () => {
    const opening = designFrame(0).tokens;
    for (const prefix of ['l-', 'r-']) expect(opening.filter(item => item.id.startsWith(prefix))
      .reduce((sum, item) => sum + item.units, 0)).toBe(10);
    const core = designFrame(1).tokens;
    const small = core.find(item => item.id === 'year-2-reinvested')!;
    const large = core.find(item => item.id === 'year-2-original')!;
    const parent = core.find(item => item.id === 'r-10')!;
    expect(small.x).toBe(parent.x);
    expect(small.units / large.units).toBeCloseTo(.1);
    expect(small.pitch).toBe(large.pitch);
    expect(small.tilt).toBe(large.tilt);
    expect(core.reduce((sum, item) => sum + item.units, 0)).toBeCloseTo(yearState(2).totalUnits);
  });
  it('最终实体保留真实尾数、金白分拆和同一物理地面', () => {
    const {tokens} = designFrame(2);
    const right = tokens.filter(item => item.id.startsWith('r-'));
    const left = tokens.filter(item => item.id.startsWith('l-'));
    expect(right).toHaveLength(175);
    expect(left).toHaveLength(40);
    expect(left.filter(item => item.tone === 'white')).toHaveLength(10);
    expect(left.filter(item => item.tone === 'dark')).toHaveLength(30);
    expect(right.filter(item => item.tone === 'white').reduce((sum, item) => sum + item.units, 0)).toBeCloseTo(yearState(30).offWhiteUnits);
    expect(right.filter(item => item.tone === 'gold').reduce((sum, item) => sum + item.units, 0)).toBeCloseTo(yearState(30).goldUnits);
    expect(tokens.every(item => item.pitch === -Math.PI / 2)).toBe(true);
    const bottom = (items: typeof tokens) => Math.min(...items.map(item => 1080 - item.y - CAPITAL_STYLE.backDepth *
      Math.max(.35, Math.sqrt(item.units)) * item.thickness!));
    expect(bottom(left)).toBeCloseTo(CAPITAL_STYLE.floorY);
    expect(bottom(right)).toBeCloseTo(CAPITAL_STYLE.floorY);
    // 按真实网格上下边界核验尾数片也不会穿入上一枚，而非只检查中心坐标。
    const piles = new Map<string, typeof tokens>();
    for (const item of tokens) {
      const key = `${item.x}:${item.z}`;
      piles.set(key, [...(piles.get(key) ?? []), item]);
    }
    for (const pile of piles.values()) {
      pile.sort((a, b) => b.y - a.y);
      for (let i = 1; i < pile.length; i++) {
        const previous = pile[i - 1], current = pile[i];
        const previousTop = 1080 - previous.y + CAPITAL_STYLE.faceHeight *
          Math.max(.35, Math.sqrt(previous.units)) * previous.thickness!;
        const currentBottom = 1080 - current.y - CAPITAL_STYLE.backDepth *
          Math.max(.35, Math.sqrt(current.units)) * current.thickness!;
        expect(currentBottom).toBeGreaterThan(previousTop);
      }
    }
  });
  it('三幅可以乱序求值且不累积状态，不产生未定义金额或无效位置', () => {
    const expected = designFrame(2);
    [1, 0, 1, 0].forEach(designFrame);
    expect(designFrame(2)).toEqual(expected);
    for (const panel of [0, 1, 2]) for (const item of designFrame(panel).tokens) {
      expect([item.x, item.y, item.z, item.units, item.opacity, item.gold].every(Number.isFinite)).toBe(true);
      expect(item.units).toBeGreaterThan(0);
    }
    for (const invalid of [-1, 3, .5, NaN, Infinity]) expect(() => designFrame(invalid)).toThrow();
  });
});
