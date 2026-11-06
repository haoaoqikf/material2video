/**
 * 金融折线的曲线与坐标求值：帧→日期映射、分段扩展的横轴、因果平滑的值域、
 * 刻度选择、数值/文本度量与折线裁剪校验。
 *
 * 全部为纯函数（只有缓存用的 `WeakMap`，输入是不可变的渲染 props），不持有
 * 帧相关状态，因此同一帧在任何一次渲染里都得到同一结果。
 */
import {easeMotion} from '../../code-scene/motion';
import {chartLinePath} from '../../code-scene/chart-geometry';
import type {FinancialDesign} from './design';

type ISODate = string;
type PricePoint = { date: ISODate; close: number };
type FxPoint = { date: ISODate; close: number };
type TimelineSegment = { frames: [number, number]; dates: [ISODate, ISODate]; kind: 'opening' | 'advance' | 'ending' };
export type FinancialPlan = {
  schemaVersion: 8; chartType: 'line';
  durationSeconds: number; fps: number; canvas: { width: 1080; height: 1920 };
  axis: { dateRange: [ISODate, ISODate]; dateScale: 'staged-expanding'; valueScale: 'revealed-linear' };
  segments: TimelineSegment[];
  pacing?: { mode: 'uniform' | 'volatility'; anchors: { frame: number; date: ISODate }[] };
  rationale: string;
};
export type FinancialTimeSeriesProps = {
  request: { instrument: { kind: 'stock' | 'index' | 'crypto'; name: string; displayName?: string; code: string; market: string; unit: string }; displayRange: [ISODate, ISODate]; investment?: { year?: number; date?: ISODate; principal: number; currency?: 'CNY'; startRationale?: string; legalStatusNotice?: string }; design?: FinancialDesign };
  prices: { schemaVersion: 3 | 4; points: PricePoint[]; unit: string; priceBasis: string; adjustmentDefinition?: string; indexType?: string; sources: unknown[]; fx?: { pair: 'USD/CNY'; points: FxPoint[] } };
  plan: FinancialPlan;
  durationInFrames: number; fps: number; width: 1080; height: 1920;
};
export type Investment = NonNullable<FinancialTimeSeriesProps['request']['investment']>;

export const WIDTH = 1080;
export const HEIGHT = 1920;
export const PLOT = { left: 200, right: 920, top: 500, bottom: 1280 };
const DAY_MS = 86_400_000;
export const FONT_STACK = '"M2V Inter", "M2V Sans", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif';
export const PROFIT_COLOR = '#FF5A4E';
export const LOSS_COLOR = '#4BD39A';
export const NEUTRAL_COLOR = '#D8D4CC';
export const BACKGROUND_COLOR = '#0B0A09';
export const TEXT_PRIMARY = '#F1EBDF';
export const TEXT_SECONDARY = '#9A9388';
export const TEXT_MUTED = '#6E685F';
export const GRID_COLOR = 'rgba(241,235,223,0.09)';
export const STATEMENT_RULE_OPACITY = 0.18;
export const STATEMENT_MASTHEAD_RULE_Y = 200;
export const STATEMENT_CLOSING_RULE_Y = 1360;
export const VALUE_AXIS_FONT_SIZE = 24;
export const VALUE_AXIS_LABEL_X = 188;
export const TITLE_SUBJECT_SIZE = 56;
export const TITLE_PREMISE_SIZE = 32;
export const TITLE_SUBJECT_MIN = 48;
export const TITLE_PREMISE_MIN = 28;
export const LAYOUT_BOUNDS = { left: 140, right: 940, top: 180, bottom: 1740 };
export type ChartPoint = { x: number; y: number };

function epochDay(value: ISODate): number {
  const [year, month, day] = value.split('-').map(Number);
  return Date.UTC(year!, month! - 1, day!) / DAY_MS;
}

