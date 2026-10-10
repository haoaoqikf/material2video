import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { FinancialTimeSeries, financialView, framePosition, valueTickDecimals, revealedValueRange, type FinancialTimeSeriesProps } from './FinancialTimeSeries';

const epochDayForTest = (value: string) => Date.parse(`${value}T00:00:00Z`) / 86400000;

const testFrame = vi.hoisted(() => ({ value: 0 }));
vi.mock('remotion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('remotion')>();
  return { ...actual, AbsoluteFill: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, useCurrentFrame: () => testFrame.value };
});

const props: FinancialTimeSeriesProps = {
  request: { instrument: { kind: 'stock', name: '合成公司', code: 'SYN', market: 'TEST', unit: 'USD' }, displayRange: ['2020-01-01', '2020-01-03'], investment: { year: 2020, principal: 100 } },
  prices: {
    schemaVersion: 3, points: [{ date: '2020-01-02', close: 100 }, { date: '2020-01-03', close: 102 }],
    unit: 'USD', priceBasis: 'split-adjusted', adjustmentDefinition: '合成数据：仅拆合股调整，不计分红再投资',
    sources: [{ url: 'https://example.invalid/prices' }],
  },
  plan: {
    schemaVersion: 7, chartType: 'line', durationSeconds: 60, fps: 30, canvas: { width: 1080, height: 1920 },
    axis: { dateRange: ['2020-01-01', '2020-01-03'], dateScale: 'staged-expanding', valueScale: 'revealed-linear' },
    segments: [
      { frames: [0, 90], dates: ['2020-01-01', '2020-01-01'], kind: 'opening' },
      { frames: [90, 1680], dates: ['2020-01-01', '2020-01-03'], kind: 'advance' },
      { frames: [1680, 1800], dates: ['2020-01-03', '2020-01-03'], kind: 'ending' },
    ],
    rationale: '测试夹具',
  },
  durationInFrames: 1800, fps: 30, width: 1080, height: 1920,
};

