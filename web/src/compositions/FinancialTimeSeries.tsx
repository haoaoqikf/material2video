import { useLayoutEffect } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { FinancialCandlesticks, type FinancialCandlestickProps } from './FinancialCandlesticks';

type ISODate = string;
type PricePoint = { date: ISODate; close: number };
type OHLCPoint = PricePoint & { open: number; high: number; low: number };
type EventItem = { id: string; date: ISODate; title: string; sources: string[]; dateBasis: 'occurred' | 'announced' | 'reported'; reason: string };
type TimelineSegment = { frames: [number, number]; dates: [ISODate, ISODate]; kind: 'opening' | 'advance' | 'hold' | 'ending' };
type FinancialPlan = {
  durationSeconds: number; fps: 30; canvas: { width: 1920; height: 1080 };
  axis: { dateRange: [ISODate, ISODate]; visibleWindowMonths: number; visibleWindowBars?: number; valueScale: 'rolling-linear' | 'rolling-log' };
  selectedPeriod?: 'day' | 'week' | 'month' | 'year';
  segments: TimelineSegment[]; eventDisplays: Array<{ eventId: string; frames: [number, number] }>;
  rationale: string;
};
export type FinancialTimeSeriesProps = {
  request: { instrument: { kind: 'stock' | 'index'; name: string; code: string; market: string; unit: string }; displayRange: [ISODate, ISODate] };
  prices: { schemaVersion?: number; points: PricePoint[] | OHLCPoint[]; unit: string; priceBasis: string; adjustmentDefinition?: string; indexType?: string; sources: unknown[] };
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

function frameDate(frame: number, plan: FinancialPlan): ISODate {
  const segment = plan.segments.find(({ frames: [start, end] }) => start <= frame && frame < end);
  if (!segment) throw new Error(`帧 ${frame} 没有对应时间段`);
  const [startDate, endDate] = segment.dates;
  if (segment.kind !== 'advance') return startDate;
  const [startFrame, endFrame] = segment.frames;
  const span = endFrame - startFrame - 1;
  const days = epochDay(endDate) - epochDay(startDate);
  return isoDay(epochDay(startDate) + Math.floor(((frame - startFrame) * days) / span));
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

function monthTicks(start: ISODate, end: ISODate): ISODate[] {
  const ticks = [start];
  const [year, month] = start.split('-').map(Number);
  let nextMonth = Date.UTC(year!, month!, 1) / DAY_MS;
  const endDay = epochDay(end);
  while (nextMonth < endDay) {
    ticks.push(isoDay(nextMonth));
    const date = new Date(nextMonth * DAY_MS);
    nextMonth = Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 1) / DAY_MS;
  }
  return ticks;
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
  if (props.prices.schemaVersion === 2) {
    return <FinancialCandlesticks {...(props as unknown as FinancialCandlestickProps)} />;
  }
  const frame = useCurrentFrame();
  const { request, prices, events, plan } = props;
  const currentDate = frameDate(frame, plan);
  const pointIndex = lastPointIndex(prices.points, currentDate);
  const latest = pointIndex >= 0 ? prices.points[pointIndex]! : null;
  const [rangeStart, rangeEnd] = plan.axis.dateRange;
  const windowStart = rollingWindowStart(currentDate, plan.axis.visibleWindowMonths, rangeStart);
  const dateSpan = Math.max(epochDay(currentDate) - epochDay(windowStart), 1);
  const xForDate = (value: ISODate) => PLOT.left + ((epochDay(value) - epochDay(windowStart)) / dateSpan) * (PLOT.right - PLOT.left);
  const firstVisiblePoint = lowerBound(prices.points, windowStart);
  const endVisiblePoint = lastPointIndex(prices.points, currentDate) + 1;
  const visiblePoints = prices.points.slice(firstVisiblePoint, Math.max(firstVisiblePoint, endVisiblePoint));
  const [minValue, maxValue] = rollingValueRange(visiblePoints);
  const tickDecimals = rollingTickDecimals(minValue, maxValue);
  const yForValue = (value: number) => PLOT.bottom - ((value - minValue) / (maxValue - minValue)) * (PLOT.bottom - PLOT.top);
  const linePoints = visiblePoints.map((point) => {
    const x = xForDate(point.date);
    const y = PLOT.bottom - ((point.close - minValue) / (maxValue - minValue)) * (PLOT.bottom - PLOT.top);
    return `${x},${y}`;
  }).join(' ');
  const visibleEventIds = new Set(events.selected.filter((event) => windowStart <= event.date && event.date <= currentDate).map(({ id }) => id));
  const activeDisplay = plan.eventDisplays.find(({ frames: [start, end] }) => start <= frame && frame < end);
  const activeEvent = activeDisplay ? events.selected.find(({ id }) => id === activeDisplay.eventId) : undefined;
  const ticks = monthTicks(windowStart, currentDate);

  useLayoutEffect(() => {
    document.documentElement.style.setProperty('--a2v-width', `${WIDTH}px`);
    document.documentElement.style.setProperty('--a2v-height', `${HEIGHT}px`);
    document.documentElement.dataset.a2vTheme = 'dark';
  }, []);

  return <AbsoluteFill style={{ background: '#080d17', color: '#eef4fc', fontFamily: 'Inter, "Noto Sans SC", sans-serif' }} data-a2v-financial="">
    <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`${request.instrument.name} 近${plan.axis.visibleWindowMonths}个月滚动价格演变图`} data-a2v-window-start={windowStart} data-a2v-window-end={currentDate}>
      <text x={PLOT.left} y="96" fill="#f6f8fc" fontSize="48" fontWeight="700">{request.instrument.name} · {request.instrument.code}</text>
      <text x={PLOT.left} y="146" fill="#97a7bd" fontSize="23">{rangeStart} — {rangeEnd}　{prices.priceBasis === 'official-index-points' ? prices.indexType : (prices.adjustmentDefinition ?? '仅拆合股调整，不含分红再投资')}</text>
      <text x={PLOT.left} y="184" fill="#8292a9" fontSize="18">市场 {request.instrument.market} · 单位 {prices.unit} · 公开来源：{prices.sources?.length ?? 0} 项</text>
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
        return <g key={`month-${tickDate}`}><line x1={x} x2={x} y1={PLOT.top} y2={PLOT.bottom} stroke="#172235" /><text x={x} y={PLOT.bottom + 40} textAnchor="middle" fill="#9ba9bc" fontSize="18">{tickDate.slice(0, 7)}</text></g>;
      })}
      <line x1={PLOT.left} x2={PLOT.left} y1={PLOT.top} y2={PLOT.bottom} stroke="#53627a" />
      <line x1={PLOT.left} x2={PLOT.right} y1={PLOT.bottom} y2={PLOT.bottom} stroke="#53627a" />
      {visiblePoints.length > 0 && <g>
        <polyline fill="none" stroke="#6ab6ff" strokeWidth="5" strokeLinejoin="round" strokeLinecap="round"
          points={linePoints} data-a2v-visible-price-points={visiblePoints.length} />
      </g>}
      {events.selected.filter((event) => visibleEventIds.has(event.id)).map((event) => {
        const x = xForDate(event.date);
        return <g key={event.id} data-a2v-event-marker={event.id}>
          <line x1={x} x2={x} y1={PLOT.top} y2={PLOT.bottom} stroke="#efb65c" strokeWidth="2" strokeDasharray="7 9" opacity=".64" />
          <circle cx={x} cy={PLOT.top + 12} r="7" fill="#ffd27b" />
        </g>;
      })}
      {latest && <g>
        {windowStart <= latest.date && <circle cx={xForDate(latest.date)} cy={yForValue(latest.close)} r="9" fill="#9bd0ff" stroke="#09213a" strokeWidth="4" />}
        <text x={PLOT.right} y="150" textAnchor="end" fill="#e8f3ff" fontSize="27" fontWeight="600">{priceText(latest.close, prices.unit)}</text>
        <text x={PLOT.right} y="185" textAnchor="end" fill="#98aac1" fontSize="18">最近有效收盘 {latest.date}</text>
      </g>}
      <text x={PLOT.left} y="872" fill="#d8e1ed" fontSize="24" fontWeight="600">{dateText(currentDate)}</text>
      <text x={PLOT.right} y="872" textAnchor="end" fill="#76859b" fontSize="16">纵轴随近{plan.axis.visibleWindowMonths}个月视窗自适应</text>
      {activeEvent && <g data-a2v-event-card={activeEvent.id}>
        <rect x={PLOT.left} y="910" width={PLOT.right - PLOT.left} height="94" rx="12" fill="#172338" stroke="#755d38" />
        <text x={PLOT.left + 24} y="947" fill="#ffd27b" fontSize="17">{activeEvent.date} · {activeEvent.dateBasis === 'occurred' ? '发生' : activeEvent.dateBasis === 'announced' ? '公告' : '报道'}</text>
        <text x={PLOT.left + 24} y="983" fill="#f0f3f8" fontSize="22">{activeEvent.title}</text>
      </g>}
      {!latest && <text x={(PLOT.left + PLOT.right) / 2} y="520" textAnchor="middle" fill="#a8b4c5" fontSize="24">尚无区间内有效收盘数据</text>}
      <text x={PLOT.left} y="1044" fill="#76859b" fontSize="15">日期与价格按来源核实；事件标记说明发生时间，不表示与价格变化存在因果关系。</text>
    </svg>
  </AbsoluteFill>;
}