function isoDay(day: number): ISODate {
  return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

export function framePosition(frame: number, plan: FinancialPlan): number {
  const segment = plan.segments.find(({ frames: [start, end] }) => start <= frame && frame < end);
  if (!segment) throw new Error(`帧 ${frame} 没有对应时间段`);
  const [startDate, endDate] = segment.dates;
  if (segment.kind !== 'advance') return epochDay(startDate);
  if (frame === segment.frames[1] - 1) return epochDay(endDate);
  const anchors = plan.pacing!.anchors;
  let low = 0; let high = anchors.length - 1;
  while (low + 1 < high) {
    const mid = (low + high) >>> 1;
    if (anchors[mid]!.frame <= frame) low = mid;
    else high = mid;
  }
  const left = anchors[low]!; const right = anchors[high]!;
  return epochDay(left.date) + ((frame - left.frame) * (epochDay(right.date) - epochDay(left.date))) / (right.frame - left.frame);
}

function lastPointIndex(points: PricePoint[], date: ISODate): number {
  let low = 0;
  let high = points.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (points[mid]!.date <= date) low = mid + 1;
    else high = mid;
  }
  return low - 1;
}

/** 投资起点首次出现的帧；用于市值入场，不改变日期映射。 */
export function firstFrameForDate(plan: FinancialPlan, value: ISODate): number {
  const target = epochDay(value);
  let low = 0;
  let high = plan.durationSeconds * plan.fps - 1;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (Math.floor(framePosition(mid, plan)) >= target) high = mid;
    else low = mid + 1;
  }
  return low;
}

export function revealedValueRange(points: PricePoint[]): [number, number] {
  if (points.length === 0) return [0, 1];
  let low = points[0]!.close;
  let high = low;
  for (let index = 1; index < points.length; index++) {
    low = Math.min(low, points[index]!.close);
    high = Math.max(high, points[index]!.close);
  }
  if (low === high) {
    const halfSpan = Math.max(Math.abs(low) * 0.01, 0.01);
    return [low - halfSpan, high + halfSpan];
  }
  const padding = (high - low) * 0.08;
  return [low - padding, high + padding];
}

export function valueTickDecimals(minValue: number, maxValue: number): number {
  const tickStep = (maxValue - minValue) / 4;
  return Math.min(6, Math.max(2, Math.ceil(-Math.log10(tickStep)) + 1));
}

type TickInterval = { unit: 'year' | 'month'; step: number };
type AxisTransition = { start: number; end: number; target: number; oldEnd: number };

function annualBoundaries(start: number, end: number): number[] {
  const startYear = new Date(start * DAY_MS).getUTCFullYear();
  const endYear = new Date(end * DAY_MS).getUTCFullYear();
  const yearCount = endYear - startYear + 1;
  if (yearCount <= 1) return [end];
  const yearStep = Math.ceil(yearCount / 6);
  const boundaries: number[] = [];
  for (let year = startYear + yearStep - 1; year < endYear; year += yearStep) {
    boundaries.push(Math.min(epochDay(`${year}-12-31`), end));
  }
  if (boundaries.at(-1) !== end) boundaries.push(end);
  return [...new Set(boundaries)];
}

const transitionCache = new WeakMap<FinancialPlan, AxisTransition[]>();

function axisTransitions(plan: FinancialPlan): AxisTransition[] {
  const cached = transitionCache.get(plan);
  if (cached) return cached;
  const [startDate, endDate] = plan.axis.dateRange;
  const start = epochDay(startDate);
  const end = epochDay(endDate);
  const boundaries = annualBoundaries(start, end);
  if (boundaries.length <= 1) return [];
  const advance = plan.segments.find(({ kind }) => kind === 'advance')!;
  const [advanceStart, advanceEnd] = advance.frames;
  const dateAt = (frame: number) => framePosition(frame, plan);
  const candidates: AxisTransition[] = [];
  let oldEnd = boundaries[0]!;
  for (const target of boundaries.slice(1)) {
    let low = advanceStart; let high = advanceEnd;
    while (low < high) {
      const mid = (low + high) >>> 1;
      // Expand before crossing the current boundary, not the new target.
      if (dateAt(mid) > oldEnd) high = mid;
      else low = mid + 1;
    }
    const endFrame = low;
    const startFrame = Math.max(advanceStart, endFrame - 15);
    candidates.push({ start: startFrame, end: endFrame, target, oldEnd });
    oldEnd = target;
  }
  const merged: AxisTransition[] = [];
  for (const current of candidates) {
    const previous = merged.at(-1);
    if (previous && current.start <= previous.end) {
      previous.end = Math.max(previous.end, current.end);
      previous.target = current.target;
    } else merged.push({ ...current });
  }
  transitionCache.set(plan, merged);
  return merged;
}

