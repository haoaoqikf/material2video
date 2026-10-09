import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { FinancialTimeSeries, rollingTickDecimals, rollingValueRange, rollingWindowStart, type FinancialTimeSeriesProps } from './FinancialTimeSeries';

const testFrame = vi.hoisted(() => ({ value: 0 }));
vi.mock('remotion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('remotion')>();
  return { ...actual, AbsoluteFill: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, useCurrentFrame: () => testFrame.value };
});

const props: FinancialTimeSeriesProps = {
  request: { instrument: { kind: 'stock', name: '合成公司', code: 'SYN', market: 'TEST', unit: 'USD' }, displayRange: ['2020-01-01', '2020-01-03'] },
  prices: {
    points: [{ date: '2020-01-02', close: 100 }, { date: '2020-01-03', close: 102 }],
    unit: 'USD', priceBasis: 'split-adjusted', adjustmentDefinition: '合成数据：仅拆合股调整，不计分红再投资',
    sources: [{ url: 'https://example.invalid/prices' }],
  },
  events: { selected: [{ id: 'announcement', date: '2020-01-02', dateBasis: 'announced', title: '合成公告', sources: ['https://example.invalid/event'], reason: '合成夹具' }] },
  plan: {
    durationSeconds: 6, fps: 30, canvas: { width: 1920, height: 1080 },
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

  it('renders schema v2 candles on the partial bucket without leaking future OHLC', () => {
    const candlesProps: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, displayRange: ['2024-12-30', '2025-01-02'] },
      prices: {
        ...props.prices,
        schemaVersion: 2,
        points: [
          { date: '2024-12-30', open: 10, high: 12, low: 9, close: 11 },
          { date: '2025-01-02', open: 11, high: 500, low: 10, close: 450 },
        ],
        candles: [{ key: '2024', start: '2024-01-01', end: '2024-12-31', firstTradingDate: '2024-12-30', lastTradingDate: '2024-12-30', open: 10, high: 12, low: 9, close: 11 }],
      } as FinancialTimeSeriesProps['prices'],
      events: { selected: [{ ...props.events.selected[0]!, date: '2025-01-02' }] },
      plan: {
        ...props.plan,
        selectedPeriod: 'year',
        axis: { dateRange: ['2024-12-30', '2025-01-02'], visibleWindowBars: 12, visibleWindowMonths: 3, valueScale: 'rolling-log' },
        segments: [
          { frames: [0, 90], dates: ['2024-12-30', '2024-12-30'], kind: 'opening' },
          { frames: [90, 100], dates: ['2024-12-30', '2025-01-02'], kind: 'advance' },
          { frames: [100, 180], dates: ['2025-01-02', '2025-01-02'], kind: 'ending' },
        ],
        eventDisplays: [{ eventId: 'announcement', frames: [100, 120] }],
      } as FinancialTimeSeriesProps['plan'],
    };
    testFrame.value = 90;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...candlesProps} />);
    expect(markup).toContain('data-a2v-financial="candlestick"');
    expect(markup).toContain('data-a2v-period="year"');
    expect(markup).toContain('2024*');
    expect(markup).not.toContain('>500.00<');
    expect(markup).not.toContain('>450.00<');
    expect(markup).not.toContain('data-a2v-event-marker="announcement"');
  });

  it('shows an empty-range message before the first v2 trading candle', () => {
    const emptyProps: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, displayRange: ['2024-12-29', '2025-01-02'] },
      prices: { ...props.prices, schemaVersion: 2, points: [], candles: [{ key: '2024', start: '2024-01-01', end: '2024-12-31', firstTradingDate: '2024-12-30', lastTradingDate: '2024-12-31', open: 10, high: 12, low: 9, close: 11 }] } as FinancialTimeSeriesProps['prices'],
      plan: { ...props.plan, selectedPeriod: 'year', axis: { ...props.plan.axis, visibleWindowBars: 12, valueScale: 'rolling-log' } } as FinancialTimeSeriesProps['plan'],
    };
    testFrame.value = 0;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...emptyProps} />);
    expect(markup).toContain('尚无区间内 OHLC 报价');
    expect(markup).not.toContain('Infinity');
  });
});
