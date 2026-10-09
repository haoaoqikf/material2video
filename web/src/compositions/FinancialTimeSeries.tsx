import { useLayoutEffect } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';

type ISODate = string;
type PricePoint = { date: ISODate; close: number };
type TimelineSegment = { frames: [number, number]; dates: [ISODate, ISODate]; kind: 'opening' | 'advance' | 'ending' };
export type FinancialPlan = {
  schemaVersion: 6; chartType: 'line';
  durationSeconds: number; fps: 30; canvas: { width: 1920; height: 1080 };
  axis: { dateRange: [ISODate, ISODate]; dateScale: 'staged-expanding'; valueScale: 'revealed-linear' };
  segments: TimelineSegment[];
  rationale: string;
};
export type FinancialTimeSeriesProps = {
  request: { instrument: { kind: 'stock' | 'index'; name: string; code: string; market: string; unit: string }; displayRange: [ISODate, ISODate] };
  prices: { schemaVersion: 3; points: PricePoint[]; unit: string; priceBasis: string; adjustmentDefinition?: string; indexType?: string; sources: unknown[] };
  plan: FinancialPlan;
  durationInFrames: number; fps: 30; width: 1920; height: 1080;
};

const WIDTH = 1920;
const HEIGHT = 1080;
const PLOT = { left: 156, right: 1768, top: 250, bottom: 790 };
const DAY_MS = 86_400_000;

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

function axisTicks(frame: number, windowStart: number, windowEnd: number, transitions: AxisTransition[], endingStart: number) {
  if (frame >= endingStart) {
    const finalEnd = transitions.at(-1)?.target ?? windowEnd;
    const interval = tickInterval(windowStart, finalEnd);
    return ticksForInterval(windowStart, windowEnd, interval).map((date) => ({ date, label: interval.unit === 'year' ? date.slice(0, 4) : date.slice(0, 7), opacity: 1 }));
  }
  const finalTransition = transitions.at(-1);
  if (finalTransition && frame >= endingStart - 6 && finalTransition.end >= endingStart - 1) {
    const progress = Math.max(0, Math.min(1, (frame - (endingStart - 6)) / 5));
    const oldInterval = tickInterval(windowStart, finalTransition.oldEnd);
    const nextInterval = tickInterval(windowStart, finalTransition.target);
    const labels = new Map<ISODate, { label: string; opacity: number }>();
    ticksForInterval(windowStart, finalTransition.oldEnd, oldInterval).forEach((date) =>
      labels.set(date, { label: oldInterval.unit === 'year' ? date.slice(0, 4) : date.slice(0, 7), opacity: 1 - progress }));
    ticksForInterval(windowStart, finalTransition.target, nextInterval).forEach((date) => {
      const prior = labels.get(date);
      labels.set(date, { label: nextInterval.unit === 'year' ? date.slice(0, 4) : date.slice(0, 7), opacity: Math.max(prior?.opacity ?? 0, progress) });
    });
    return [...labels].map(([date, { label, opacity }]) => ({ date, label, opacity })).filter(({ opacity }) => opacity > 0);
  }
  const active = transitions.find(({ start, end }) => start <= frame && frame <= end);
  if (active) {
    const oldInterval = tickInterval(windowStart, active.oldEnd);
    const nextInterval = tickInterval(windowStart, active.target);
    const oldTicks = ticksForInterval(windowStart, windowEnd, oldInterval);
    const oldSet = new Set(oldTicks);
    const nextTicks = ticksForInterval(windowStart, windowEnd, nextInterval).filter((tick) => !oldSet.has(tick));
    return [
      ...oldTicks.map((date) => ({ date, label: oldInterval.unit === 'year' ? date.slice(0, 4) : date.slice(0, 7), opacity: 1 })),
      ...nextTicks.map((date) => {
        const distance = windowEnd - epochDay(date);
        return { date, label: nextInterval.unit === 'year' ? date.slice(0, 4) : date.slice(0, 7), opacity: Math.max(0, Math.min(1, 1 - distance / Math.max((windowEnd - active.oldEnd) * 0.12, 1))) };
      }).filter(({ opacity }) => opacity > 0),
    ];
  }
  const previous = [...transitions].reverse().find(({ end }) => end < frame && frame - end <= 6);
  if (previous) {
    const progress = (frame - previous.end) / 6;
    const oldTicks = ticksForInterval(windowStart, previous.oldEnd, tickInterval(windowStart, previous.oldEnd));
    const nextTicks = ticksForInterval(windowStart, previous.target, tickInterval(windowStart, previous.target));
    const opacities = new Map<ISODate, { opacity: number; label: string }>();
    oldTicks.forEach((date) => opacities.set(date, { label: previous.oldEnd - windowStart > 730 ? date.slice(0, 4) : date.slice(0, 7), opacity: 1 - progress }));
    nextTicks.forEach((date) => {
      const existing = opacities.get(date);
      opacities.set(date, { label: previous.target - windowStart > 730 ? date.slice(0, 4) : date.slice(0, 7), opacity: Math.max(existing?.opacity ?? 0, progress) });
    });
    return [...opacities].map(([date, { opacity, label }]) => ({ date, label, opacity })).filter(({ opacity }) => opacity > 0);
  }
  const interval = tickInterval(windowStart, windowEnd);
  return ticksForInterval(windowStart, windowEnd, interval).map((date) => ({ date, label: interval.unit === 'year' ? date.slice(0, 4) : date.slice(0, 7), opacity: 1 }));
}