function tickInterval(start: number, end: number): TickInterval {
  const span = end - start;
  if (span > 730) {
    const step = Math.max(1, Math.ceil(span / 365.25 / 7));
    return { unit: 'year', step };
  }
  const monthStep = Math.max(1, Math.ceil(span / 30 / 7));
  return { unit: 'month', step: monthStep };
}

function ticksForInterval(start: number, end: number, interval: TickInterval): ISODate[] {
  const ticks: ISODate[] = [];
  if (interval.unit === 'year') {
    const firstYear = new Date(start * DAY_MS).getUTCFullYear();
    const step = interval.step;
    for (let value = Math.ceil(firstYear / step) * step; epochDay(`${value}-01-01`) <= end; value += step) {
      const tick = `${value}-01-01`;
      if (epochDay(tick) >= start) ticks.push(tick);
    }
  } else {
    const date = new Date(start * DAY_MS);
    const step = interval.step;
    let next = Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 1) / DAY_MS;
    while (next < end) {
      ticks.push(isoDay(next));
      const tick = new Date(next * DAY_MS);
      next = Date.UTC(tick.getUTCFullYear(), tick.getUTCMonth() + step, 1) / DAY_MS;
    }
  }
  return ticks;
}

type AxisTick = { date: ISODate; label: string; opacity: number };

function selectStableTicks(ticks: AxisTick[], start: number, layoutEnd: number): AxisTick[] {
  const unique = [...new Map(ticks.map((tick) => [tick.date, tick])).values()];
  const span = Math.max(layoutEnd - start, 1);
  const positioned = unique.map((tick) => {
    const width = tick.label.length * 18;
    const x = PLOT.left + ((epochDay(tick.date) - start) / span) * (PLOT.right - PLOT.left);
    return { ...tick, x: Math.max(PLOT.left, Math.min(x, PLOT.right - width / 2)), width };
  }).sort((a, b) => a.x - b.x || a.date.localeCompare(b.date));
  if (positioned.length <= 4) return positioned;

  const selected: typeof positioned = [];
  const first = positioned[0]!;
  const last = positioned.at(-1)!;
  if (Math.abs(last.x - first.x) >= (last.width + first.width) / 2 + 12) selected.push(first, last);
  else selected.push(last);
  while (selected.length < 4) {
    const next = positioned
      .filter((tick) => !selected.some((item) => item.date === tick.date))
      .filter((tick) => selected.every((other) => Math.abs(tick.x - other.x) >= (tick.width + other.width) / 2 + 12))
      .sort((a, b) => {
        const spreadA = Math.min(...selected.map((item) => Math.abs(a.x - item.x)));
        const spreadB = Math.min(...selected.map((item) => Math.abs(b.x - item.x)));
        return spreadB - spreadA || b.opacity - a.opacity || a.date.localeCompare(b.date);
      })[0];
    if (!next) break;
    selected.push(next);
  }
  return selected.sort((a, b) => a.x - b.x);
}

