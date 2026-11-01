import {describe, expect, it} from 'vitest';
import {
  FRAME_BOUNDARIES, FULL_DIAMETER, MODEL, SEGMENTS, UNITS_PER_DISC, balance, comparison,
  discDiameter, discFractions, screenDiameter, secondYear, segmentAt,
  withdrawState, yearAt, yearState,
} from '../../styles/count-ledger/examples/compound-interest/scenes/compoundMath';
import {
  AXES, FIRST_DISC_INDEX, HILL_ROWS, hillCell, hillLandingDelay, hillPositions,
} from '../../styles/count-ledger/examples/compound-interest/scenes/compoundLayout';

describe('复利作品的统一金额口径', () => {
  it('匹配独立年度终值，计算过程中不舍入', () => {
    const expected = [10000, 11000, 12100, 25937, 67275, 174494];
    [0, 1, 2, 10, 20, 30].forEach((year, i) => expect(Math.round(balance(year, true).total)).toBe(expected[i]));
    expect(balance(30, false).total).toBe(40000);
    expect(balance(10, true).total).not.toBe(25937);
    expect(balance(30, true).principal).toBe(MODEL.principal);
  });
  it('第二年区分本金收益与收益的收益', () => {
    const v = secondYear();
    expect(v.firstGain).toBeCloseTo(1000);
    expect(v.fromPrincipal).toBe(1000);
    expect(v.fromGain).toBeCloseTo(100);
    expect(v.total).toBeCloseTo(11000 + v.fromPrincipal + v.fromGain);
  });
  it('第30年差额', () => {
    const c = comparison(30);
    expect(Math.round(c.withdraw.total)).toBe(40000);
    expect(Math.round(c.reinvest.total)).toBe(174494);
    expect(Math.round(c.difference)).toBe(134494);
    expect(comparison(30, 10000, 0).difference).toBe(0);
  });
  it('收益取出但仍计入财富，零收益保持本金不变', () => {
    for (const reinvest of [false, true]) for (const year of [0, 1, 2, 10, 20, 30]) {
      const zero = balance(year, reinvest, 10000, 0);
      expect(zero).toEqual({principal: 10000, gain: 0, total: 10000});
      const v = balance(year, reinvest);
      expect(v.principal + v.gain).toBeCloseTo(v.total);
    }
    expect(balance(30, true).total / balance(30, false).total).toBeCloseTo(4.3623505672);
  });
  it('拒绝无效参数', () => {
    for (const n of [-1, NaN, Infinity]) {
      expect(() => balance(n, true)).toThrow();
      expect(() => balance(1, true, n)).toThrow();
      expect(() => balance(1, true, 10000, n)).toThrow();
      expect(() => yearState(n)).toThrow();
      expect(() => withdrawState(n)).toThrow();
      expect(() => discFractions(n)).toThrow();
    }
  });
});

describe('圆片状态机与面积编码', () => {
  it('第30年拆成158.631枚米白与15.863枚金色', () => {
    const v = yearState(30);
    expect(Math.round(v.offWhite)).toBe(158631);
    expect(Math.round(v.gold)).toBe(15863);
    expect(Math.round(v.total)).toBe(174494);
    expect(v.offWhiteUnits).toBeCloseTo(158.631, 2);
    expect(v.goldUnits).toBeCloseTo(15.863, 2);
    expect(v.offWhiteUnits + v.goldUnits).toBeCloseTo(v.totalUnits, 9);
  });
  it('第2年有11枚米白与1.1枚金，0.1枚直径是0.316倍', () => {
    const v = yearState(2);
    expect(v.offWhiteUnits).toBeCloseTo(11);
    expect(v.goldUnits).toBeCloseTo(1.1);
    const discs = discFractions(v.goldUnits, .1);
    expect(discs).toHaveLength(2);
    expect(discs[0]).toBeCloseTo(1);
    expect(discs[1]).toBeCloseTo(.1);
    expect(discDiameter(discs[1]) / discDiameter(1)).toBeCloseTo(.3162277, 5);
  });
  it('取出组第30年是10枚米白加30枚暗金', () => {
    const v = withdrawState(30);
    expect(v.total).toBe(40000);
    expect(v.offWhiteUnits).toBe(10);
    expect(v.darkGoldUnits).toBe(30);
  });
  it('分数圆片按面积直径缩放，小于阈值的尾数不并入整枚', () => {
    expect(FULL_DIAMETER).toBe(42);
    expect(discDiameter(1)).toBe(42);
    expect(discDiameter(4)).toBe(84);
    expect(discDiameter(.1)).toBeCloseTo(13.282, 3);
    expect(discFractions(158.631)).toHaveLength(159);
    expect(discFractions(158.631).reduce((a, b) => a + b, 0)).toBeCloseTo(158.631);
    expect(discFractions(15.863)).toHaveLength(16);
    // 尾数低于阈值时不并入整枚，避免一枚圆片代表超过 1,000 元。
    expect(discFractions(1.21)).toEqual([1]);
    expect(discFractions(12.1)).toHaveLength(12);
    expect(discFractions(.21)).toEqual([.21]);
    expect(discFractions(1).every(unit => unit <= 1)).toBe(true);
    expect(UNITS_PER_DISC).toBe(1000);
    // 852 宽下：S3 的 0.1 金片与 S5 的分数圆片都必须 ≥14px。
    // S3 相机 2.4×：0.1 金片在 852 宽仍 ≥14px。
    expect(screenDiameter(.1, 2.4)).toBeGreaterThanOrEqual(14);
    expect(screenDiameter(.631, 1)).toBeGreaterThanOrEqual(14);
    expect(screenDiameter(.863, 1)).toBeGreaterThanOrEqual(14);
  });
  it('S5丘有159个位置并容纳0.631分数片', () => {
    const white = discFractions(yearState(30).offWhiteUnits);
    const hill = hillPositions(159);
    expect(white).toHaveLength(159);
    expect(hill).toHaveLength(159);
    expect(white.reduce((a, b) => a + b, 0)).toBeCloseTo(158.631);
    expect(FIRST_DISC_INDEX).toBeGreaterThanOrEqual(0);
    expect(FIRST_DISC_INDEX).toBeLessThan(hill.length);
  });
});

