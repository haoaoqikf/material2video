import { AbsoluteFill, useCurrentFrame } from 'remotion';

type Day = { date: string; open: number; high: number; low: number; close: number };
export type FinancialCandlestickProps = {
  request: { instrument: { name: string; code: string; market: string; unit: string }; displayRange: [string, string] };
  prices: { points: Day[]; candles: Array<{ key: string; start: string; end: string; firstTradingDate: string; lastTradingDate: string; open: number; high: number; low: number; close: number }>; unit: string; adjustmentDefinition?: string; sources: Array<{ url?: string; adjustmentDefinition?: string }>; rawSnapshots?: Array<{ path?: string }> };
  events: { selected: Array<{ id: string; date: string; title: string; dateBasis: string }> };
  plan: { durationSeconds: number; selectedPeriod: 'day' | 'week' | 'month' | 'year'; axis: { visibleWindowBars: number; valueScale: 'rolling-linear' | 'rolling-log' }; segments: Array<{ frames: [number, number]; dates: [string, string]; kind: string }>; eventDisplays: Array<{ eventId: string; frames: [number, number] }> };
};
type Period = FinancialCandlestickProps['plan']['selectedPeriod'];

const W = 1920; const H = 1080; const L = 170; const R = 1770; const T = 260; const B = 790;
const DAY = 86_400_000;
const epoch = (date: string) => Date.parse(`${date}T00:00:00Z`) / DAY;
const iso = (day: number) => new Date(day * DAY).toISOString().slice(0, 10);
const periodName = { day: '日 K', week: '周 K', month: '月 K', year: '年 K' };

function bucketKey(date: string, period: Period): string {
  if (period === 'day') return date;
  const day = new Date(`${date}T00:00:00Z`);
  if (period === 'month') return date.slice(0, 7);
  if (period === 'year') return date.slice(0, 4);
  const thursday = new Date(day); thursday.setUTCDate(day.getUTCDate() + 3 - ((day.getUTCDay() + 6) % 7));
  const year = thursday.getUTCFullYear();
  const first = new Date(Date.UTC(year, 0, 4));
  const firstThursday = new Date(first); firstThursday.setUTCDate(first.getUTCDate() + 3 - ((first.getUTCDay() + 6) % 7));
  const week = 1 + Math.round((thursday.getTime() - firstThursday.getTime()) / (7 * DAY));
  return `${year}-W${String(week).padStart(2, '0')}`;
}

function bucketStart(key: string, period: Period): string {
  if (period === 'day') return key;
  if (period === 'year') return `${key}-01-01`;
  if (period === 'month') return `${key}-01`;
  const [year, week] = key.split('-W').map(Number); const jan4 = Date.UTC(year!, 0, 4) / DAY;
  return iso(jan4 - ((new Date(jan4 * DAY).getUTCDay() + 6) % 7) + (week! - 1) * 7);
}
function bucketEnd(key: string, period: Period): string {
  if (period === 'day') return key;
  if (period === 'year') return `${key}-12-31`;
  if (period === 'month') { const [y, m] = key.split('-').map(Number); return iso(Date.UTC(y!, m!, 0) / DAY); }
  const [year, week] = key.split('-W').map(Number);
  const jan4 = Date.UTC(year!, 0, 4) / DAY;
  const monday = jan4 - ((new Date(jan4 * DAY).getUTCDay() + 6) % 7) + (week! - 1) * 7;
  return iso(monday + 6);
}

function currentDate(frame: number, plan: FinancialCandlestickProps['plan']): string {
  const segment = plan.segments.find(({ frames: [start, end] }) => start <= frame && frame < end);
  if (!segment) return plan.segments.at(-1)!.dates[1];
  if (segment.kind !== 'advance') return segment.dates[0];
  const [startFrame, endFrame] = segment.frames; const [start, end] = segment.dates;
  const progress = (frame - startFrame) / Math.max(endFrame - startFrame - 1, 1);
  return iso(epoch(start) + Math.floor((epoch(end) - epoch(start)) * progress));
}

