/** 复利数学与圆片编码：1 枚圆片 = 1,000 元，直径按面积（√金额）缩放。 */

export const MODEL = {principal: 10000, rate: .1, years: 30} as const;
export const UNITS_PER_DISC = 1000;
/** 全貌镜头的单枚直径（1920 画布像素）；852 宽下约 18.7px。 */
export const FULL_DIAMETER = 42;
export const SEGMENTS = [
  {id: 'S1', start: 0, end: 3.5},
  {id: 'S2', start: 3.5, end: 8},
  {id: 'S3', start: 8, end: 13},
  {id: 'S4', start: 13, end: 19},
  {id: 'S5', start: 19, end: 29},
] as const;
export const FRAME_BOUNDARIES = [0, 105, 240, 390, 570, 870] as const;
export type SegmentId = (typeof SEGMENTS)[number]['id'];

export const clamp = (v: number) => Math.max(0, Math.min(1, v));
export const ease = (v: number) => {const p = clamp(v); return p * p * (3 - 2 * p);};

function checkYear(year: number, principal: number, rate: number) {
  if (!Number.isFinite(year) || year < 0 || !Number.isFinite(principal) || principal < 0
      || !Number.isFinite(rate) || rate < 0) {
    throw new Error('本金、年份、收益率必须为有限非负数');
  }
}

/** 累计总额；只在显示时舍入。取出组收益留存，不消费也不再产生收益。 */
export function balance(year: number, reinvest: boolean, principal: number = MODEL.principal,
                        rate: number = MODEL.rate) {
  checkYear(year, principal, rate);
  const total = reinvest ? principal * (1 + rate) ** year : principal * (1 + rate * year);
  return {principal, gain: total - principal, total};
}

export function secondYear(principal: number = MODEL.principal, rate: number = MODEL.rate) {
  checkYear(2, principal, rate);
  const firstGain = balance(1, true, principal, rate).gain;
  return {firstGain, fromPrincipal: principal * rate, fromGain: firstGain * rate,
    total: balance(2, true, principal, rate).total};
}

/** 第30年两路累计总额与差额；画面只显示枚数，差额保留为数学口径与测试。 */
export function comparison(year: number, principal: number = MODEL.principal,
                            rate: number = MODEL.rate) {
  checkYear(year, principal, rate);
  const withdraw = balance(year, false, principal, rate);
  const reinvest = balance(year, true, principal, rate);
  return {withdraw, reinvest, difference: reinvest.total - withdraw.total};
}

/** 再投入路径第 n 年末：上年总额已成为资本（米白），本年收益尚未再投入（金）。 */
export function yearState(year: number, principal: number = MODEL.principal,
                          rate: number = MODEL.rate) {
  checkYear(year, principal, rate);
  const total = balance(year, true, principal, rate).total;
  const offWhite = year <= 0 ? principal : balance(year - 1, true, principal, rate).total;
  return {year, offWhite, gold: total - offWhite, total,
    offWhiteUnits: offWhite / UNITS_PER_DISC, goldUnits: (total - offWhite) / UNITS_PER_DISC,
    totalUnits: total / UNITS_PER_DISC};
}

/** 取出路径第 n 年末：10 枚米白本金 + n 枚暗金已取收益。 */
export function withdrawState(year: number, principal: number = MODEL.principal,
                              rate: number = MODEL.rate) {
  checkYear(year, principal, rate);
  const total = balance(year, false, principal, rate).total;
  return {year, offWhite: principal, darkGold: total - principal, total,
    offWhiteUnits: principal / UNITS_PER_DISC, darkGoldUnits: (total - principal) / UNITS_PER_DISC};
}

/**
 * 把单位数拆成可绘制的圆片。小于 minFraction 的尾数不画，也不并进整枚：
 * 并入会让一枚圆片代表超过 1,000 元，破坏“1 枚=1,000、直径∝√金额”。
 * 金额由精确标签承载；S3 微距可显式传 0.1 保留那枚 0.1 金片。
 */
export function discFractions(units: number, minFraction = .25) {
  if (!Number.isFinite(units) || units < 0) throw new Error('圆片单位必须为有限非负数');
  const whole = Math.floor(units + 1e-9);
  const rest = units - whole;
  const discs = Array.from({length: whole}, () => 1);
  if (rest >= minFraction) discs.push(rest);
  else if (!discs.length && rest > 0) discs.push(rest);
  return discs;
}

/** 面积编码：直径 ∝ √单位数。 */
export const discDiameter = (units: number, full: number = FULL_DIAMETER) => full * Math.sqrt(units);

/** 圆片在给定 1920 画布相机缩放与目标显示宽度下的屏幕直径（像素）。 */
export const screenDiameter = (units: number, cameraScale: number, viewportWidth = 852,
                               full: number = FULL_DIAMETER) =>
  discDiameter(units, full) * cameraScale * viewportWidth / 1920;

export function segmentAt(t: number): SegmentId {
  for (const segment of SEGMENTS) if (t < segment.end) return segment.id;
  return SEGMENTS[SEGMENTS.length - 1].id;
}

/** 年份读数：S2=1、S3=2、S4=3，S5 从 3 推进到 30，之后保持 30。 */
export function yearAt(t: number) {
  if (t < 3.5) return 0;
  if (t < 8) return 1;
  if (t < 13) return 2;
  if (t < 19) return 3;
  if (t < 21.4) return 3 + Math.floor(27 * ease((t - 19) / 2.4));
  return MODEL.years;
}

export const money = (n: number) => Math.round(n).toLocaleString('en-US');
