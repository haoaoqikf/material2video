import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { FinancialTimeSeries, financialView, framePosition, rollingTickDecimals, rollingValueRange, rollingWindowStart, type FinancialTimeSeriesProps } from './FinancialTimeSeries';

const testFrame = vi.hoisted(() => ({ value: 0 }));
vi.mock('remotion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('remotion')>();
  return { ...actual, AbsoluteFill: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, useCurrentFrame: () => testFrame.value };
});

const props: FinancialTimeSeriesProps = {
  request: { instrument: { kind: 'stock', name: '合成公司', code: 'SYN', market: 'TEST', unit: 'USD' }, displayRange: ['2020-01-01', '2020-01-03'] },
  prices: {
    schemaVersion: 3, points: [{ date: '2020-01-02', close: 100 }, { date: '2020-01-03', close: 102 }],
    unit: 'USD', priceBasis: 'split-adjusted', adjustmentDefinition: '合成数据：仅拆合股调整，不计分红再投资',
    sources: [{ url: 'https://example.invalid/prices' }],
  },
  plan: {
    schemaVersion: 4, chartType: 'line', durationSeconds: 60, fps: 30, canvas: { width: 1920, height: 1080 },
    axis: { dateRange: ['2020-01-01', '2020-01-03'], visibleWindowMonths: 3, valueScale: 'rolling-linear' },
    segments: [
      { frames: [0, 90], dates: ['2020-01-01', '2020-01-01'], kind: 'opening' },
      { frames: [90, 1620], dates: ['2020-01-01', '2020-01-03'], kind: 'advance' },
      { frames: [1620, 1680], dates: ['2020-01-03', '2020-01-03'], kind: 'overview' },
      { frames: [1680, 1800], dates: ['2020-01-03', '2020-01-03'], kind: 'ending' },
    ],
    rationale: '测试夹具',
  },
  durationInFrames: 1800, fps: 30, width: 1920, height: 1080,
};