function axisTicks(windowStart: number, visibleEnd: number, fullRangeEnd: number) {
  // Fix labels for the whole composition. Each label enters once as the axis
  // reaches it, so changing span or collision order cannot make a year blink.
  const interval = tickInterval(windowStart, fullRangeEnd);
  const dates = [isoDay(windowStart), ...ticksForInterval(windowStart, fullRangeEnd, interval)];
  const finalYear = isoDay(fullRangeEnd).slice(0, 4);
  if (interval.unit === 'year' && !dates.some((date) => date.slice(0, 4) === finalYear)) dates.push(isoDay(fullRangeEnd));
  const stable = selectStableTicks(dates.map((date) => ({ date, label: interval.unit === 'year' ? date.slice(0, 4) : date.slice(0, 7), opacity: 1 })), windowStart, fullRangeEnd);
  return stable.filter((tick) => epochDay(tick.date) <= visibleEnd);
}

// Prefix ranges avoid scanning decades of daily prices six times per frame.
// Inputs are immutable render props; the cache stores no frame-dependent state.
const prefixRanges = new WeakMap<PricePoint[], [number, number][]>();
const investmentSeriesCache = new WeakMap<PricePoint[], Map<string, { points: PricePoint[]; startDate: ISODate; principal: number; buyClose: number } | null>>();
const cryptoSeriesCache = new WeakMap<PricePoint[], WeakMap<FxPoint[], Map<string, { points: PricePoint[]; startDate: ISODate; principal: number; buyClose: number } | null>>>();
function investmentSeries(points: PricePoint[], year: number, principal: number) {
  let cache = investmentSeriesCache.get(points);
  if (!cache) { cache = new Map(); investmentSeriesCache.set(points, cache); }
  const key = `${year}:${principal}`;
  if (cache.has(key)) return cache.get(key)!;
  const first = points.findIndex((point) => Number(point.date.slice(0, 4)) === year);
  if (first < 0) { cache.set(key, null); return null; }
  const buyClose = points[first]!.close;
  const result = { points: points.slice(first).map((point) => ({ date: point.date, close: principal * point.close / buyClose })), startDate: points[first]!.date, principal, buyClose };
  cache.set(key, result);
  return result;
}
function cryptoInvestmentSeries(points: PricePoint[], fxPoints: FxPoint[], date: ISODate, principal: number) {
  let byFx = cryptoSeriesCache.get(points);
  if (!byFx) { byFx = new WeakMap(); cryptoSeriesCache.set(points, byFx); }
  let cache = byFx.get(fxPoints);
  if (!cache) { cache = new Map(); byFx.set(fxPoints, cache); }
  const key = `${date}:${principal}`;
  if (cache.has(key)) return cache.get(key)!;
  const startIndex = points.findIndex((point) => point.date === date);
  if (startIndex < 0) throw new Error(`缺少买入日 ${date} 的 BTC 日收盘价`);
  const buyFxIndex = lastPointIndex(fxPoints, date);
  if (buyFxIndex < 0) throw new Error(`缺少 ${date} 当日或此前的 USD/CNY 汇率`);
  const buyClose = points[startIndex]!.close;
  const buyFx = fxPoints[buyFxIndex]!.close;
  let fxIndex = buyFxIndex;
  const valued = points.slice(startIndex).map((point) => {
    while (fxIndex + 1 < fxPoints.length && fxPoints[fxIndex + 1]!.date <= point.date) fxIndex++;
    return { date: point.date, close: principal * point.close / buyClose * fxPoints[fxIndex]!.close / buyFx };
  });
  const series = { points: valued, startDate: date, principal, buyClose };
  cache.set(key, series);
  return series;
}
function rangesFor(points: PricePoint[]): [number, number][] {
  const cached = prefixRanges.get(points);
  if (cached) return cached;
  let low = Infinity; let high = -Infinity;
  const ranges = points.map((point) => {
    low = Math.min(low, point.close); high = Math.max(high, point.close);
    return revealedValueRange([{ date: point.date, close: low }, { date: point.date, close: high }]);
  });
  prefixRanges.set(points, ranges);
  return ranges;
}