describe('统一列轴与结构化金雨', () => {
  it('左右列轴关于画面中心对称，丘与右柱同轴', () => {
    expect(AXES.left + AXES.right).toBe(1920);
    expect(AXES.right).toBe(AXES.hill);
    expect(960 - AXES.left).toBe(AXES.right - 960);
  });
  it('丘索引按行列定位，行从下往上、行内从左往右', () => {
    expect(hillCell(0)).toEqual({row: 0, col: 0});
    expect(hillCell(HILL_ROWS[0] - 1)).toEqual({row: 0, col: HILL_ROWS[0] - 1});
    expect(hillCell(HILL_ROWS[0])).toEqual({row: 1, col: 0});
    const last = HILL_ROWS.reduce((a, b) => a + b, 0) - 1;
    expect(hillCell(last)).toEqual({row: HILL_ROWS.length - 1, col: HILL_ROWS.at(-1)! - 1});
    expect(() => hillCell(-1)).toThrow();
    expect(() => hillCell(last + 1)).toThrow();
    expect(() => hillCell(1.5)).toThrow();
  });
  it('金雨落定按行列成波次，不再随机', () => {
    expect(hillLandingDelay(0)).toBe(0);
    expect(hillLandingDelay(1)).toBeGreaterThan(hillLandingDelay(0));
    // 下一行首枚比本行首枚晚 0.09 秒；同排逐枚递增 0.018 秒。
    expect(hillLandingDelay(HILL_ROWS[0]) - hillLandingDelay(0)).toBeCloseTo(.09);
    // 末枚落定不超过 1.1 秒，仍在 19.4–20.5 秒窗口内。
    const last = HILL_ROWS.reduce((a, b) => a + b, 0) - 1;
    expect(hillLandingDelay(last)).toBeLessThan(1.1);
    for (let i = 1; i <= last; i++) {
      if (hillCell(i).row === hillCell(i - 1).row) {
        expect(hillLandingDelay(i)).toBeGreaterThan(hillLandingDelay(i - 1));
      }
    }
  });
});

describe('六段时间轴', () => {
  it('段落连续覆盖29秒', () => {
    expect(SEGMENTS[0].start).toBe(0);
    expect(SEGMENTS.at(-1)?.end).toBe(29);
    SEGMENTS.slice(1).forEach((segment, i) => expect(segment.start).toBe(SEGMENTS[i].end));
    expect(Array.from(FRAME_BOUNDARIES)).toEqual(SEGMENTS.flatMap((s, i) => i === 0 ? [0, s.end * 30] : [s.end * 30]));
  });
  it('段落与年份读数在边界正确', () => {
    expect(segmentAt(0)).toBe('S1');
    expect(segmentAt(3.49)).toBe('S1');
    expect(segmentAt(3.5)).toBe('S2');
    expect(segmentAt(8)).toBe('S3');
    expect(segmentAt(13)).toBe('S4');
    expect(segmentAt(18)).toBe('S4');
    expect(segmentAt(19)).toBe('S5');
    expect(segmentAt(24.79)).toBe('S5');
    expect(segmentAt(24.8)).toBe('S6');
    expect(segmentAt(28.99)).toBe('S6');
    expect(segmentAt(29.5)).toBe('S6');
    expect(yearAt(3.5)).toBe(1);
    expect(yearAt(8)).toBe(2);
    expect(yearAt(13)).toBe(3);
    expect(yearAt(18)).toBe(3);
    expect(yearAt(19)).toBe(3);
    expect(yearAt(21.4)).toBe(30);
    expect(yearAt(21.5)).toBe(30);
    expect(yearAt(24)).toBe(30);
  });
  it('S5年份单调推进且不超过30', () => {
    let previous = 3;
    for (let frame = 570; frame <= 720; frame++) {
      const year = yearAt(frame / 30);
      expect(Number.isInteger(year)).toBe(true);
      expect(year).toBeGreaterThanOrEqual(previous);
      expect(year).toBeLessThanOrEqual(30);
      previous = year;
    }
  });
});
