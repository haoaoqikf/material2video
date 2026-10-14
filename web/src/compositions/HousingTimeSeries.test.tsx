import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { HousingTimeSeries, YEAR_HOLD_FRAMES, housingAxisLabelIndexes, housingPositionAtFrame, housingValueRange, type HousingSeries } from './HousingTimeSeries';

const currentFrame = vi.hoisted(() => ({ value: 0 }));
vi.mock('remotion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('remotion')>();
  return { ...actual, AbsoluteFill: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, useCurrentFrame: () => currentFrame.value };
});

const series: HousingSeries = {
  schemaVersion: 1, city: '郑州市', metric: '住宅商品房平均销售价格', unit: '元/平方米',
  areaUnit: '万平方米', salesAmountUnit: '亿元', formula: 'salesAmountYiYuan / salesAreaWanSquareMeters * 10000',
  durationSeconds: 60, calculationPrecisionNote: '源数据四舍五入。', methodologyNote: '按住宅销售额和面积计算。',
  sources: [{ title: '来源', url: 'https://example.org' }],
  breakpoints: [{ year: 2005, label: '2005 年起使用新口径' }],
  points: [
    { year: 2002, salesAreaWanSquareMeters: 10, salesAmountYiYuan: 2, averagePriceYuanPerSquareMeter: 2000 },
    { year: 2003, salesAreaWanSquareMeters: 10, salesAmountYiYuan: 2.2, averagePriceYuanPerSquareMeter: 2200 },
    { year: 2004, salesAreaWanSquareMeters: 10, salesAmountYiYuan: 2.4, averagePriceYuanPerSquareMeter: 2400 },
    { year: 2005, salesAreaWanSquareMeters: 10, salesAmountYiYuan: 2.8, averagePriceYuanPerSquareMeter: 2800 },
  ],
};

describe('housing annual time series', () => {
  it('maps the advance range to the first and last annual point', () => {
    expect(housingPositionAtFrame(30, series, 1800)).toEqual({ position: 0, heldIndex: 0 });
    expect(housingPositionAtFrame(30 + YEAR_HOLD_FRAMES + 1, series, 1800).position).toBeGreaterThan(0);
    expect(housingPositionAtFrame(900, series, 1800).position).toBeGreaterThan(1);
    expect(housingPositionAtFrame(1740, series, 1800)).toEqual({ position: 3, heldIndex: 3 });
  });

  it('holds every point for 15 frames and reaches the final point before the ending', () => {
    const longSeries = { ...series, points: Array.from({ length: 23 }, (_, index) => ({
      year: 2002 + index, salesAreaWanSquareMeters: 10, salesAmountYiYuan: 2 + index / 10,
      averagePriceYuanPerSquareMeter: 2000 + index * 100,
    })) };
    expect(housingPositionAtFrame(30, longSeries, 1800)).toEqual({ position: 0, heldIndex: 0 });
    const secondYear = 30 + YEAR_HOLD_FRAMES + (1800 - 30 - 60 - 23 * YEAR_HOLD_FRAMES) / 22;
    expect(housingPositionAtFrame(Math.ceil(secondYear), longSeries, 1800)).toEqual({ position: 1, heldIndex: 1 });
    expect(housingPositionAtFrame(Math.ceil(secondYear) + YEAR_HOLD_FRAMES - 1, longSeries, 1800)).toEqual({ position: 1, heldIndex: 1 });
    expect(housingPositionAtFrame(Math.ceil(secondYear) + YEAR_HOLD_FRAMES, longSeries, 1800).heldIndex).toBeNull();
    expect(housingPositionAtFrame(1725, longSeries, 1800)).toEqual({ position: 22, heldIndex: 22 });
  });

  it('keeps the revealed value range nonnegative and padded', () => {
    expect(housingValueRange([2000, 3000])).toEqual({ min: 1920, max: 3080 });
    expect(housingValueRange([2000])).toEqual({ min: 1984, max: 2016 });
  });

  it('keeps sparse year labels apart while retaining the final year', () => {
    const points = Array.from({ length: 23 }, (_, index) => ({
      year: 2002 + index, salesAreaWanSquareMeters: 10, salesAmountYiYuan: 2,
      averagePriceYuanPerSquareMeter: 2000,
    }));
    expect(housingAxisLabelIndexes(points)).toEqual([0, 4, 8, 12, 16, 22]);
  });

  it('reveals year and price and marks the 2005 break without audio or subtitles', () => {
    currentFrame.value = 1799;
    const markup = renderToStaticMarkup(<HousingTimeSeries series={series} durationInFrames={1800} fps={30} width={1080} height={1920} />);
    expect(markup).toContain('data-m2v-current-year="2005"');
    expect(markup).toContain('data-m2v-breakpoint-label="2005"');
    expect(markup).toContain('data-m2v-housing-endpoint="true"');
    expect(markup).not.toContain('<audio');
    expect(markup).not.toContain('data-m2v-subtitle');
  });

  it('shows the held year exact value and highlights its annual point', () => {
    currentFrame.value = 30;
    const markup = renderToStaticMarkup(<HousingTimeSeries series={series} durationInFrames={1800} fps={30} width={1080} height={1920} />);
    expect(markup).toContain('data-m2v-current-year="2002"');
    expect(markup).toContain('data-m2v-current-value="2000"');
    expect(markup).toContain('data-m2v-highlight-year="2002"');
  });
});