export function financialView(frame: number, points: PricePoint[], plan: FinancialPlan, investment?: { year?: number; date?: ISODate; principal: number; currency?: 'CNY' }, fxPoints?: FxPoint[]) {
  const position = framePosition(frame, plan);
  const currentDate = isoDay(Math.floor(position));
  const windowPosition = epochDay(plan.axis.dateRange[0]);
  const fullRangeEnd = epochDay(plan.axis.dateRange[1]);
  const transitions = axisTransitions(plan);
  let windowEndPosition = annualBoundaries(windowPosition, fullRangeEnd)[0]!;
  for (const transition of transitions) {
    if (frame < transition.start) break;
    const progress = Math.max(0, Math.min(1, (frame - transition.start) / Math.max(transition.end - transition.start, 1)));
    const eased = easeMotion('easeInOutCubic', progress);
    windowEndPosition = Math.max(windowEndPosition, transition.oldEnd + (transition.target - transition.oldEnd) * eased);
    if (frame >= transition.end) windowEndPosition = Math.max(windowEndPosition, transition.target);
  }
  windowEndPosition = Math.min(fullRangeEnd, Math.max(windowEndPosition, position));
  const endingStart = plan.segments.find((segment) => segment.kind === 'ending')!.frames[0];
  if (frame >= endingStart - 1) windowEndPosition = fullRangeEnd;
  const config = investment ?? { year: Number(plan.axis.dateRange[0].slice(0, 4)), principal: 1_000_000 };
  let series;
  if (config.date) {
    if (!fxPoints?.length) throw new Error('缺少 USD/CNY 历史汇率');
    series = cryptoInvestmentSeries(points, fxPoints, config.date, config.principal);
  } else {
    series = investmentSeries(points, config.year ?? Number(plan.axis.dateRange[0].slice(0, 4)), config.principal);
  }
  const valuePoints = series?.points ?? [];
  const end = lastPointIndex(valuePoints, currentDate) + 1;
  const ranges = rangesFor(valuePoints);
  const target = ranges[end - 1] ?? [0, 1];
  let low = 0; let high = 0; let weightTotal = 0;
  // Freeze the last advance frame's axis for the entire ending.
  const rawTicks = axisTicks(windowPosition, windowEndPosition, fullRangeEnd);
  const axisWidth = PLOT.right - PLOT.left;
  const positioned = rawTicks.filter((tick) => epochDay(tick.date) <= windowEndPosition).map((tick) => {
    const width = tick.label.length * 18;
    const x = PLOT.left + ((epochDay(tick.date) - windowPosition) / Math.max(windowEndPosition - windowPosition, 1)) * axisWidth;
    return { ...tick, x: Math.max(PLOT.left, Math.min(x, PLOT.right - width / 2)), width };
  });
  const visibleAxisTicks = positioned.filter((tick) => epochDay(tick.date) <= position).sort((a, b) => a.x - b.x);
  const axisFrame = Math.min(frame, endingStart - 1);
  for (let offset = 0; offset < 6; offset++) {
    const date = isoDay(Math.floor(framePosition(Math.max(0, axisFrame - offset), plan)));
    const range = ranges[lastPointIndex(valuePoints, date)];
    if (!range) continue;
    const weight = 6 - offset;
    low += range[0] * weight; high += range[1] * weight; weightTotal += weight;
  }
  // Never crop a newly arrived extreme while smoothing a contracting bound.
  low = Math.max(0, weightTotal ? Math.min(target[0], low / weightTotal) : target[0]);
  high = weightTotal ? Math.max(target[1], high / weightTotal) : target[1];
  const visiblePoints = valuePoints.slice(0, end);
  const latest = end > 0 ? valuePoints[end - 1]! : null;
  const gain = latest ? latest.close - config.principal : null;
  return { currentDate, position, windowPosition, windowEndPosition,
    windowStart: plan.axis.dateRange[0], windowEnd: plan.axis.dateRange[1], ticks: visibleAxisTicks,
    minValue: low, maxValue: high, visiblePoints, linePoints: visiblePoints,
    latest, investmentStartDate: series?.startDate ?? null, principal: config.principal,
    gain, returnRate: gain === null ? null : gain / config.principal };
}