// Prefix ranges avoid scanning decades of daily prices six times per frame.
// Inputs are immutable render props; the cache stores no frame-dependent state.
const prefixRanges = new WeakMap<PricePoint[], [number, number][]>();
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

export function financialView(frame: number, points: PricePoint[], plan: FinancialPlan) {
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
  const end = lastPointIndex(points, currentDate) + 1;
  const ranges = rangesFor(points);
  const target = ranges[end - 1] ?? [0, 1];
  let low = 0; let high = 0; let weightTotal = 0;
  // Freeze the last advance frame's axis for the entire four-second ending.
  const axisTicksForFrame = axisTicks(frame, windowPosition, windowEndPosition, transitions, endingStart);
  const axisFrame = Math.min(frame, endingStart - 1);
  for (let offset = 0; offset < 6; offset++) {
    const date = isoDay(Math.floor(framePosition(Math.max(0, axisFrame - offset), plan)));
    const range = ranges[lastPointIndex(points, date)];
    if (!range) continue;
    const weight = 6 - offset;
    low += range[0] * weight; high += range[1] * weight; weightTotal += weight;
  }
  // Never crop a newly arrived extreme while smoothing a contracting bound.
  low = weightTotal ? Math.min(target[0], low / weightTotal) : target[0];
  high = weightTotal ? Math.max(target[1], high / weightTotal) : target[1];
  const visiblePoints = points.slice(0, end);
  return { currentDate, position, windowPosition, windowEndPosition,
    windowStart: plan.axis.dateRange[0], windowEnd: plan.axis.dateRange[1], ticks: axisTicksForFrame,
    minValue: low, maxValue: high, visiblePoints, linePoints: visiblePoints,
    latest: end > 0 ? points[end - 1]! : null };
}

