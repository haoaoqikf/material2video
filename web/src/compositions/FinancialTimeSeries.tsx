import { useLayoutEffect, useRef } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';

type ISODate = string;
type PricePoint = { date: ISODate; close: number };
type TimelineSegment = { frames: [number, number]; dates: [ISODate, ISODate]; kind: 'opening' | 'advance' | 'ending' };
export type FinancialPlan = {
  schemaVersion: 7; chartType: 'line';
  durationSeconds: number; fps: 30; canvas: { width: 1080; height: 1920 };
  axis: { dateRange: [ISODate, ISODate]; dateScale: 'staged-expanding'; valueScale: 'revealed-linear' };
  segments: TimelineSegment[];
  rationale: string;
};
export type FinancialTimeSeriesProps = {
  request: { instrument: { kind: 'stock' | 'index'; name: string; displayName?: string; code: string; market: string; unit: string }; displayRange: [ISODate, ISODate]; investment?: { year: number; principal: number } };
  prices: { schemaVersion: 3; points: PricePoint[]; unit: string; priceBasis: string; adjustmentDefinition?: string; indexType?: string; sources: unknown[] };
  plan: FinancialPlan;
  durationInFrames: number; fps: 30; width: 1080; height: 1920;
};

const WIDTH = 1080;
const HEIGHT = 1920;
const PLOT = { left: 92, right: 1008, top: 520, bottom: 1190 };
const DAY_MS = 86_400_000;
const PROFIT_COLOR = '#ff5d68';
const LOSS_COLOR = '#55d58a';
const SAFE_AREA = { left: 64, right: 1016, top: 180, bottom: 1500 };
const VALUE_AXIS_SAFE_AREA = { left: 24, right: 1016, top: 180, bottom: 1500 };

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
  const [startFrame, endFrame] = segment.frames;
  return epochDay(startDate) + ((frame - startFrame) * (epochDay(endDate) - epochDay(startDate))) / (endFrame - startFrame - 1);
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