export type FinancialView = ReturnType<typeof financialView>;

function magnitude(value: number): { value: number; unit: string } {
  const rounded = Math.sign(value) * (Math.round(Math.abs(value) * 100) / 100);
  const { divisor, unit } = unitScale(rounded);
  return { value: rounded / divisor, unit };
}

/** 中文数量级与除数；金额和纵轴共用同一刻度体系。 */
export function unitScale(value: number): { divisor: number; unit: string } {
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000_000_000) return { divisor: 1_000_000_000_000, unit: '万亿' };
  if (absolute >= 100_000_000) return { divisor: 100_000_000, unit: '亿' };
  if (absolute >= 10_000) return { divisor: 10_000, unit: '万' };
  return { divisor: 1, unit: '' };
}

const plainNumber = new Intl.NumberFormat('zh-CN', { useGrouping: false, maximumFractionDigits: 2 });
const fixedNumber = (digits: number) => new Intl.NumberFormat('zh-CN', {
  useGrouping: false, minimumFractionDigits: digits, maximumFractionDigits: digits,
});

function magnitudeNumber(value: number): string {
  return plainNumber.format(value);
}

export function investmentAmountText(value: number): string {
  const scaled = magnitude(value);
  return `${magnitudeNumber(scaled.value)}${scaled.unit}`;
}

export function moneyText(value: number): string {
  const scaled = magnitude(value);
  return `${magnitudeNumber(scaled.value)}${scaled.unit}元`;
}

export function compactValue(value: number): string {
  const scaled = magnitude(value);
  return `${new Intl.NumberFormat('zh-CN', { useGrouping: false, maximumSignificantDigits: 3 }).format(scaled.value)}${scaled.unit}`;
}

/** 纵轴刻度的统一小数位：按缩放后的刻度间距决定，避免相邻刻度四舍五入成同一个值。 */
export function axisTickDecimals(minValue: number, maxValue: number): number {
  const { divisor } = unitScale(Math.max(Math.abs(minValue), Math.abs(maxValue)));
  const step = Math.abs(maxValue - minValue) / 4 / divisor;
  if (!Number.isFinite(step) || step <= 0) return 0;
  return Math.min(4, Math.max(0, Math.ceil(-Math.log10(step)) + 1));
}

/** 纵轴刻度只输出数字，数量级单位在轴顶标注一次。 */
export function axisTickLabel(value: number, divisor: number, decimals: number): string {
  const scaled = value / divisor;
  if (Math.abs(scaled) < 10 ** -decimals / 2) return fixedNumber(decimals).format(0);
  return fixedNumber(decimals).format(scaled);
}

/** 纵轴数量级单位，取纵轴上限所在档位。 */
export function axisUnit(maxValue: number): { divisor: number; unit: string } {
  return unitScale(maxValue);
}

export function displayDate(value: ISODate): string {
  const [year, month, day] = value.split('-');
  return `${year}年${Number(month)}月${Number(day)}日`;
}

export function measuredTextWidth(value: string, fontSize: number): number {
  return [...value].reduce((width, char) => width + (/[^\u0000-\u00ff]/u.test(char) ? fontSize : fontSize * 0.56), 0);
}

export function wrapSvgText(value: string, maxWidth: number, fontSize: number): string[] {
  const measure = (text: string) => [...text].reduce((width, char) => width + (/[\u0000-\u00ff]/.test(char) ? fontSize * 0.56 : fontSize), 0);
  const lines: string[] = [];
  let line = '';
  const units = value.match(/[A-Za-z0-9.-]+|\s+|[\s\S]/gu) ?? [];
  for (const unit of units) {
    const candidate = line + unit;
    if (line && measure(candidate) > maxWidth) { lines.push(line.trimEnd()); line = unit.trimStart(); }
    else line = candidate;
    if (measure(line) > maxWidth) {
      let remainder = '';
      for (const char of [...line]) {
        if (remainder && measure(remainder + char) > maxWidth) { lines.push(remainder); remainder = char; }
        else remainder += char;
      }
      line = remainder;
    }
  }
  if (line) lines.push(line);
  return lines;
}

