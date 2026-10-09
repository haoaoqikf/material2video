import { useLayoutEffect } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';

type ISODate = string;
type PricePoint = { date: ISODate; close: number };
type EventItem = { id: string; date: ISODate; title: string; sources: string[]; dateBasis: 'occurred' | 'announced' | 'reported'; reason: string };
type TimelineSegment = { frames: [number, number]; dates: [ISODate, ISODate]; kind: 'opening' | 'advance' | 'hold' | 'overview' | 'ending' };
export type FinancialPlan = {
  schemaVersion: 3; chartType: 'line';
  durationSeconds: number; fps: 30; canvas: { width: 1920; height: 1080 };
  axis: { dateRange: [ISODate, ISODate]; visibleWindowMonths: number; valueScale: 'rolling-linear' };
  segments: TimelineSegment[]; eventDisplays: Array<{ eventId: string; frames: [number, number] }>;
  rationale: string;
};
export type FinancialTimeSeriesProps = {
  request: { instrument: { kind: 'stock' | 'index'; name: string; code: string; market: string; unit: string }; displayRange: [ISODate, ISODate] };
  prices: { schemaVersion: 3; points: PricePoint[]; unit: string; priceBasis: string; adjustmentDefinition?: string; indexType?: string; sources: unknown[] };
  events: { selected: EventItem[] };
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

function fractionalWindowStart(position: number, months: number, dataStart: ISODate): number {
  const day = Math.floor(position);
  const start = epochDay(rollingWindowStart(isoDay(day), months, dataStart));
  const next = epochDay(rollingWindowStart(isoDay(day + 1), months, dataStart));
  return start + (next - start) * (position - day);
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

function lowerBound(points: PricePoint[], date: ISODate): number {
  let low = 0;
  let high = points.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (points[mid]!.date < date) low = mid + 1;
    else high = mid;
  }
  return low;
}

export function rollingWindowStart(endDate: ISODate, months: number, dataStart: ISODate): ISODate {
  const [year, month, day] = endDate.split('-').map(Number);
  const absoluteMonth = year! * 12 + month! - 1 - months;
  const targetYear = Math.floor(absoluteMonth / 12);
  const targetMonth = ((absoluteMonth % 12) + 12) % 12;
  const lastDay = new Date(Date.UTC(targetYear, targetMonth + 1, 0)).getUTCDate();
  const start = `${targetYear.toString().padStart(4, '0')}-${(targetMonth + 1).toString().padStart(2, '0')}-${Math.min(day!, lastDay).toString().padStart(2, '0')}`;
  return start < dataStart ? dataStart : start;
}

export function rollingValueRange(points: PricePoint[]): [number, number] {
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

export function rollingTickDecimals(minValue: number, maxValue: number): number {
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

function windowRange(points: PricePoint[], start: number, position: number): [number, number] {
  const first = lowerBound(points, isoDay(Math.ceil(start)));
  const end = lastPointIndex(points, isoDay(Math.floor(position))) + 1;
  const visible = points.slice(first, Math.max(first, end));
  if (first > 0 && first < end) {
    const previous = points[first - 1]!;
    const next = points[first]!;
    const progress = (start - epochDay(previous.date)) / (epochDay(next.date) - epochDay(previous.date));
    // The clipped line's boundary is geometry, never a displayed historical quote.
    // Including it keeps the scale continuous as older points enter the viewport.
    visible.push({ date: isoDay(Math.ceil(start)), close: previous.close + (next.close - previous.close) * progress });
  }
  return rollingValueRange(visible);
}

export function financialView(frame: number, points: PricePoint[], plan: FinancialPlan) {
  const position = framePosition(frame, plan);
  const currentDate = isoDay(Math.floor(position));
  const dataStart = plan.axis.dateRange[0];
  const rollingStart = fractionalWindowStart(position, plan.axis.visibleWindowMonths, dataStart);
  const target = windowRange(points, rollingStart, position);
  // A fixed causal lookback makes seeking and offline export identical. Newly
  // arrived extremes remain visible; history only slows contraction of the axis.
  let low = 0; let high = 0; let weightTotal = 0;
  for (let offset = 0; offset < 6; offset++) {
    const previous = framePosition(Math.max(0, frame - offset), plan);
    const range = windowRange(points, fractionalWindowStart(previous, plan.axis.visibleWindowMonths, dataStart), previous);
    const weight = 6 - offset;
    low += range[0] * weight; high += range[1] * weight; weightTotal += weight;
  }
  low = Math.min(target[0], low / weightTotal);
  high = Math.max(target[1], high / weightTotal);
  const overview = plan.segments.find((segment) => segment.kind === 'overview');
  const overviewStart = overview?.frames[0] ?? Infinity;
  const progress = overview ? Math.max(0, Math.min(1, (frame - overviewStart) / (overview.frames[1] - overviewStart - 1))) : 0;
  const blend = progress * progress * (3 - 2 * progress);
  if (frame >= overviewStart) {
    // Anchor to the last rolling frame: the start of the reveal has no axis jump.
    const before = financialView(overviewStart - 1, points, plan);
    const full = rollingValueRange(points);
    low = blend === 1 ? full[0] : before.minValue + (full[0] - before.minValue) * blend;
    high = blend === 1 ? full[1] : before.maxValue + (full[1] - before.maxValue) * blend;
  }
  const windowPosition = rollingStart + (epochDay(dataStart) - rollingStart) * blend;
  if (frame >= overviewStart) {
    const visibleRange = windowRange(points, windowPosition, position);
    // Linear interpolation of the start/end axes alone can clip older, lower
    // prices during the reveal. The visible envelope is the minimum safe range.
    low = Math.min(low, visibleRange[0]);
    high = Math.max(high, visibleRange[1]);
  }
  const first = lowerBound(points, isoDay(Math.ceil(windowPosition)));
  const end = lastPointIndex(points, currentDate) + 1;
  // One preceding real point gives the clipped viewport an unbroken left edge.
  // It is never used as a synthetic quote or included in the displayed count.
  const visiblePoints = points.slice(first, Math.max(first, end));
  const linePoints = points.slice(Math.max(0, first - 1), Math.max(first, end));
  return { currentDate, position, windowPosition, windowStart: isoDay(Math.ceil(windowPosition)),
    minValue: low, maxValue: high, visiblePoints, linePoints, overviewProgress: progress, latest: end > 0 ? points[end - 1]! : null };
}

function priceText(value: number, unit: string): string {
  const decimals = value >= 1000 ? 0 : value >= 1 ? 2 : 4;
  return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: decimals }).format(value)} ${unit}`;
}

function dateText(value: ISODate): string {
  return new Intl.DateTimeFormat('zh-CN', { timeZone: 'UTC', year: 'numeric', month: 'long', day: 'numeric' })
    .format(new Date(`${value}T00:00:00Z`));
}

export function markerRows(positions: number[]): number[] {
  const placed: Array<{ x: number; row: number }> = [];
  return positions.map((x) => {
    let row = 0;
    while (placed.some((item) => item.row === row && Math.abs(item.x - x) < 30)) row++;
    placed.push({ x, row });
    return row;
  });
}

export function FinancialTimeSeries(props: FinancialTimeSeriesProps) {
  const frame = useCurrentFrame();
  const { request, prices, events, plan } = props;
  const view = financialView(frame, prices.points, plan);
  const { currentDate, windowStart, latest, visiblePoints, minValue, maxValue } = view;
  const [rangeStart, rangeEnd] = plan.axis.dateRange;
  const dateSpan = Math.max(view.position - view.windowPosition, 1);
  const xForDate = (value: ISODate) => PLOT.left + ((epochDay(value) - view.windowPosition) / dateSpan) * (PLOT.right - PLOT.left);
  const tickDecimals = rollingTickDecimals(minValue, maxValue);
  const yForValue = (value: number) => PLOT.bottom - ((value - minValue) / (maxValue - minValue)) * (PLOT.bottom - PLOT.top);
  const linePoints = view.linePoints.map((point) => `${xForDate(point.date)},${yForValue(point.close)}`).join(' ');
  const activeDisplay = plan.eventDisplays.find(({ frames: [start, end] }) => start <= frame && frame < end);
  const activeEvent = activeDisplay ? events.selected.find(({ id }) => id === activeDisplay.eventId) : undefined;
  const ticks = dateTicks(view.windowPosition, view.position);
  const overviewActive = plan.segments.some((segment) => segment.kind === 'overview' && frame >= segment.frames[0]);
  const arrivedEvents = events.selected.map((event, index) => ({ event, index }))
    .filter(({ event }) => epochDay(event.date) >= view.windowPosition && event.date <= currentDate);
  const labelPositions = arrivedEvents.map(({ event }) => Math.max(PLOT.left + 14, Math.min(PLOT.right - 14, xForDate(event.date))));
  const rows = markerRows(labelPositions);
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
    <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" data-a2v-financial="line" aria-label={`${request.instrument.name} ${overviewActive ? '全历史' : `近${plan.axis.visibleWindowMonths}个月滚动`}价格演变图`} data-a2v-window-start={windowStart} data-a2v-window-end={currentDate} data-a2v-overview-progress={view.overviewProgress}>
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
        return <g key={`month-${tickDate}`}><line x1={x} x2={x} y1={PLOT.top} y2={PLOT.bottom} stroke="#172235" /><text x={x} y={PLOT.bottom + 40} textAnchor="middle" fill="#9ba9bc" fontSize="18">{view.position - view.windowPosition > 730 ? tickDate.slice(0, 4) : tickDate.slice(0, 7)}</text></g>;
      })}
      <line x1={PLOT.left} x2={PLOT.left} y1={PLOT.top} y2={PLOT.bottom} stroke="#53627a" />
      <line x1={PLOT.left} x2={PLOT.right} y1={PLOT.bottom} y2={PLOT.bottom} stroke="#53627a" />
      {view.linePoints.length > 0 && <g clipPath="url(#financial-plot)">
        <polyline fill="none" stroke="#6ab6ff" strokeWidth="5" strokeLinejoin="round" strokeLinecap="round"
          points={linePoints} data-a2v-visible-price-points={visiblePoints.length} />
      </g>}
      {arrivedEvents.map(({ event, index }, visibleIndex) => {
        const x = xForDate(event.date);
        const labelX = labelPositions[visibleIndex]!;
        const labelY = PLOT.top + 20 + rows[visibleIndex]! * 32;
        return <g key={event.id} data-a2v-event-marker={event.id}>
          <line x1={x} x2={x} y1={PLOT.top} y2={PLOT.bottom} stroke="#efb65c" strokeWidth="2" strokeDasharray="7 9" opacity=".64" />
          <circle cx={labelX} cy={labelY} r="13" fill="#ffd27b" />
          <text x={labelX} y={labelY + 6} textAnchor="middle" fill="#080d17" fontSize="15" fontWeight="700">{index + 1}</text>
        </g>;
      })}
      {latest && <g>
        {windowStart <= latest.date && <circle cx={xForDate(latest.date)} cy={yForValue(latest.close)} r="9" fill="#9bd0ff" stroke="#09213a" strokeWidth="4" />}
        <text x={PLOT.right} y="150" textAnchor="end" fill="#e8f3ff" fontSize="27" fontWeight="600">{priceText(latest.close, prices.unit)}</text>
        <text x={PLOT.right} y="185" textAnchor="end" fill="#98aac1" fontSize="18">最近有效收盘 {latest.date}</text>
      </g>}
      <text x={PLOT.left} y="872" fill="#d8e1ed" fontSize="24" fontWeight="600">{dateText(currentDate)}</text>
      <text x={PLOT.right} y="872" textAnchor="end" fill="#76859b" fontSize="16">{overviewActive ? '全历史 · 线性纵轴' : `近${plan.axis.visibleWindowMonths}个月 · 纵轴随视窗自适应`}</text>
      {activeEvent && <g data-a2v-event-card={activeEvent.id}>
        <rect x={PLOT.left} y="910" width={PLOT.right - PLOT.left} height="94" rx="12" fill="#172338" stroke="#755d38" />
        <text x={PLOT.left + 24} y="947" fill="#ffd27b" fontSize="17">{activeEvent.date} · {activeEvent.dateBasis === 'occurred' ? '发生' : activeEvent.dateBasis === 'announced' ? '公告' : '报道'}</text>
        <text x={PLOT.left + 24} y="983" fill="#f0f3f8" fontSize="22">{activeEvent.title}</text>
      </g>}
      {overviewActive && <g data-a2v-overview-legend="">
        {events.selected.map((event, index) => <text key={event.id} x={PLOT.left + (index % 4) * 403} y={936 + Math.floor(index / 4) * 48} fill="#c6d3e4" fontSize="15">
          {index + 1} · {event.date} · {event.title.length > 18 ? `${event.title.slice(0, 17)}…` : event.title}
        </text>)}
      </g>}
      {!latest && <text x={(PLOT.left + PLOT.right) / 2} y="520" textAnchor="middle" fill="#a8b4c5" fontSize="24">尚无区间内有效收盘数据</text>}
      <text x={PLOT.left} y="1044" fill="#76859b" fontSize="15">日期与价格按来源核实；事件标记说明发生时间，不表示与价格变化存在因果关系。</text>
    </svg>
  </AbsoluteFill>;
}