function axisTransitions(plan: FinancialPlan): AxisTransition[] {
  const [startDate, endDate] = plan.axis.dateRange;
  const start = epochDay(startDate);
  const end = epochDay(endDate);
  const boundaries = annualBoundaries(start, end);
  if (boundaries.length <= 1) return [];
  const advance = plan.segments.find(({ kind }) => kind === 'advance')!;
  const [advanceStart, advanceEnd] = advance.frames;
  const [advanceDateStart, advanceDateEnd] = advance.dates.map(epochDay) as [number, number];
  const dateAt = (frame: number) => advanceDateStart + ((frame - advanceStart) * (advanceDateEnd - advanceDateStart)) / (advanceEnd - advanceStart - 1);
  const candidates: AxisTransition[] = [];
  let oldEnd = boundaries[0]!;
  for (const target of boundaries.slice(1)) {
    let low = advanceStart; let high = advanceEnd;
    while (low < high) {
      const mid = (low + high) >>> 1;
      if (dateAt(mid) > target) high = mid;
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

export function financialView(frame: number, points: PricePoint[], plan: FinancialPlan, investment?: { year: number; principal: number }) {
  const position = framePosition(frame, plan);
  const currentDate = isoDay(Math.floor(position));
  const windowPosition = epochDay(plan.axis.dateRange[0]);
  const fullRangeEnd = epochDay(plan.axis.dateRange[1]);
  const transitions = axisTransitions(plan);
  let windowEndPosition = annualBoundaries(windowPosition, fullRangeEnd)[0]!;
  for (const transition of transitions) {
    if (frame < transition.start) break;
    const progress = Math.max(0, Math.min(1, (frame - transition.start) / Math.max(transition.end - transition.start, 1)));
    const eased = progress * progress * (3 - 2 * progress);
    windowEndPosition = Math.max(windowEndPosition, transition.oldEnd + (transition.target - transition.oldEnd) * eased);
    if (frame >= transition.end) windowEndPosition = Math.max(windowEndPosition, transition.target);
  }
  windowEndPosition = Math.min(fullRangeEnd, Math.max(windowEndPosition, position));
  const endingStart = plan.segments.find((segment) => segment.kind === 'ending')!.frames[0];
  if (frame >= endingStart - 1) windowEndPosition = fullRangeEnd;
  const config = investment ?? { year: Number(plan.axis.dateRange[0].slice(0, 4)), principal: 1_000_000 };
  const series = investmentSeries(points, config.year, config.principal);
  const valuePoints = series?.points ?? [];
  const end = lastPointIndex(valuePoints, currentDate) + 1;
  const ranges = rangesFor(valuePoints);
  const target = ranges[end - 1] ?? [0, 1];
  let low = 0; let high = 0; let weightTotal = 0;
  // Freeze the last advance frame's axis for the entire four-second ending.
  const rawTicks = axisTicks(windowPosition, windowEndPosition, fullRangeEnd);
  const axisWidth = PLOT.right - PLOT.left;
  const positioned = rawTicks.filter((tick) => epochDay(tick.date) <= windowEndPosition).map((tick) => {
    const width = tick.label.length * 18;
    const x = PLOT.left + ((epochDay(tick.date) - windowPosition) / Math.max(windowEndPosition - windowPosition, 1)) * axisWidth;
    return { ...tick, x: Math.max(PLOT.left, Math.min(x, PLOT.right - width / 2)), width };
  });
  const visibleAxisTicks = positioned.sort((a, b) => a.x - b.x);
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

function magnitude(value: number): { value: number; unit: string } {
  const rounded = Math.sign(value) * (Math.round(Math.abs(value) * 100) / 100);
  const absolute = Math.abs(rounded);
  if (absolute >= 1_000_000_000_000) return { value: rounded / 1_000_000_000_000, unit: '万亿' };
  if (absolute >= 100_000_000) return { value: rounded / 100_000_000, unit: '亿' };
  if (absolute >= 10_000) return { value: rounded / 10_000, unit: '万' };
  return { value: rounded, unit: '' };
}

function magnitudeNumber(value: number): string {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(value);
}

function investmentAmountText(value: number): string {
  const scaled = magnitude(value);
  return `${magnitudeNumber(scaled.value)}${scaled.unit}`;
}

function moneyText(value: number): string {
  const scaled = magnitude(value);
  const amount = scaled.unit ? `${magnitudeNumber(scaled.value)} ${scaled.unit}` : magnitudeNumber(scaled.value);
  return `${amount}元`;
}

function compactValue(value: number): string {
  const scaled = magnitude(value);
  return `${new Intl.NumberFormat('zh-CN', { maximumSignificantDigits: 3 }).format(scaled.value)}${scaled.unit}`;
}

function displayDate(value: ISODate): string {
  const [year, month, day] = value.split('-');
  return `${year}年${Number(month)}月${Number(day)}日`;
}

function measuredTextWidth(value: string, fontSize: number): number {
  return [...value].reduce((width, char) => width + (/[^\u0000-\u00ff]/u.test(char) ? fontSize : fontSize * 0.56), 0);
}

function wrapSvgText(value: string, maxWidth: number, fontSize: number): string[] {
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

export function FinancialTimeSeries(props: FinancialTimeSeriesProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const frame = useCurrentFrame();
  const { request, prices, plan } = props;
  const investment = request.investment ?? { year: Number(request.displayRange[0].slice(0, 4)), principal: 1_000_000 };
  const view = financialView(frame, prices.points, plan, investment);
  const { windowStart, latest, visiblePoints, minValue, maxValue, ticks } = view;
  const displayName = request.instrument.displayName ?? request.instrument.name;
  const investmentAmount = investmentAmountText(investment.principal);
  const title = request.instrument.kind === 'index'
    ? `假如你在${investment.year}年按比例投资${displayName}，投入${investmentAmount}`
    : `假如你在${investment.year}年买入${displayName}，投入${investmentAmount}`;
  const titleWidth = SAFE_AREA.right - SAFE_AREA.left;
  const titleFontSize = Math.min(48, (titleWidth / measuredTextWidth(title, 48)) * 48);
  if (titleFontSize < 26) throw new Error('投资假设标题过长，无法在安全区内保持可读的单行字号');
  const graphTop = 520;
  const gainColor = view.gain !== null && view.gain > 0 ? PROFIT_COLOR : LOSS_COLOR;
  const gainSign = view.gain !== null && view.gain > 0 ? '+' : view.gain !== null && view.gain < 0 ? '−' : '';
  const rateSign = view.returnRate !== null && view.returnRate > 0 ? '+' : view.returnRate !== null && view.returnRate < 0 ? '−' : '';
  const liveGain = latest ? `收益 ${gainSign}${moneyText(Math.abs(view.gain!))}` : '';
  const liveRate = latest
    ? `收益率 ${rateSign}${new Intl.NumberFormat('zh-CN', { style: 'percent', maximumFractionDigits: 2 }).format(Math.abs(view.returnRate!))}`
    : '';
  const liveDate = latest ? displayDate(latest.date) : '';
  const dateSpan = Math.max(view.windowEndPosition - view.windowPosition, 1);
  const xForDate = (value: ISODate) => PLOT.left + ((epochDay(value) - view.windowPosition) / dateSpan) * (PLOT.right - PLOT.left);
  const yForValue = (value: number) => PLOT.bottom - ((value - minValue) / (maxValue - minValue)) * (PLOT.bottom - graphTop);
  const linePoints = view.linePoints.map((point) => `${xForDate(point.date)},${yForValue(point.close)}`).join(' ');
  const endpointLabel = latest ? moneyText(latest.close) : '';
  const endpointX = latest ? xForDate(latest.date) : PLOT.left;
  const endpointY = latest ? yForValue(latest.close) : PLOT.bottom;
  const endpointLabelWidth = measuredTextWidth(endpointLabel, 24) * 1.15;
  const endpointLabelX = Math.max(SAFE_AREA.left, Math.min(endpointX + 14, SAFE_AREA.right - endpointLabelWidth));
  const endpointLabelY = latest && endpointY > graphTop + (PLOT.bottom - graphTop) * 0.35
    ? Math.min(PLOT.bottom - 14, endpointY + 58)
    : Math.max(graphTop + 36, endpointY - 34);
  const sourceHosts = prices.sources.map((source) => {
    if (typeof source === 'object' && source !== null && 'url' in source && typeof source.url === 'string') return new URL(source.url).hostname;
    return '公开资料';
  }).filter((source, index, all) => all.indexOf(source) === index);
  const summaryText = [
    `来源 ${sourceHosts.join(' / ')}`,
    `${prices.priceBasis === 'official-index-points' ? `指数类型 ${prices.indexType}；按点位比例模拟，不代表指数可直接持有` : '仅拆合股调整，不计分红再投资'}；按比例持仓，不计手续费及税费`,
  ];
  const summaryLines = summaryText.flatMap((line) => wrapSvgText(line, SAFE_AREA.right - SAFE_AREA.left, 24));
  if (summaryLines.length > 4) throw new Error('来源和统计口径超出说明区域四行容量');

  useLayoutEffect(() => {
    document.documentElement.style.setProperty('--a2v-width', `${WIDTH}px`);
    document.documentElement.style.setProperty('--a2v-height', `${HEIGHT}px`);
    document.documentElement.dataset.a2vTheme = 'dark';
    if (frame % 5 !== 0 && frame !== props.durationInFrames - 1) return;
    const svg = svgRef.current;
    if (!svg) return;
    for (const element of svg.querySelectorAll('text')) {
      const bounds = element.getBBox();
      const safeArea = element.hasAttribute('data-a2v-value-axis-label') ? VALUE_AXIS_SAFE_AREA : SAFE_AREA;
      if (bounds.x < safeArea.left || bounds.x + bounds.width > safeArea.right || bounds.y < safeArea.top || bounds.y + bounds.height > safeArea.bottom) {
        throw new Error(`金融画面文字超出手机安全区：${element.textContent ?? ''}（${bounds.x},${bounds.y},${bounds.width},${bounds.height}）`);
      }
    }
    const labelBounds = [...svg.querySelectorAll<SVGTextElement>('[data-a2v-axis-label="true"]')]
      .map((element) => element.getBBox()).sort((a, b) => a.x - b.x);
    for (let index = 1; index < labelBounds.length; index++) {
      if (labelBounds[index]!.x - (labelBounds[index - 1]!.x + labelBounds[index - 1]!.width) < 12) {
        throw new Error('金融画面横轴标签实际字体边界发生重叠');
      }
    }
    for (const endpoint of svg.querySelectorAll<SVGCircleElement>('circle')) {
      const x = Number(endpoint.getAttribute('cx'));
      const y = Number(endpoint.getAttribute('cy'));
      const radius = Number(endpoint.getAttribute('r'));
      if (x - radius < SAFE_AREA.left || x + radius > SAFE_AREA.right || y - radius < SAFE_AREA.top || y + radius > SAFE_AREA.bottom) {
        throw new Error('金融画面曲线端点超出手机安全区');
      }
    }
  }, [frame]);

  return <AbsoluteFill style={{ background: '#080d17', color: '#eef4fc', fontFamily: 'Inter, "Noto Sans SC", sans-serif' }} data-a2v-financial="line">
    <svg ref={svgRef} width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" data-a2v-financial="line" aria-label={`${displayName} 假设投资价值演变图`} data-a2v-window-start={windowStart} data-a2v-window-end={view.windowEnd}>
      <defs><clipPath id="financial-plot"><rect x={PLOT.left} y={graphTop} width={PLOT.right - PLOT.left} height={PLOT.bottom - graphTop} /></clipPath></defs>
      <text data-a2v-investment-title="true" x={SAFE_AREA.left} y="270" textLength={titleWidth} lengthAdjust="spacing" fill="#f6f8fc" fontSize={titleFontSize} fontWeight="700">{title}</text>
      {latest && <>
        <text data-a2v-live-date="true" x={SAFE_AREA.right} y="350" textAnchor="end" fill="#b9c7d9" fontSize="24" fontWeight="500">{liveDate}</text>
        <text data-a2v-live-return="true" x={SAFE_AREA.right} y="390" textAnchor="end" fill={gainColor} fontSize="24" fontWeight="600">{liveRate}</text>
        <text data-a2v-live-gain="true" x={SAFE_AREA.right} y="430" textAnchor="end" fill={gainColor} fontSize="24" fontWeight="650">{liveGain}</text>
      </>}
      {Array.from({ length: 5 }, (_, index) => {
        const value = minValue + ((maxValue - minValue) * index) / 4;
        const y = yForValue(value);
        const label = compactValue(value);
        const labelWidth = PLOT.left - 14 - VALUE_AXIS_SAFE_AREA.left;
        const estimatedLabelWidth = measuredTextWidth(label, 14);
        return <g key={`grid-${index}`}>
          <line x1={PLOT.left} x2={PLOT.right} y1={y} y2={y} stroke="#253247" strokeWidth="1" />
          <text data-a2v-value-axis-label="true" x={PLOT.left - 14} y={y + 9} textAnchor="end" fill="#8b9ab0" fontSize="14"
            textLength={estimatedLabelWidth > labelWidth ? labelWidth : undefined}
            lengthAdjust={estimatedLabelWidth > labelWidth ? 'spacingAndGlyphs' : undefined}>{label}</text>
        </g>;
      })}
      {ticks.map(({ date: tickDate, label, opacity }) => {
        const x = xForDate(tickDate);
        const labelHalfWidth = label.length * 9;
        const labelX = Math.max(SAFE_AREA.left + labelHalfWidth, Math.min(x, SAFE_AREA.right - labelHalfWidth));
        return <g key={`month-${tickDate}`} opacity={opacity}><line x1={x} x2={x} y1={graphTop} y2={PLOT.bottom} stroke="#172235" /><text data-a2v-axis-label="true" x={labelX} y={PLOT.bottom + 46} textAnchor="middle" fill="#9ba9bc" fontSize="30">{label}</text></g>;
      })}
      <line x1={PLOT.left} x2={PLOT.left} y1={graphTop} y2={PLOT.bottom} stroke="#53627a" />
      <line x1={PLOT.left} x2={PLOT.right} y1={PLOT.bottom} y2={PLOT.bottom} stroke="#53627a" />
      {view.linePoints.length > 0 && <g clipPath="url(#financial-plot)">
        <polyline fill="none" stroke={gainColor} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round"
          points={linePoints} data-a2v-visible-value-points={visiblePoints.length} />
      </g>}
      {latest && windowStart <= latest.date && <>
        <circle cx={endpointX} cy={endpointY} r="8" fill={gainColor} stroke="#09213a" strokeWidth="3" />
        <text data-a2v-current-value-follow="true" x={endpointLabelX} y={endpointLabelY} fill={gainColor} fontSize="24" fontWeight="700">{endpointLabel}</text>
      </>}
      {summaryLines.map((line, index) => <text data-a2v-summary="true" key={`summary-${index}`} x={SAFE_AREA.left} y={1320 + index * 32} fill="#b9c7d9" fontSize="24">{line}</text>)}
      <text data-a2v-risk-disclaimer="true" x={SAFE_AREA.left} y="1460" fill="#8b9ab0" fontSize="20">过往业绩不代表未来表现。本视频仅作信息展示，不构成投资建议。</text>
    </svg>
  </AbsoluteFill>;
}