describe('financial time-series composition', () => {
  it('handles thirty years of daily data within the view-computation budget', () => {
    const start = Date.UTC(1990, 0, 1);
    const points = Array.from({ length: 11000 }, (_, index) => ({
      date: new Date(start + index * 86400000).toISOString().slice(0, 10), close: 1 + index / 100,
    }));
    const first = points[0]!.date; const last = points.at(-1)!.date;
    const plan = { ...props.plan, axis: { ...props.plan.axis, dateRange: [first, last] as [string, string] }, segments: props.plan.segments.map((segment) => ({
      ...segment, dates: (segment.kind === 'opening' ? [first, first] : segment.kind === 'advance' ? [first, last] : [last, last]) as [string, string],
    })) };
    const started = performance.now();
    let count = 0;
    for (let frame = 0; frame < 1800; frame++) count = financialView(frame, points, plan, { year: 1990, principal: 1 }).visiblePoints.length;
    const elapsed = performance.now() - started;
    expect(count).toBe(11000);
    expect(elapsed).toBeLessThan(3000);
    console.info(`financialView: 11000 points / 1800 frames = ${elapsed.toFixed(1)} ms (budget 3000 ms)`);
  });

  it('pads adaptive price ranges, including a single flat value', () => {
    expect(revealedValueRange([{ date: '2020-01-01', close: 10 }, { date: '2020-01-02', close: 20 }])).toEqual([9.2, 20.8]);
    expect(revealedValueRange([{ date: '2020-01-01', close: 100 }])).toEqual([99, 101]);
    expect(valueTickDecimals(...revealedValueRange([{ date: '2020-01-01', close: 0.041 }]))).toBe(4);
    expect(revealedValueRange([])).toEqual([0, 1]);
  });

  it('shows no quote before the first real trading close arrives', () => {
    testFrame.value = 90;
    const opening = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(opening).toContain('尚未到达投资起点');
    expect(opening).not.toContain('当前市值');
    expect(opening).not.toContain('收益率');
    expect(opening).not.toContain('data-a2v-current-value-follow');
  });

  it('shows the latest arrived close and its real trading date', () => {
    testFrame.value = 885;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(markup).toContain('100 USD');
    expect(markup).toContain('2020年1月2日');
    expect(markup).not.toContain('收盘日期 2020-01-02');
    expect(markup).not.toContain('102 USD');
    expect(markup).toContain('收益 0 USD');
    expect(markup).toContain('收益率 0%');
    expect(markup).toContain('假设 2020 年投入 100 USD');
    expect(markup).toContain('data-a2v-current-value-follow="true"');
    expect(markup).not.toContain('100.00 USD');
  });

  it('buys on the first trading close in the investment year and derives portfolio returns', () => {
    const points = [
      { date: '2019-12-31', close: 50 },
      { date: '2020-01-02', close: 100 },
      { date: '2020-01-03', close: 125 },
    ];
    const before = financialView(90, points, props.plan, { year: 2020, principal: 1_000_000 });
    const after = financialView(1679, points, props.plan, { year: 2020, principal: 1_000_000 });
    expect(before.latest).toBeNull();
    expect(after.investmentStartDate).toBe('2020-01-02');
    expect(after.latest?.close).toBe(1_250_000);
    expect(after.gain).toBe(250_000);
    expect(after.returnRate).toBe(0.25);
    expect(after.visiblePoints.map(({ date }) => date)).toEqual(['2020-01-02', '2020-01-03']);
    expect(after.minValue).toBeGreaterThanOrEqual(0);
  });

  it('contains no event markers, cards, lists, or copy', () => {
    testFrame.value = 1679;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(markup).not.toMatch(/event|事件|公告|发生/iu);
    expect(markup).toContain('不计分红再投资');
    expect(markup).not.toContain('横轴分阶段扩展');
    expect(markup).not.toContain('市场 TEST');
  });

  it('uses the optional short name and derives one wrapped index note from unique source hosts', () => {
    const indexProps: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, instrument: { ...props.request.instrument, kind: 'index', displayName: '示例指数' } },
      prices: { ...props.prices, priceBasis: 'official-index-points', indexType: '价格指数', sources: [
        { url: 'https://example.invalid/series' }, { url: 'https://example.invalid/calendar' }, { url: 'https://market.example/index' },
      ] },
    };
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...indexProps} />);
    expect(markup).toContain('示例指数 · SYN');
    expect(markup).toContain('按点位比例模拟');
    expect(markup.match(/example\.invalid/g)).toHaveLength(1);
    expect(markup).toContain('market.example');
  });

  it('blocks a title that exceeds the fixed two-line capacity instead of shrinking it', () => {
    const longName: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, instrument: { ...props.request.instrument, displayName: '超长显示名称'.repeat(8) } },
    };
    expect(() => renderToStaticMarkup(<FinancialTimeSeries {...longName} />)).toThrow('instrument.displayName/code');
  });

  it('holds the previous real close on non-trading dates without inventing a quote', () => {
    const nonTradingProps: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, displayRange: ['2020-01-01', '2020-04-03'], investment: { year: 2020, principal: 100 } },
      prices: { ...props.prices, points: [{ date: '2020-04-01', close: 99 }] },
      plan: { ...props.plan, axis: { ...props.plan.axis, dateRange: ['2020-01-01', '2020-04-03'] }, segments: [
        { frames: [0, 90], dates: ['2020-01-01', '2020-01-01'], kind: 'opening' },
        { frames: [90, 1680], dates: ['2020-01-01', '2020-04-03'], kind: 'advance' },
        { frames: [1680, 1800], dates: ['2020-04-03', '2020-04-03'], kind: 'ending' },
      ] },
    };
    testFrame.value = 1679;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...nonTradingProps} />);
    expect(markup).toContain('100 USD');
    expect(markup).not.toContain('99 USD');
    expect(markup).toContain('2020年4月3日');
  });

  it('moves calendar coordinates continuously but quotes only arrived trading points', () => {
    const view = financialView(885, props.prices.points, props.plan);
    const next = financialView(886, props.prices.points, props.plan);
    expect(framePosition(885, props.plan) % 1).not.toBe(0);
    expect(next.position).toBeGreaterThan(view.position);
    expect(view.latest?.close).toBe(1_000_000);
    expect(view.linePoints.every((point) => point.date <= view.currentDate)).toBe(true);
    const changedFuture = props.prices.points.map((point) => point.date > view.currentDate ? { ...point, close: 99999 } : point);
    expect(financialView(885, changedFuture, props.plan)).toEqual(view);
  });

  it('expands the full-history axis in stages and preserves every historical point', () => {
    const historyProps: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, investment: { year: 2000, principal: 100 } },
      prices: { ...props.prices, points: [
        { date: '2000-01-01', close: 1 }, { date: '2010-01-01', close: 100 }, { date: '2020-01-03', close: 10 },
      ] },
      plan: { ...props.plan, axis: { ...props.plan.axis, dateRange: ['2000-01-01', '2020-01-03'] }, segments: [
        { frames: [0, 90], dates: ['2000-01-01', '2000-01-01'], kind: 'opening' },
        { frames: [90, 1680], dates: ['2000-01-01', '2020-01-03'], kind: 'advance' },
        { frames: [1680, 1800], dates: ['2020-01-03', '2020-01-03'], kind: 'ending' },
      ] },
    };
    const opening = financialView(0, historyProps.prices.points, historyProps.plan);
    const middle = financialView(1000, historyProps.prices.points, historyProps.plan);
    const final = financialView(1679, historyProps.prices.points, historyProps.plan);
    const ordered = Array.from({ length: 1680 }, (_, frame) => financialView(frame, historyProps.prices.points, historyProps.plan));
    for (let frame = 1; frame < ordered.length; frame++) {
      expect(ordered[frame]!.windowEndPosition).toBeGreaterThanOrEqual(ordered[frame - 1]!.windowEndPosition);
      expect(ordered[frame]!.windowEndPosition).toBeGreaterThanOrEqual(ordered[frame]!.position);
    }
    expect(opening.windowPosition).toBe(final.windowPosition);
    expect(opening.windowEndPosition).toBeLessThan(final.windowEndPosition);
    expect(middle.visiblePoints).toHaveLength(2);
    expect(final.visiblePoints).toHaveLength(3);
    expect(final.windowEndPosition).toBe(epochDayForTest('2020-01-03'));
    expect(final.maxValue).toBeGreaterThan(100);
    expect(final.minValue).toBeLessThan(100);
    for (let frame = 1680; frame < 1800; frame++) {
      expect(financialView(frame, historyProps.prices.points, historyProps.plan)).toEqual(final);
    }
    const markupAt = (frame: number) => {
      testFrame.value = frame;
      return renderToStaticMarkup(<FinancialTimeSeries {...historyProps} />);
    };
    expect(opening.ticks.length).toBeGreaterThan(1);
    expect(opening.ticks).not.toEqual(final.ticks);
    expect(markupAt(1799)).toContain('data-a2v-visible-value-points="3"');
  });

  it.each([[1, 2, 3], [100, 1, 150], [0.01, 0.01, 0.01], [10, 10, 10]])('contains arrived prices and ignores future extremes: %s', (...values) => {
    const points = values.map((close, index) => ({ date: `2020-01-0${index + 1}`, close }));
    const ordered = Array.from({ length: 1800 }, (_, frame) => financialView(frame, points, props.plan));
    for (const frame of Array.from({ length: 1800 }, (_, index) => 1799 - index)) {
      const view = financialView(frame, points, props.plan);
      expect(view).toEqual(ordered[frame]);
      for (const point of view.visiblePoints) {
        expect(point.close).toBeGreaterThan(view.minValue);
        expect(point.close).toBeLessThan(view.maxValue);
      }
      const changed = points.map((point) => point.date > view.currentDate ? { ...point, close: 999999 } : point);
      expect(financialView(frame, changed, props.plan)).toEqual(view);
    }
  });

  it('keeps every arrived point within the causal smoothed axis and is seek independent', () => {
    for (const frame of [90, 885, 1679, 1680, 1679, 1799]) {
      const view = financialView(frame, props.prices.points, props.plan);
      for (const point of view.visiblePoints) {
        expect(point.close).toBeGreaterThan(view.minValue);
        expect(point.close).toBeLessThan(view.maxValue);
      }
    }
    expect(financialView(885, props.prices.points, props.plan)).toEqual(financialView(885, props.prices.points, props.plan));
  });

  it('derives up to six natural-year stages from partial and leap-year ranges', () => {
    const rangePlan = (start: string, end: string, durationSeconds = 60) => {
      const frames = durationSeconds * 30;
      const advanceEnd = frames - 120;
      return {
        ...props.plan, durationSeconds,
        axis: { ...props.plan.axis, dateRange: [start, end] as [string, string] },
        segments: [
          { frames: [0, 90] as [number, number], dates: [start, start] as [string, string], kind: 'opening' as const },
          { frames: [90, advanceEnd] as [number, number], dates: [start, end] as [string, string], kind: 'advance' as const },
          { frames: [advanceEnd, frames] as [number, number], dates: [end, end] as [string, string], kind: 'ending' as const },
        ],
      };
    };
    const decades = rangePlan('1999-02-01', '2026-10-08');
    expect(financialView(0, [], decades).windowEndPosition).toBe(epochDayForTest('2003-12-31'));
    expect(financialView(1679, [], decades).windowEndPosition).toBe(epochDayForTest('2026-10-08'));
    for (const frame of [0, 300, 600, 900, 1200, 1500, 1679, 1799]) {
      const labels = financialView(frame, [], decades).ticks;
      expect(labels.length).toBeLessThanOrEqual(4);
      for (let index = 1; index < labels.length; index++) {
        const left = labels[index - 1]!;
        const right = labels[index]!;
        expect(right.x - left.x).toBeGreaterThanOrEqual((right.width + left.width) / 2 + 12);
      }
    }

    const leap = rangePlan('2019-03-01', '2024-02-29');
    expect(financialView(0, [], leap).windowEndPosition).toBe(epochDayForTest('2019-12-31'));
    expect(financialView(1679, [], leap).windowEndPosition).toBe(epochDayForTest('2024-02-29'));

    const singleYear = rangePlan('2024-02-29', '2024-12-31');
    expect(financialView(0, [], singleYear).windowEndPosition).toBe(epochDayForTest('2024-12-31'));

    const fast = rangePlan('2000-01-01', '2026-12-31', 10);
    let previous = financialView(90, [], fast).windowEndPosition;
    for (let frame = 91; frame < 180; frame++) {
      const view = financialView(frame, [], fast);
      expect(view.windowEndPosition).toBeGreaterThanOrEqual(previous);
      expect(view.windowEndPosition).toBeGreaterThanOrEqual(view.position);
      previous = view.windowEndPosition;
    }
    expect(financialView(179, [], fast).windowEndPosition).toBe(epochDayForTest('2026-12-31'));
    expect(financialView(180, [], fast)).toEqual(financialView(299, [], fast));
  });
});