describe('financial time-series composition', () => {
  it('subtracts calendar months with month-end clamping and clamps to the data start', () => {
    expect(rollingWindowStart('2020-05-31', 3, '1999-01-22')).toBe('2020-02-29');
    expect(rollingWindowStart('2024-05-31', 3, '1999-01-22')).toBe('2024-02-29');
    expect(rollingWindowStart('2020-02-29', 3, '2020-01-22')).toBe('2020-01-22');
  });

  it('pads adaptive price ranges, including a single flat value', () => {
    expect(rollingValueRange([{ date: '2020-01-01', close: 10 }, { date: '2020-01-02', close: 20 }])).toEqual([9.2, 20.8]);
    expect(rollingValueRange([{ date: '2020-01-01', close: 100 }])).toEqual([99, 101]);
    expect(rollingTickDecimals(...rollingValueRange([{ date: '2020-01-01', close: 0.041 }]))).toBe(4);
    expect(rollingValueRange([])).toEqual([0, 1]);
  });

  it('shows no quote before the first real trading close arrives', () => {
    testFrame.value = 90;
    const opening = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(opening).toContain('尚无区间内有效收盘数据');
    expect(opening).not.toContain('100 USD');
  });

  it('shows the latest arrived close and its real trading date', () => {
    testFrame.value = 855;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(markup).toContain('100 USD');
    expect(markup).toContain('最近有效收盘 2020-01-02');
    expect(markup).not.toContain('102 USD');
  });

  it('contains no event markers, cards, lists, or copy', () => {
    testFrame.value = 1679;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(markup).not.toMatch(/event|事件|公告|发生/iu);
    expect(markup).toContain('全历史 · 线性纵轴');
  });

  it('holds the previous real close on non-trading dates without inventing a quote', () => {
    const nonTradingProps: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, displayRange: ['2020-01-01', '2020-04-03'] },
      prices: { ...props.prices, points: [{ date: '2020-04-01', close: 99 }] },
      plan: { ...props.plan, axis: { ...props.plan.axis, dateRange: ['2020-01-01', '2020-04-03'] }, segments: [
        { frames: [0, 90], dates: ['2020-01-01', '2020-01-01'], kind: 'opening' },
        { frames: [90, 1620], dates: ['2020-01-01', '2020-04-03'], kind: 'advance' },
        { frames: [1620, 1680], dates: ['2020-04-03', '2020-04-03'], kind: 'overview' },
        { frames: [1680, 1800], dates: ['2020-04-03', '2020-04-03'], kind: 'ending' },
      ] },
    };
    testFrame.value = 1619;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...nonTradingProps} />);
    expect(markup).toContain('99 USD');
    expect(markup).toContain('最近有效收盘 2020-04-01');
    expect(markup).toContain('2020年4月3日');
  });

  it('moves calendar coordinates continuously but quotes only arrived trading points', () => {
    const view = financialView(855, props.prices.points, props.plan);
    const next = financialView(856, props.prices.points, props.plan);
    expect(framePosition(855, props.plan) % 1).not.toBe(0);
    expect(next.position).toBeGreaterThan(view.position);
    expect(view.latest?.close).toBe(100);
    expect(view.linePoints.every((point) => point.date <= view.currentDate)).toBe(true);
    const changedFuture = props.prices.points.map((point) => point.date > view.currentDate ? { ...point, close: 99999 } : point);
    expect(financialView(855, changedFuture, props.plan)).toEqual(view);
  });

  it('expands to the full history with a stable linear axis', () => {
    const overviewProps: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, displayRange: ['2000-01-01', '2020-01-03'] },
      prices: { ...props.prices, points: [
        { date: '2000-01-01', close: 1 }, { date: '2019-01-01', close: 10 }, { date: '2020-01-03', close: 100 },
      ] },
      plan: { ...props.plan, axis: { ...props.plan.axis, dateRange: ['2000-01-01', '2020-01-03'] }, segments: [
        { frames: [0, 90], dates: ['2000-01-01', '2000-01-01'], kind: 'opening' },
        { frames: [90, 1620], dates: ['2000-01-01', '2020-01-03'], kind: 'advance' },
        { frames: [1620, 1680], dates: ['2020-01-03', '2020-01-03'], kind: 'overview' },
        { frames: [1680, 1800], dates: ['2020-01-03', '2020-01-03'], kind: 'ending' },
      ] },
    };
    const before = financialView(1619, overviewProps.prices.points, overviewProps.plan);
    const start = financialView(1620, overviewProps.prices.points, overviewProps.plan);
    expect(start.minValue).toBe(before.minValue);
    expect(start.maxValue).toBe(before.maxValue);
    expect(start.windowPosition).toBe(before.windowPosition);
    for (let frame = 1620; frame < 1680; frame++) {
      const view = financialView(frame, overviewProps.prices.points, overviewProps.plan);
      for (const point of view.visiblePoints) {
        expect(point.close).toBeGreaterThanOrEqual(view.minValue);
        expect(point.close).toBeLessThanOrEqual(view.maxValue);
      }
    }
    const final = financialView(1679, overviewProps.prices.points, overviewProps.plan);
    expect(final.windowStart).toBe('2000-01-01');
    expect(final.visiblePoints).toHaveLength(3);
    expect([final.minValue, final.maxValue]).toEqual(rollingValueRange(overviewProps.prices.points));
    expect(financialView(1799, overviewProps.prices.points, overviewProps.plan)).toEqual(final);
    testFrame.value = 1799;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...overviewProps} />);
    expect(markup).toContain('全历史 · 线性纵轴');
    expect(markup).toContain('data-a2v-visible-price-points="3"');
    expect(markup).toContain('data-a2v-financial="line"');
    expect(markup).not.toContain('candlestick');
  });

  it('keeps every arrived point within the causal smoothed axis and is seek independent', () => {
    for (const frame of [90, 855, 1619, 1620, 1679, 1799]) {
      const view = financialView(frame, props.prices.points, props.plan);
      for (const point of view.visiblePoints) {
        expect(point.close).toBeGreaterThan(view.minValue);
        expect(point.close).toBeLessThan(view.maxValue);
      }
    }
    expect(financialView(855, props.prices.points, props.plan)).toEqual(financialView(855, props.prices.points, props.plan));
  });
});
