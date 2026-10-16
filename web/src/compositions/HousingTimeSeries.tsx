import { FPS } from '../video-config';
import { AbsoluteFill, useCurrentFrame } from 'remotion';

export type HousingPoint = {
  year: number;
  salesAreaWanSquareMeters: number;
  salesAmountYiYuan: number;
  averagePriceYuanPerSquareMeter: number;
};

export type HousingSeries = {
  schemaVersion: 1;
  city: string;
  metric: string;
  unit: string;
  areaUnit: string;
  salesAmountUnit: string;
  formula: string;
  durationSeconds: number;
  calculationPrecisionNote: string;
  methodologyNote: string;
  sources: { title: string; url: string }[];
  breakpoints: { year: number; label: string }[];
  points: HousingPoint[];
};

export type HousingTimeSeriesProps = {
  series: HousingSeries;
  durationInFrames: number;
  fps: number;
  width: number;
  height: number;
};

const PLOT = { left: 220, right: 928, top: 650, bottom: 1450 };
const OPENING_FRAMES = FPS;
const ENDING_FRAMES = 2 * FPS;
export const YEAR_HOLD_FRAMES = FPS / 2;

export type HousingPosition = { position: number; heldIndex: number | null };

export function housingPositionAtFrame(frame: number, series: HousingSeries, durationInFrames: number): HousingPosition {
  const lastIndex = series.points.length - 1;
  const intervalCount = lastIndex;
  const holdFrames = YEAR_HOLD_FRAMES * series.points.length;
  const movementFrames = Math.max(intervalCount, durationInFrames - OPENING_FRAMES - ENDING_FRAMES - holdFrames);
  const movementPerInterval = movementFrames / intervalCount;
  const startFrame = OPENING_FRAMES;
  const endFrame = startFrame + holdFrames + movementFrames;
  const boundedFrame = Math.max(startFrame, Math.min(endFrame, frame));
  let cursor = startFrame;

  for (let index = 0; index <= lastIndex; index += 1) {
    const holdEnd = cursor + YEAR_HOLD_FRAMES;
    if (boundedFrame < holdEnd || index === lastIndex) {
      return { position: index, heldIndex: index };
    }
    cursor = holdEnd;
    if (index < lastIndex) {
      const movementEnd = cursor + movementPerInterval;
      if (boundedFrame < movementEnd) {
        const fraction = (boundedFrame - cursor) / movementPerInterval;
        return { position: index + fraction, heldIndex: null };
      }
      cursor = movementEnd;
    }
  }

  return { position: lastIndex, heldIndex: lastIndex };
}

export function housingValueRange(values: number[]) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || Math.max(Math.abs(max) * 0.02, 200);
  const padding = span * 0.08;
  return { min: Math.max(0, min - padding), max: max + padding };
}

export function housingAxisLabelIndexes(points: HousingPoint[]) {
  const lastIndex = points.length - 1;
  const indexes = points.map((_, index) => index).filter((index) => index % 4 === 0);
  if (!indexes.includes(lastIndex)) {
    if (indexes.length && lastIndex - indexes[indexes.length - 1]! < 4) indexes.pop();
    indexes.push(lastIndex);
  }
  return indexes;
}

function formatPrice(value: number) {
  return Math.round(value).toLocaleString('zh-CN');
}

function formatAxis(value: number) {
  return Math.round(value).toLocaleString('zh-CN');
}

