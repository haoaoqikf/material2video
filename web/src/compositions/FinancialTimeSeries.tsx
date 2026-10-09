import { useLayoutEffect } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';

type ISODate = string;
type PricePoint = { date: ISODate; close: number };
type TimelineSegment = { frames: [number, number]; dates: [ISODate, ISODate]; kind: 'opening' | 'advance' | 'ending' };
export type FinancialPlan = {
  schemaVersion: 5; chartType: 'line';
  durationSeconds: number; fps: 30; canvas: { width: 1920; height: 1080 };
  axis: { dateRange: [ISODate, ISODate]; dateScale: 'full-range'; valueScale: 'revealed-linear' };
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

function dateTicks(start: number, end: number): ISODate[] {
  // Keep tick density bounded even when the final viewport spans decades.
  const span = end - start;
  const ticks: ISODate[] = [];
  const year = new Date(start * DAY_MS).getUTCFullYear();
  if (span > 730) {
    const step = Math.max(1, Math.ceil(span / 365.25 / 7));
    for (let value = Math.ceil(year / step) * step; epochDay(`${value}-01-01`) <= end; value += step) {
      const tick = `${value}-01-01`;
      if (epochDay(tick) >= start) ticks.push(tick);
    }
  } else {
    const date = new Date(start * DAY_MS);
    const step = Math.max(1, Math.ceil(span / 30 / 7));
    let next = Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 1) / DAY_MS;
    while (next < end) {
      ticks.push(isoDay(next));
      const tick = new Date(next * DAY_MS);
      next = Date.UTC(tick.getUTCFullYear(), tick.getUTCMonth() + step, 1) / DAY_MS;
    }
  }
  return ticks;
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
  const windowEndPosition = epochDay(plan.axis.dateRange[1]);
  const end = lastPointIndex(points, currentDate) + 1;
  const ranges = rangesFor(points);
  const target = ranges[end - 1] ?? [0, 1];
  let low = 0; let high = 0; let weightTotal = 0;
  // Freeze the last advance frame's axis for the entire four-second ending.
  const endingStart = plan.segments.find((segment) => segment.kind === 'ending')!.frames[0];
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
    windowStart: plan.axis.dateRange[0], windowEnd: plan.axis.dateRange[1],
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
  const { currentDate, windowStart, latest, visiblePoints, minValue, maxValue } = view;
  const [rangeStart, rangeEnd] = plan.axis.dateRange;
  const dateSpan = Math.max(view.windowEndPosition - view.windowPosition, 1);
  const xForDate = (value: ISODate) => PLOT.left + ((epochDay(value) - view.windowPosition) / dateSpan) * (PLOT.right - PLOT.left);
  const tickDecimals = valueTickDecimals(minValue, maxValue);
  const yForValue = (value: number) => PLOT.bottom - ((value - minValue) / (maxValue - minValue)) * (PLOT.bottom - PLOT.top);
  const linePoints = view.linePoints.map((point) => `${xForDate(point.date)},${yForValue(point.close)}`).join(' ');
  const ticks = dateTicks(view.windowPosition, view.windowEndPosition);
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
      {ticks.map((tickDate) => {
        const x = xForDate(tickDate);
        return <g key={`month-${tickDate}`}><line x1={x} x2={x} y1={PLOT.top} y2={PLOT.bottom} stroke="#172235" /><text x={x} y={PLOT.bottom + 40} textAnchor="middle" fill="#9ba9bc" fontSize="18">{view.windowEndPosition - view.windowPosition > 730 ? tickDate.slice(0, 4) : tickDate.slice(0, 7)}</text></g>;
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
      <text x={PLOT.right} y="872" textAnchor="end" fill="#76859b" fontSize="16">完整年份 · 纵轴随已展示价格自适应</text>
      {!latest && <text x={(PLOT.left + PLOT.right) / 2} y="520" textAnchor="middle" fill="#a8b4c5" fontSize="24">尚无区间内有效收盘数据</text>}
      <text x={PLOT.left} y="1044" fill="#76859b" fontSize="15">日期与价格按来源核实；休市期间不生成新的报价点。</text>
    </svg>
  </AbsoluteFill>;
}
