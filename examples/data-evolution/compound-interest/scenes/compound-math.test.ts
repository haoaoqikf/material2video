import {expect, it} from 'vitest';
import {balance, comparison, discDiameter, discFractions, secondYear} from './compoundMath';

it('年度金额独立核对及零收益边界不引入虚构回报', () => {
  const expected = [[0, 10000], [1, 11000], [2, 12100], [3, 13310],
    [10, 25937], [20, 67275], [30, 174494]];
  for (const [year, value] of expected) expect(Math.round(balance(year, true).total)).toBe(value);
  expect(comparison(30).withdraw.total).toBe(40000);
  expect(Math.round(comparison(30).difference)).toBe(134494);
  for (const reinvest of [false, true]) expect(balance(30, reinvest, 10000, 0).total).toBe(10000);
  expect(secondYear().fromGain).toBe(100);
  expect(() => balance(NaN, true)).toThrow();
  expect(() => balance(1, true, 10000, -1)).toThrow();
});

it('保留全部尾数时面积编码精确且不把小收益并成整枚', () => {
  for (const units of [.1, 1.1, 12.1, 158.631, 15.863]) {
    const coins = discFractions(units, 0).filter(value => value > 1e-8);
    expect(coins.reduce((sum, value) => sum + value, 0)).toBeCloseTo(units);
    expect(coins.every(value => value <= 1)).toBe(true);
  }
  expect((discDiameter(.1) / discDiameter(1)) ** 2).toBeCloseTo(.1);
});