export type FinancialBounds = { x: number; y: number; width: number; height: number };

export function boundsInMatrix(bounds: FinancialBounds, matrix: DOMMatrix) {
  const corners = [
    new DOMPoint(bounds.x, bounds.y), new DOMPoint(bounds.x + bounds.width, bounds.y),
    new DOMPoint(bounds.x, bounds.y + bounds.height), new DOMPoint(bounds.x + bounds.width, bounds.y + bounds.height),
  ].map((point) => point.matrixTransform(matrix));
  const left = Math.min(...corners.map(({ x }) => x));
  const right = Math.max(...corners.map(({ x }) => x));
  const top = Math.min(...corners.map(({ y }) => y));
  const bottom = Math.max(...corners.map(({ y }) => y));
  return { x: left, y: top, width: right - left, height: bottom - top };
}

export function transformedBounds(element: SVGGraphicsElement) {
  const bounds = element.getBBox();
  const matrix = element.getCTM();
  return matrix ? boundsInMatrix(bounds, matrix) : bounds;
}

export function assertFinancialPlotUnclipped(plot: FinancialBounds, clip: FinancialBounds, line: FinancialBounds): void {
  const tolerance = 0.1; // SVG 包围盒使用浮点数；允许亚像素舍入，不允许整体位移错位。
  const details = () => `绘图区=${JSON.stringify(plot)}，裁剪=${JSON.stringify(clip)}，历史折线=${JSON.stringify(line)}`;
  if (Math.abs(plot.x - clip.x) > tolerance || Math.abs(plot.y - clip.y) > tolerance
    || Math.abs(plot.width - clip.width) > tolerance || Math.abs(plot.height - clip.height) > tolerance) {
    throw new Error(`金融折线裁剪区域与绘图区错位：${details()}`);
  }
  if (line.x < clip.x - tolerance || line.y < clip.y - tolerance
    || line.x + line.width > clip.x + clip.width + tolerance
    || line.y + line.height > clip.y + clip.height + tolerance) {
    throw new Error(`金融历史折线超出有效裁剪范围：${details()}`);
  }
}

/** 主曲线采样：每个自然月保留最后一个真实收盘点，首末点天然落在采样中。 */
export function trendPoints(points: PricePoint[]): PricePoint[] {
  if (points.length <= 2) return points;
  const sampled: PricePoint[] = [];
  let month = '';
  for (const point of points) {
    const current = point.date.slice(0, 7);
    if (current !== month) {
      sampled.push(point);
      month = current;
    } else {
      sampled[sampled.length - 1] = point;
    }
  }
  return sampled.length >= 2 ? sampled : points;
}

/** D3 单调曲线：不在相邻采样点之间过冲，业务取样与坐标口径仍由本类型负责。 */
export function monotoneCurvePath(points: ChartPoint[]): string {
  return chartLinePath(points.map(point => [point.x, point.y]), 'monotone');
}

export type ChartGeometry = {
  xForDate: (value: ISODate) => number;
  yForValue: (value: number) => number;
  chartPoints: ChartPoint[];
  linePoints: string;
  trendLinePoints: string;
  trendPath: string;
  areaPath: string;
  principalY: number | null;
  endpointX: number;
  endpointY: number;
};