function priceText(value: number, unit: string): string {
  const decimals = value >= 1000 ? 0 : value >= 1 ? 2 : 4;
  return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: decimals }).format(value)} ${unit}`;
}

function dateText(value: ISODate): string {
  return new Intl.DateTimeFormat('zh-CN', { timeZone: 'UTC', year: 'numeric', month: 'long', day: 'numeric' })
    .format(new Date(`${value}T00:00:00Z`));
}

export function FinancialTimeSeries(props: FinancialTimeSeriesProps) {
  const frame = useCurrentFrame();
  const { request, prices, plan } = props;
  const view = financialView(frame, prices.points, plan);
  const { currentDate, windowStart, latest, visiblePoints, minValue, maxValue, ticks } = view;
  const [rangeStart, rangeEnd] = plan.axis.dateRange;
  const dateSpan = Math.max(view.windowEndPosition - view.windowPosition, 1);
  const xForDate = (value: ISODate) => PLOT.left + ((epochDay(value) - view.windowPosition) / dateSpan) * (PLOT.right - PLOT.left);
  const tickDecimals = valueTickDecimals(minValue, maxValue);
  const yForValue = (value: number) => PLOT.bottom - ((value - minValue) / (maxValue - minValue)) * (PLOT.bottom - PLOT.top);
  const linePoints = view.linePoints.map((point) => `${xForDate(point.date)},${yForValue(point.close)}`).join(' ');
  const sourceSummary = prices.sources.map((source) => {
    if (typeof source === 'object' && source !== null && 'url' in source && typeof source.url === 'string') return new URL(source.url).hostname;
    return '公开资料';
  }).filter((source, index, all) => all.indexOf(source) === index).join(' / ');

  useLayoutEffect(() => {
    document.documentElement.style.setProperty('--a2v-width', `${WIDTH}px`);
    document.documentElement.style.setProperty('--a2v-height', `${HEIGHT}px`);
    document.documentElement.dataset.a2vTheme = 'dark';
  }, []);

  return <AbsoluteFill style={{ background: '#080d17', color: '#eef4fc', fontFamily: 'Inter, "Noto Sans SC", sans-serif' }} data-a2v-financial="line">
    <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" data-a2v-financial="line" aria-label={`${request.instrument.name} 全日期范围价格演变图`} data-a2v-window-start={windowStart} data-a2v-window-end={view.windowEnd} data-a2v-current-date={currentDate}>
      <defs><clipPath id="financial-plot"><rect x={PLOT.left} y={PLOT.top} width={PLOT.right - PLOT.left} height={PLOT.bottom - PLOT.top} /></clipPath></defs>
      <text x={PLOT.left} y="96" fill="#f6f8fc" fontSize="48" fontWeight="700">{request.instrument.name} · {request.instrument.code}</text>
      <text x={PLOT.left} y="146" fill="#97a7bd" fontSize="23">{rangeStart} — {rangeEnd}　{prices.priceBasis === 'official-index-points' ? prices.indexType : '仅拆合股调整 · 不含分红再投资'}</text>
      <text x={PLOT.left} y="184" fill="#8292a9" fontSize="18">市场 {request.instrument.market} · 单位 {prices.unit} · 来源：{sourceSummary}</text>
      {Array.from({ length: 5 }, (_, index) => {
        const value = minValue + ((maxValue - minValue) * index) / 4;
        const y = yForValue(value);
        return <g key={`grid-${index}`}>
          <line x1={PLOT.left} x2={PLOT.right} y1={y} y2={y} stroke="#253247" strokeWidth="1" />
          <text x={PLOT.left - 18} y={y + 7} textAnchor="end" fill="#8b9ab0" fontSize="18">{new Intl.NumberFormat('en-US', { maximumFractionDigits: tickDecimals }).format(value)}</text>
        </g>;
      })}
      {ticks.map(({ date: tickDate, label, opacity }) => {
        const x = xForDate(tickDate);
        return <g key={`month-${tickDate}`} opacity={opacity}><line x1={x} x2={x} y1={PLOT.top} y2={PLOT.bottom} stroke="#172235" /><text x={x} y={PLOT.bottom + 40} textAnchor="middle" fill="#9ba9bc" fontSize="18">{label}</text></g>;
      })}
      <line x1={PLOT.left} x2={PLOT.left} y1={PLOT.top} y2={PLOT.bottom} stroke="#53627a" />
      <line x1={PLOT.left} x2={PLOT.right} y1={PLOT.bottom} y2={PLOT.bottom} stroke="#53627a" />
      {view.linePoints.length > 0 && <g clipPath="url(#financial-plot)">
        <polyline fill="none" stroke="#6ab6ff" strokeWidth="5" strokeLinejoin="round" strokeLinecap="round"
          points={linePoints} data-a2v-visible-price-points={visiblePoints.length} />
      </g>}
      {latest && <g>
        {windowStart <= latest.date && <circle cx={xForDate(latest.date)} cy={yForValue(latest.close)} r="9" fill="#9bd0ff" stroke="#09213a" strokeWidth="4" />}
        <text x={PLOT.right} y="150" textAnchor="end" fill="#e8f3ff" fontSize="27" fontWeight="600">{priceText(latest.close, prices.unit)}</text>
        <text x={PLOT.right} y="185" textAnchor="end" fill="#98aac1" fontSize="18">最近有效收盘 {latest.date}</text>
      </g>}
      <text x={PLOT.left} y="872" fill="#d8e1ed" fontSize="24" fontWeight="600">{dateText(currentDate)}</text>
      <text x={PLOT.right} y="872" textAnchor="end" fill="#76859b" fontSize="16">横轴分阶段扩展 · 纵轴随已展示价格自适应</text>
      {!latest && <text x={(PLOT.left + PLOT.right) / 2} y="520" textAnchor="middle" fill="#a8b4c5" fontSize="24">尚无区间内有效收盘数据</text>}
      <text x={PLOT.left} y="1044" fill="#76859b" fontSize="15">日期与价格按来源核实；休市期间不生成新的报价点。</text>
    </svg>
  </AbsoluteFill>;
}
