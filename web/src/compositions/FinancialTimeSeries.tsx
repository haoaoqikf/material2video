import { useLayoutEffect, useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';

type ISODate = string;
type PricePoint = { date: ISODate; close: number };
type EventItem = { id: string; date: ISODate; title: string; sources: string[]; dateBasis: 'occurred' | 'announced' | 'reported'; reason: string };
type TimelineSegment = { frames: [number, number]; dates: [ISODate, ISODate]; kind: 'opening' | 'advance' | 'hold' | 'ending' };
type FinancialPlan = {
  durationSeconds: number; fps: 30; canvas: { width: 1920; height: 1080 };
  axis: { dateRange: [ISODate, ISODate]; valueRange: [number, number] };
  segments: TimelineSegment[]; eventDisplays: Array<{ eventId: string; frames: [number, number] }>;
  rationale: string;
};
export type FinancialTimeSeriesProps = {
  request: { instrument: { kind: 'stock' | 'index'; name: string; code: string; market: string; unit: string }; displayRange: [ISODate, ISODate] };
  prices: { points: PricePoint[]; unit: string; priceBasis: string; adjustmentDefinition?: string; indexType?: string; sources: unknown[] };
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
  const { request, prices, events, plan } = props;
  const currentDate = frameDate(frame, plan);
  const pointIndex = lastPointIndex(prices.points, currentDate);
  const latest = pointIndex >= 0 ? prices.points[pointIndex]! : null;
  const [rangeStart, rangeEnd] = plan.axis.dateRange;
  const [minValue, maxValue] = plan.axis.valueRange;
  const dateSpan = Math.max(epochDay(rangeEnd) - epochDay(rangeStart), 1);
  const xForDate = (value: ISODate) => PLOT.left + ((epochDay(value) - epochDay(rangeStart)) / dateSpan) * (PLOT.right - PLOT.left);
  const yForValue = (value: number) => PLOT.bottom - ((value - minValue) / (maxValue - minValue)) * (PLOT.bottom - PLOT.top);
  const clipX = latest ? xForDate(latest.date) : PLOT.left;
  const fullLinePoints = useMemo(() => prices.points.map((point) => {
    const x = PLOT.left + ((epochDay(point.date) - epochDay(rangeStart)) / dateSpan) * (PLOT.right - PLOT.left);
    const y = PLOT.bottom - ((point.close - minValue) / (maxValue - minValue)) * (PLOT.bottom - PLOT.top);
    return `${x},${y}`;
  }).join(' '), [prices.points, rangeStart, dateSpan, minValue, maxValue]);
  const visibleEventIds = new Set(events.selected.filter((event) => event.date <= currentDate).map(({ id }) => id));
  const activeDisplay = plan.eventDisplays.find(({ frames: [start, end] }) => start <= frame && frame < end);
  const activeEvent = activeDisplay ? events.selected.find(({ id }) => id === activeDisplay.eventId) : undefined;
  const yearCount = Number(rangeEnd.slice(0, 4)) - Number(rangeStart.slice(0, 4)) + 1;
  const yearStep = Math.max(1, Math.ceil(yearCount / 6));
  const years: number[] = [];
  for (let year = Number(rangeStart.slice(0, 4)); year <= Number(rangeEnd.slice(0, 4)); year += yearStep) years.push(year);
  if (years.at(-1) !== Number(rangeEnd.slice(0, 4))) years.push(Number(rangeEnd.slice(0, 4)));

  useLayoutEffect(() => {
    document.documentElement.style.setProperty('--a2v-width', `${WIDTH}px`);
    document.documentElement.style.setProperty('--a2v-height', `${HEIGHT}px`);
    document.documentElement.dataset.a2vTheme = 'dark';
  }, []);

  return <AbsoluteFill style={{ background: '#080d17', color: '#eef4fc', fontFamily: 'Inter, "Noto Sans SC", sans-serif' }} data-a2v-financial="">
    <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`${request.instrument.name} 历史价格时间演变图`}>
      <defs><clipPath id="financial-line-reveal"><rect x={PLOT.left} y={PLOT.top} width={Math.max(0, clipX - PLOT.left)} height={PLOT.bottom - PLOT.top} /></clipPath></defs>
      <text x={PLOT.left} y="96" fill="#f6f8fc" fontSize="48" fontWeight="700">{request.instrument.name} · {request.instrument.code}</text>
      <text x={PLOT.left} y="146" fill="#97a7bd" fontSize="23">{rangeStart} — {rangeEnd}　{prices.priceBasis === 'official-index-points' ? prices.indexType : (prices.adjustmentDefinition ?? '仅拆合股调整，不含分红再投资')}</text>
      <text x={PLOT.left} y="184" fill="#8292a9" fontSize="18">市场 {request.instrument.market} · 单位 {prices.unit} · 公开来源：{prices.sources?.length ?? 0} 项</text>
      {Array.from({ length: 5 }, (_, index) => {
        const value = minValue + ((maxValue - minValue) * index) / 4;
        const y = yForValue(value);
        return <g key={`grid-${index}`}>
          <line x1={PLOT.left} x2={PLOT.right} y1={y} y2={y} stroke="#253247" strokeWidth="1" />
          <text x={PLOT.left - 18} y={y + 7} textAnchor="end" fill="#8b9ab0" fontSize="18">{new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)}</text>
        </g>;
      })}
      {years.map((year) => {
        const tickDate = `${year}-01-01`;
        const x = xForDate(tickDate);
        if (x < PLOT.left || x > PLOT.right) return null;
        return <g key={`year-${year}`}><line x1={x} x2={x} y1={PLOT.top} y2={PLOT.bottom} stroke="#172235" /><text x={x} y={PLOT.bottom + 40} textAnchor="middle" fill="#9ba9bc" fontSize="18">{year}</text></g>;
      })}
      <line x1={PLOT.left} x2={PLOT.left} y1={PLOT.top} y2={PLOT.bottom} stroke="#53627a" />
      <line x1={PLOT.left} x2={PLOT.right} y1={PLOT.bottom} y2={PLOT.bottom} stroke="#53627a" />
      {latest && <g clipPath="url(#financial-line-reveal)">
        <polyline fill="none" stroke="#6ab6ff" strokeWidth="5" strokeLinejoin="round" strokeLinecap="round"
          points={fullLinePoints} />
      </g>}
      {events.selected.filter((event) => visibleEventIds.has(event.id)).map((event) => {
        const x = xForDate(event.date);
        return <g key={event.id} data-a2v-event-marker={event.id}>
          <line x1={x} x2={x} y1={PLOT.top} y2={PLOT.bottom} stroke="#efb65c" strokeWidth="2" strokeDasharray="7 9" opacity=".64" />
          <circle cx={x} cy={PLOT.top + 12} r="7" fill="#ffd27b" />
        </g>;
      })}
      {latest && <g>
        <circle cx={xForDate(latest.date)} cy={yForValue(latest.close)} r="9" fill="#9bd0ff" stroke="#09213a" strokeWidth="4" />
        <text x={PLOT.right} y="150" textAnchor="end" fill="#e8f3ff" fontSize="27" fontWeight="600">{priceText(latest.close, prices.unit)}</text>
        <text x={PLOT.right} y="185" textAnchor="end" fill="#98aac1" fontSize="18">最近有效收盘 {latest.date}</text>
      </g>}
      <text x={PLOT.left} y="872" fill="#d8e1ed" fontSize="24" fontWeight="600">{dateText(currentDate)}</text>
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