/** 曲线与坐标求值：日期→横坐标、数值→纵坐标、主曲线与日线点串、端点与本金基线。 */
export function chartGeometry(view: FinancialView, minValue: number, maxValue: number, principal?: number): ChartGeometry {
  const dateSpan = Math.max(view.windowEndPosition - view.windowPosition, 1);
  const xForDate = (value: ISODate) => PLOT.left + ((epochDay(value) - view.windowPosition) / dateSpan) * (PLOT.right - PLOT.left);
  const yForValue = (value: number) => PLOT.bottom - ((value - minValue) / (maxValue - minValue)) * (PLOT.bottom - PLOT.top);
  const chartPoints = view.linePoints.map((point) => ({ x: xForDate(point.date), y: yForValue(point.close) }));
  const trendChartPoints = trendPoints(view.linePoints).map((point) => ({ x: xForDate(point.date), y: yForValue(point.close) }));
  const linePoints = chartPoints.map((point) => `${point.x},${point.y}`).join(' ');
  const trendLinePoints = trendChartPoints.map((point) => `${point.x},${point.y}`).join(' ');
  const trendPath = monotoneCurvePath(trendChartPoints);
  const areaPath = trendPath && trendChartPoints.length > 1
    ? `${trendPath} L ${trendChartPoints.at(-1)!.x},${PLOT.bottom} L ${trendChartPoints[0]!.x},${PLOT.bottom} Z` : '';
  const principalY = principal !== undefined && principal > minValue && principal < maxValue ? yForValue(principal) : null;
  const endpointX = view.latest ? xForDate(view.latest.date) : PLOT.left;
  const endpointY = view.latest ? yForValue(view.latest.close) : PLOT.bottom;
  return { xForDate, yForValue, chartPoints, linePoints, trendLinePoints, trendPath, areaPath, principalY, endpointX, endpointY };
}

/** 折线裁剪校验：裁剪区域必须与绘图区重合，且历史折线不得越界。
 *
 * 只检查真实日线 polyline：主曲线是它的按月采样加单调插值，采样点与日线共用坐标，
 * 曲线本身不出相邻采样点范围；而 path 的 bbox 会把贝塞尔控制点算进去，用于裁剪判定会误报。
 */
export function assertChartPlotUnclipped(svg: SVGSVGElement, contentLayer: SVGGElement): void {
  const polyline = svg.querySelector<SVGPolylineElement>('[data-m2v-visible-value-points]');
  if (polyline) {
    const clipRect = svg.querySelector<SVGRectElement>('#financial-plot rect');
    const clipReference = polyline.parentNode;
    const clipReferenceMatrix = clipReference instanceof SVGGraphicsElement ? clipReference.getCTM() : null;
    const clipDefinitionMatrix = clipRect?.getCTM();
    const svgMatrix = svg.getCTM();
    const contentMatrix = contentLayer.getCTM();
    if (!clipRect || !clipReferenceMatrix || !clipDefinitionMatrix || !svgMatrix || !contentMatrix
      || clipRect.parentElement?.getAttribute('clipPathUnits') !== 'userSpaceOnUse') {
      throw new Error('金融折线缺少有效的 userSpaceOnUse 裁剪区域或坐标变换');
    }
    // userSpaceOnUse 使用引用组的坐标系。先移除 defs 的 SVG 根变换，
    // 再接入引用组变换，得到包含裁剪定义自身变换的真正有效裁剪边界。
    const effectiveClipMatrix = clipReferenceMatrix.multiply(svgMatrix.inverse()).multiply(clipDefinitionMatrix);
    // getBBox 返回未经裁剪的全部历史几何边界，既检查当前端点也检查历史峰谷。
    assertFinancialPlotUnclipped(
      boundsInMatrix({ x: PLOT.left, y: PLOT.top, width: PLOT.right - PLOT.left, height: PLOT.bottom - PLOT.top }, contentMatrix),
      boundsInMatrix(clipRect.getBBox(), effectiveClipMatrix),
      transformedBounds(polyline),
    );
  }
}

/** 曲线端点必须绘制在完整历史折线上方。 */
export function assertEndpointAboveLine(svg: SVGSVGElement): void {
  const polyline = svg.querySelector<SVGPolylineElement>('[data-m2v-visible-value-points]');
  const endpoint = svg.querySelector<SVGCircleElement>('[data-m2v-financial-endpoint="true"]');
  if (endpoint && polyline && !(polyline.compareDocumentPosition(endpoint) & Node.DOCUMENT_POSITION_FOLLOWING)) {
    throw new Error('金融曲线端点必须绘制在完整历史折线上方');
  }
}