export function FinancialCandlesticks({ request, prices, events, plan }: FinancialCandlestickProps) {
  const frame = useCurrentFrame(); const date = currentDate(frame, plan);
  const key = bucketKey(date, plan.selectedPeriod);
  const through = prices.points.filter((point) => point.date <= date && bucketKey(point.date, plan.selectedPeriod) === key);
  const partial = through.length ? [{ key, date: through[0]!.date, end: bucketEnd(key, plan.selectedPeriod), open: through[0]!.open, high: Math.max(...through.map((point) => point.high)), low: Math.min(...through.map((point) => point.low)), close: through.at(-1)!.close }] : [];
  const complete = prices.candles.filter((candle) => candle.key !== key && candle.lastTradingDate <= date).map((candle) => ({ key: candle.key, date: candle.firstTradingDate, end: candle.end, open: candle.open, high: candle.high, low: candle.low, close: candle.close }));
  const all = [...complete, ...partial];
  const visible = all.slice(-plan.axis.visibleWindowBars);
  if (!visible.length) return <AbsoluteFill style={{ background: '#080d17', color: '#eef4fc', fontFamily: 'Inter, "Noto Sans SC", sans-serif', justifyContent: 'center', alignItems: 'center', fontSize: 32 }}>尚无区间内 OHLC 报价 · {date}</AbsoluteFill>;
  const low = Math.min(...visible.map((item) => item.low)); const high = Math.max(...visible.map((item) => item.high));
  const logarithmic = plan.axis.valueScale === 'rolling-log';
  const scale = (value: number) => logarithmic ? Math.log(value) : value;
  const span = Math.max(scale(high) - scale(low), Math.abs(scale(high) || 1) * 0.02, 0.01); const min = scale(low) - span * 0.08; const max = scale(high) + span * 0.08;
  const y = (value: number) => B - ((scale(value) - min) / (max - min)) * (B - T);
  const fullRange = request.displayRange[1] > request.displayRange[0];
  const fixedSlots = all.length < plan.axis.visibleWindowBars && fullRange;
  const step = fixedSlots ? (R - L) / Math.max(all.length, 1) : (R - L) / Math.max(visible.length, 1);
  const bodyWidth = Math.min(28, Math.max(3, step * 0.62));
  const latest = [...prices.points].reverse().find((point) => point.date <= date);
  const active = plan.eventDisplays.find(({ frames: [start, end] }) => start <= frame && frame < end);
  const event = active && events.selected.find(({ id }) => id === active.eventId);
  const label = periodName[plan.selectedPeriod];
  return <AbsoluteFill style={{ background: '#080d17', color: '#eef4fc', fontFamily: 'Inter, "Noto Sans SC", sans-serif' }} data-a2v-financial="candlestick" data-a2v-period={plan.selectedPeriod}>
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${request.instrument.name} ${label}价格演变`} data-a2v-financial="candlestick" data-a2v-period={plan.selectedPeriod}>
      <text x={L} y="96" fill="#f6f8fc" fontSize="48" fontWeight="700">{request.instrument.name} · {request.instrument.code}</text>
      <text x={L} y="150" fill="#a8b8cf" fontSize="25">{request.displayRange[0]} — {request.displayRange[1]}　{label}　{request.instrument.unit}　仅拆股调整</text>
      <text x={R} y="150" textAnchor="end" fill="#d4e3f7" fontSize="23">{latest ? `${latest.close.toFixed(2)} USD · ${latest.date}` : '尚无报价'}</text>
      <text x={L} y="195" fill="#76859b" fontSize="16">股价按区间末股份单位调整；不计分红再投资。{logarithmic ? '纵轴为对数刻度。' : ''}事件标记表示时间关联，不代表因果。</text>
      {Array.from({ length: 5 }, (_, i) => { const value = min + (max - min) * i / 4; const labelValue = logarithmic ? Math.exp(value) : value; return <g key={i}><line x1={L} x2={R} y1={B - ((value - min) / (max - min)) * (B - T)} y2={B - ((value - min) / (max - min)) * (B - T)} stroke="#253247"/><text x={L - 18} y={B - ((value - min) / (max - min)) * (B - T) + 7} textAnchor="end" fill="#8b9ab0" fontSize="18">{labelValue.toFixed(labelValue >= 100 ? 0 : 2)}</text></g>; })}
      <line x1={L} x2={L} y1={T} y2={B} stroke="#53627a"/><line x1={L} x2={R} y1={B} y2={B} stroke="#53627a"/>
      {visible.map((candle, index) => {
        const x = fixedSlots
          ? L + ((epoch(candle.date) - epoch(request.displayRange[0])) / (epoch(request.displayRange[1]) - epoch(request.displayRange[0]))) * (R - L)
          : L + step * (index + 0.5);
        const up = candle.close >= candle.open; const color = up ? '#36c890' : '#ff6e78';
        const top = y(Math.max(candle.open, candle.close)); const height = Math.max(2, Math.abs(y(candle.open) - y(candle.close)));
        const complete = candle.end <= date && request.displayRange[0] <= bucketStart(candle.key, plan.selectedPeriod) && request.displayRange[1] >= candle.end;
        return <g key={candle.date} data-a2v-candle={candle.date} data-a2v-candle-complete={complete ? 'true' : 'false'}>
          <line x1={x} x2={x} y1={y(candle.high)} y2={y(candle.low)} stroke={color} strokeWidth="3"/>
          <rect x={x - bodyWidth / 2} y={top} width={bodyWidth} height={height} fill={up ? color : 'none'} stroke={color} strokeWidth="3" rx="1"/>
          {(index % Math.max(1, Math.ceil(visible.length / 9)) === 0 || index === visible.length - 1) && <text x={x} y={B + 40} textAnchor="middle" fill="#9ba9bc" fontSize="18">{plan.selectedPeriod === 'year' ? candle.date.slice(0, 4) : candle.date}{complete ? '' : '*'}</text>}
          {!complete && <title>{`${candle.key} 未完成或范围截断`}</title>}
        </g>;
      })}
      {events.selected.filter((item) => item.date <= date).map((item) => {
        const index = visible.findIndex((candle) => candle.key === bucketKey(item.date, plan.selectedPeriod));
        if (index < 0) return null;
        const candle = visible[index]!;
        const x = fixedSlots
          ? L + ((epoch(candle.date) - epoch(request.displayRange[0])) / (epoch(request.displayRange[1]) - epoch(request.displayRange[0]))) * (R - L)
          : L + step * (index + 0.5);
        return <g key={item.id} data-a2v-event-marker={item.id}><line x1={x} x2={x} y1={T} y2={B} stroke="#efb65c" strokeDasharray="7 9" opacity=".52"/><circle cx={x} cy={T + 10} r="7" fill="#ffd27b"/></g>;
      })}
      <text x={L} y="875" fill="#d8e1ed" fontSize="25">{date}　{visible.length} 根可见蜡烛</text>
      <text x={R} y="875" textAnchor="end" fill="#76859b" fontSize="17">* 未完成或范围截断　红跌绿涨</text>
      {event && <g data-a2v-event-card={event.id}><rect x={L} y="920" width={R-L} height="86" rx="12" fill="#172338" stroke="#755d38"/><text x={L+24} y="974" fill="#ffd27b" fontSize="24">{event.date} · {event.title}</text></g>}
      <text x={L} y="1045" fill="#76859b" fontSize="15">市场 {request.instrument.market} · 来源 {prices.sources.length} 项 · 事件标注表示时间关联，不代表因果</text>
    </svg>
  </AbsoluteFill>;
}
