import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { FinancialTimeSeries, financialView, framePosition, markerRows, rollingTickDecimals, rollingValueRange, rollingWindowStart, type FinancialTimeSeriesProps } from './FinancialTimeSeries';

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
  events: { selected: [{ id: 'announcement', date: '2020-01-02', dateBasis: 'announced', title: '合成公告', sources: ['https://example.invalid/event'], reason: '合成夹具' }] },
  plan: {
    schemaVersion: 3, chartType: 'line', durationSeconds: 6, fps: 30, canvas: { width: 1920, height: 1080 },
    axis: { dateRange: ['2020-01-01', '2020-01-03'], visibleWindowMonths: 3, valueScale: 'rolling-linear' },
    segments: [
      { frames: [0, 15], dates: ['2020-01-01', '2020-01-01'], kind: 'opening' },
      { frames: [15, 90], dates: ['2020-01-01', '2020-01-03'], kind: 'advance' },
      { frames: [90, 180], dates: ['2020-01-03', '2020-01-03'], kind: 'ending' },
    ],
    eventDisplays: [{ eventId: 'announcement', frames: [53, 70] }], rationale: '测试夹具',
  },
  durationInFrames: 180, fps: 30, width: 1920, height: 1080,
};

describe('financial time-series composition', () => {
  it('separates all eight coincident or nearby event labels instead of cycling three rows', () => {
    expect(markerRows([100, 100, 100, 100, 100, 100, 100, 100])).toEqual([0, 1, 2, 3, 4, 5, 6, 7]);
    expect(markerRows([100, 120, 180, 181])).toEqual([0, 1, 0, 1]);
  });
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

  it('does not expose prices or event markers before their dates', () => {
    testFrame.value = 15;
    const opening = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(opening).toContain('尚无区间内有效收盘数据');
    expect(opening).not.toContain('data-a2v-event-marker');
    expect(opening).not.toContain('data-a2v-event-card');
  });

  it('reveals the matching close and event at its scheduled frame', () => {
    testFrame.value = 53;
    const eventFrame = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(eventFrame).toContain('data-a2v-event-marker="announcement"');
    expect(eventFrame).toContain('data-a2v-event-card="announcement"');
    expect(eventFrame).toContain('100 USD');
    expect(eventFrame).toContain('最近有效收盘 2020-01-02');
    expect(eventFrame).not.toContain('102 USD');
  });

  it('holds the last trading close through non-trading dates and reaches all data at the ending frame', () => {
    testFrame.value = 179;
    const ending = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(ending).toContain('102 USD');
    expect(ending).toContain('最近有效收盘 2020-01-03');
    expect(ending).toContain('data-a2v-event-marker="announcement"');
  });

  it('shows only arrived prices and markers inside the rolling window', () => {
    const rollingProps: FinancialTimeSeriesProps = {
      ...props,
      prices: {
        ...props.prices,
        points: [
          { date: '2020-01-01', close: 15 },
          { date: '2020-01-02', close: 16 },
          { date: '2020-01-03', close: 17 },
          { date: '2020-04-01', close: 99 },
          { date: '2020-04-02', close: 100 },
          { date: '2020-04-03', close: 999 },
        ],
      },
      events: { selected: [
        { ...props.events.selected[0]!, id: 'rolled-out', date: '2020-01-01' },
        { ...props.events.selected[0]!, id: 'in-window', date: '2020-03-01' },
      ] },
      plan: {
        ...props.plan,
        axis: { dateRange: ['2020-01-01', '2020-04-03'], visibleWindowMonths: 3, valueScale: 'rolling-linear' },
        segments: [
          { frames: [0, 1], dates: ['2020-01-01', '2020-01-01'], kind: 'opening' },
          { frames: [1, 90], dates: ['2020-01-01', '2020-04-02'], kind: 'advance' },
          { frames: [90, 180], dates: ['2020-04-02', '2020-04-02'], kind: 'ending' },
        ],
        eventDisplays: [],
      },
    };
    testFrame.value = 179;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...rollingProps} />);
    expect(markup).toContain('data-a2v-window-start="2020-01-02"');
    expect(markup).toContain('data-a2v-window-end="2020-04-02"');
    expect(markup).toContain('data-a2v-visible-price-points="4"');
    expect(markup).toContain('100 USD');
    expect(markup).toContain('最近有效收盘 2020-04-02');
    expect(markup).not.toContain('15 USD');
    expect(markup).not.toContain('16 USD');
    expect(markup).not.toContain('17 USD');
    expect(markup).not.toContain('99 USD');
    expect(markup).not.toContain('999 USD');
    expect(markup).not.toContain('data-a2v-event-marker="rolled-out"');
    expect(markup).toContain('data-a2v-event-marker="in-window"');
  });

  it('holds the previous real close while the current date is a non-trading day', () => {
    const nonTradingProps: FinancialTimeSeriesProps = {
      ...props,
      prices: { ...props.prices, points: [{ date: '2020-04-01', close: 99 }] },
      plan: {
        ...props.plan,
        axis: { dateRange: ['2020-01-01', '2020-04-02'], visibleWindowMonths: 3, valueScale: 'rolling-linear' },
        segments: [
          { frames: [0, 1], dates: ['2020-01-01', '2020-01-01'], kind: 'opening' },
          { frames: [1, 90], dates: ['2020-01-01', '2020-04-02'], kind: 'advance' },
          { frames: [90, 180], dates: ['2020-04-02', '2020-04-02'], kind: 'ending' },
        ],
        eventDisplays: [],
      },
    };
    testFrame.value = 179;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...nonTradingProps} />);
    expect(markup).toContain('99 USD');
    expect(markup).toContain('最近有效收盘 2020-04-01');
    expect(markup).toContain('2020年4月2日');
  });

  it('moves calendar coordinates continuously but quotes only arrived trading points', () => {
    const view = financialView(54, props.prices.points, props.plan);
    const next = financialView(55, props.prices.points, props.plan);
    expect(framePosition(54, props.plan) % 1).not.toBe(0);
    expect(next.position).toBeGreaterThan(view.position);
    expect(view.latest?.close).toBe(100);
    expect(view.linePoints.every((point) => point.date <= view.currentDate)).toBe(true);
    const changedFuture = props.prices.points.map((point) => point.date > view.currentDate ? { ...point, close: 99999 } : point);
    expect(financialView(54, changedFuture, props.plan)).toEqual(view);
  });

  it('expands to every historical point with a stable final linear axis and numbered events', () => {
    const overviewProps: FinancialTimeSeriesProps = {
      ...props,
      prices: { ...props.prices, points: [
        { date: '2000-01-01', close: 1 }, { date: '2019-01-01', close: 10 }, { date: '2020-01-03', close: 100 },
      ] },
      plan: { ...props.plan, axis: { ...props.plan.axis, dateRange: ['2000-01-01', '2020-01-03'], visibleWindowMonths: 12 }, segments: [
        { frames: [0, 90], dates: ['2000-01-01', '2000-01-01'], kind: 'opening' },
        { frames: [90, 120], dates: ['2000-01-01', '2020-01-03'], kind: 'advance' },
        { frames: [120, 180], dates: ['2020-01-03', '2020-01-03'], kind: 'overview' },
        { frames: [180, 300], dates: ['2020-01-03', '2020-01-03'], kind: 'ending' },
      ], eventDisplays: [] },
    };
    const before = financialView(119, overviewProps.prices.points, overviewProps.plan);
    const start = financialView(120, overviewProps.prices.points, overviewProps.plan);
    expect(start.minValue).toBe(before.minValue);
    expect(start.maxValue).toBe(before.maxValue);
    expect(start.windowPosition).toBe(before.windowPosition);
    for (let frame = 120; frame < 180; frame++) {
      const view = financialView(frame, overviewProps.prices.points, overviewProps.plan);
      for (const point of view.visiblePoints) {
        expect(point.close).toBeGreaterThanOrEqual(view.minValue);
        expect(point.close).toBeLessThanOrEqual(view.maxValue);
      }
    }
    const final = financialView(179, overviewProps.prices.points, overviewProps.plan);
    expect(final.windowStart).toBe('2000-01-01');
    expect(final.visiblePoints).toHaveLength(3);
    expect([final.minValue, final.maxValue]).toEqual(rollingValueRange(overviewProps.prices.points));
    expect(financialView(299, overviewProps.prices.points, overviewProps.plan)).toEqual(final);
    testFrame.value = 299;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...overviewProps} />);
    expect(markup).toContain('全历史 · 线性纵轴');
    expect(markup).toContain('data-a2v-overview-legend');
    expect(markup).toContain('data-a2v-visible-price-points="3"');
    expect(markup).toContain('data-a2v-financial="line"');
    expect(markup).not.toContain('candlestick');
  });

  it('keeps every arrived point within the causal smoothed axis and is seek independent', () => {
    for (const frame of [15, 53, 70, 89, 179, 53]) {
      const view = financialView(frame, props.prices.points, props.plan);
      for (const point of view.visiblePoints) {
        expect(point.close).toBeGreaterThan(view.minValue);
        expect(point.close).toBeLessThan(view.maxValue);
      }
    }
    expect(financialView(53, props.prices.points, props.plan)).toEqual(financialView(53, props.prices.points, props.plan));
  });
});