export function HousingTimeSeries(props: HousingTimeSeriesProps) {
  const frame = useCurrentFrame();
  const { series, durationInFrames } = props;
  const points = series.points;
  const { position, heldIndex } = housingPositionAtFrame(frame, series, durationInFrames);
  const index = Math.floor(position);
  const fraction = position - index;
  const current = points[index]!;
  const next = points[Math.min(index + 1, points.length - 1)]!;
  const interpolatedPrice = current.averagePriceYuanPerSquareMeter
    + (next.averagePriceYuanPerSquareMeter - current.averagePriceYuanPerSquareMeter) * fraction;
  const interpolatedYear = heldIndex !== null ? points[heldIndex]!.year : (fraction >= 0.5 ? next.year : current.year);
  const visible = points.slice(0, index + 1).map((point) => point.averagePriceYuanPerSquareMeter);
  if (fraction > 0) visible.push(interpolatedPrice);
  const range = housingValueRange(visible);
  const lastPosition = Math.max(position, 1);
  const xForIndex = (pointIndex: number) => PLOT.left + (pointIndex / lastPosition) * (PLOT.right - PLOT.left);
  const yForValue = (value: number) => PLOT.bottom - ((value - range.min) / (range.max - range.min)) * (PLOT.bottom - PLOT.top);
  const linePoints = points.slice(0, index + 1).map((point, pointIndex) => `${xForIndex(pointIndex)},${yForValue(point.averagePriceYuanPerSquareMeter)}`);
  if (fraction > 0) linePoints.push(`${xForIndex(position)},${yForValue(interpolatedPrice)}`);
  const displayedPrice = heldIndex !== null ? points[heldIndex]!.averagePriceYuanPerSquareMeter : interpolatedPrice;
  const value = Math.round(displayedPrice);
  const tickStep = Math.max(1, Math.ceil((range.max - range.min) / 4 / 1000)) * 1000;
  const firstTick = Math.ceil(range.min / tickStep) * tickStep;
  const ticks: number[] = [];
  for (let tick = firstTick; tick < range.max && ticks.length < 5; tick += tickStep) ticks.push(tick);
  const axisLabelIndexes = new Set(housingAxisLabelIndexes(points));
  const xLabels = points.map((point, pointIndex) => ({ point, pointIndex }))
    .filter(({ pointIndex }) => axisLabelIndexes.has(pointIndex) && pointIndex <= position);
  const change = series.breakpoints.find((item) => item.year === 2005);
  const changeIndex = change ? points.findIndex((point) => point.year === change.year) : -1;
  const markerX = changeIndex >= 0 && position >= changeIndex ? xForIndex(changeIndex) : null;

  return <AbsoluteFill style={{ backgroundColor: '#080d17', color: '#eef4fc', fontFamily: 'Inter, "Noto Sans SC", sans-serif' }} data-m2v-housing="line">
    <svg width="1080" height="1920" viewBox="0 0 1080 1920" role="img"
      aria-label={`${series.city}${series.metric}年度变化 ${points[0]!.year}至${points.at(-1)!.year}`}
      data-m2v-housing="line" data-m2v-current-year={interpolatedYear} data-m2v-current-value={value}>
      <text x="540" y="250" textAnchor="middle" fill="#eef4fc" fontSize="46" fontWeight="700">{series.city}住宅商品房销售均价</text>
      <text x="145" y="390" fill="#eef4fc" fontSize="72" fontWeight="700" fontVariant="tabular-nums" data-m2v-live-year="true">{interpolatedYear}</text>
      <text x="940" y="330" textAnchor="end" fill="#aebbd0" fontSize="25">住宅平均销售价格</text>
      <text x="940" y="395" textAnchor="end" fill="#5bd2c0" fontSize="58" fontWeight="700" fontVariant="tabular-nums" data-m2v-live-value="true">{formatPrice(displayedPrice)} 元/㎡</text>
      <text x={PLOT.left} y="520" fill="#aebbd0" fontSize="24">年度住宅商品房平均销售价格 · 按销售额 ÷ 销售面积计算</text>
      {ticks.map((tick) => {
        const y = yForValue(tick);
        return <g key={tick}>
          <line x1={PLOT.left} x2={PLOT.right} y1={y} y2={y} stroke="#253248" strokeWidth="2" />
          <text x={PLOT.left - 18} y={y + 8} textAnchor="end" fill="#9aa9be" fontSize="21">{formatAxis(tick)}</text>
        </g>;
      })}
      <line x1={PLOT.left} x2={PLOT.right} y1={PLOT.bottom} y2={PLOT.bottom} stroke="#718097" strokeWidth="2" />
      {markerX !== null && <g data-m2v-housing-breakpoint="2005">
        <line x1={markerX} x2={markerX} y1={PLOT.top} y2={PLOT.bottom} stroke="#ffbf69" strokeWidth="2" strokeDasharray="8 10" opacity="0.8" />
        <circle cx={markerX} cy={PLOT.top + 16} r="8" fill="#ffbf69" />
      </g>}
      {xLabels.map(({ point, pointIndex }) => <text key={point.year} x={xForIndex(pointIndex)} y={PLOT.bottom + 48}
        textAnchor={pointIndex === 0 ? 'start' : pointIndex === points.length - 1 ? 'end' : 'middle'}
        fill="#aebbd0" fontSize="21" data-m2v-axis-label="year">{point.year}</text>)}
      <polyline points={linePoints.join(' ')} fill="none" stroke="#5bd2c0" strokeWidth="5" strokeLinejoin="round" strokeLinecap="round" data-m2v-housing-line="true" />
      {heldIndex !== null && <circle cx={xForIndex(heldIndex)} cy={yForValue(points[heldIndex]!.averagePriceYuanPerSquareMeter)} r="24" fill="#5bd2c0" opacity="0.2" data-m2v-housing-highlight="true" data-m2v-highlight-year={points[heldIndex]!.year} />}
      <circle cx={xForIndex(position)} cy={yForValue(heldIndex !== null ? points[heldIndex]!.averagePriceYuanPerSquareMeter : interpolatedPrice)} r={heldIndex !== null ? 13 : 10} fill="#5bd2c0" stroke="#e1fff9" strokeWidth="3" data-m2v-housing-endpoint="true" />
      {change && markerX !== null && <text x={Math.min(markerX + 12, PLOT.right - 220)} y={PLOT.top - 22}
        fill="#ffcf8a" fontSize="20" data-m2v-breakpoint-label="2005">2005 统计口径调整</text>}
      <text x="145" y="1600" fill="#d1d9e5" fontSize="21">统计局注：2005 年起销售面积、销售额采用新口径。</text>
      <text x="145" y="1640" fill="#9eabc0" fontSize="19">均价由公布的住宅销售额（亿元）÷面积（万平方米）×10,000 计算；原始指标取整至 0.1，均价为近似值。</text>
      <text x="145" y="1700" fill="#75839a" fontSize="19">数据来源：郑州市统计局《历年房地产开发主要指标》 · {series.points[0]!.year}—{points.at(-1)!.year}</text>
    </svg>
  </AbsoluteFill>;
}
