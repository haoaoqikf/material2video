import { execFileSync } from 'node:child_process';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { FinancialTimeSeries, financialView, framePosition, valueTickDecimals, revealedValueRange, canvasCenterOffset, placeEndpointCallout, type FinancialTimeSeriesProps } from './FinancialTimeSeries';

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

describe('endpoint value callout placement', () => {
  it('keeps an open right-side location separated from the endpoint and line', () => {
    const endpoint = { x: 700, y: 800 };
    const callout = placeEndpointCallout(endpoint, 120, [{ x: 300, y: 700 }, { x: 700, y: 800 }]);
    expect(callout.side).toBe('right');
    expect(callout.x).toBeGreaterThan(endpoint.x + 8);
    expect(callout.y + callout.height).toBeGreaterThan(endpoint.y);
    expect(callout.x + callout.width).toBeLessThanOrEqual(940);
  });

  it('moves a right-edge label inward and keeps it within the project layout', () => {
    const endpoint = { x: 928, y: 800 };
    const callout = placeEndpointCallout(endpoint, 100, [{ x: 850, y: 740 }, endpoint]);
    expect(callout.side).not.toBe('right');
    expect(callout.x).toBeGreaterThanOrEqual(140);
    expect(callout.x + callout.width).toBeLessThanOrEqual(940);
    expect(callout.y).toBeGreaterThanOrEqual(180);
    expect(callout.y + callout.height).toBeLessThanOrEqual(1740);
  });

  it('selects the least-colliding side for a volatile path and supports large values', () => {
    const endpoint = { x: 800, y: 800 };
    const volatileLine = [{ x: 500, y: 850 }, { x: 760, y: 850 }, { x: 780, y: 830 }, endpoint];
    const callout = placeEndpointCallout(endpoint, 160, volatileLine);
    expect(callout.side).toBe('above');
    expect(callout.x).toBeGreaterThanOrEqual(140);
    expect(callout.x + callout.width).toBeLessThanOrEqual(940);
    expect(callout.y + callout.height).toBeLessThan(endpoint.y - 8);
    const largeCallout = placeEndpointCallout({ x: 760, y: 800 }, 330, [{ x: 760, y: 800 }]);
    expect(largeCallout.width).toBeGreaterThan(390);
    expect(largeCallout.x + largeCallout.width).toBeLessThanOrEqual(940);
  });
});

describe('financial time-series composition', () => {
  const renderedTitle = (markup: string) => markup.match(/data-m2v-investment-title="true"[^>]*>([^<]+)<\/text>/u)?.[1] ?? '';

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
    expect(renderedTitle(opening)).toBe('假如你2020年买入100元合成公司');
    expect(opening).not.toContain('data-m2v-live-gain');
    expect(opening).not.toContain('data-m2v-live-return');
    expect(opening).not.toContain('data-m2v-live-date');
    expect(opening).not.toContain('data-m2v-current-value-follow');
    expect(opening).not.toContain('尚未到达投资起点');
    expect(opening).not.toContain('data-m2v-visible-value-points');
    expect(opening).toContain('data-m2v-risk-disclaimer="true"');
  });

  it('writes a million-unit principal without appending its currency to the title', () => {
    testFrame.value = 0;
    const millionProps: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, investment: { year: 2020, principal: 1_000_000 } },
    };
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...millionProps} />);
    expect(renderedTitle(markup)).toBe('假如你2020年买入100万元合成公司');
    expect(markup.match(/data-m2v-investment-title="true"[^>]*>([^<]+)<\/text>/u)?.[1]).not.toContain('美元');
  });

  it('formats title principal before the instrument and includes 元 for stock and index', () => {
    const tenThousandProps = { ...props, request: { ...props.request, instrument: { ...props.request.instrument, displayName: '苹果' }, investment: { year: 2020, principal: 100_000 } } };
    const stock = renderToStaticMarkup(<FinancialTimeSeries {...tenThousandProps} />);
    expect(renderedTitle(stock)).toBe('假如你2020年买入10万元苹果');
    const indexProps = { ...tenThousandProps, request: { ...tenThousandProps.request, instrument: { ...tenThousandProps.request.instrument, kind: 'index' as const } } };
    const index = renderToStaticMarkup(<FinancialTimeSeries {...indexProps} />);
    expect(renderedTitle(index)).toBe('假如你2020年按比例投资10万元苹果');
  });

  it('shows the investment title, year and live portfolio value, with the endpoint amount following the line', () => {
    testFrame.value = 885;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(markup).toContain('100元');
    expect(markup).toContain('2020年1月2日');
    expect(markup).not.toContain('2020-01-01 — 2020-01-03');
    expect(markup).not.toContain('102元');
    expect(markup).not.toContain('data-m2v-live-gain');
    expect(markup).not.toContain('收益率');
    expect(renderedTitle(markup)).toBe('假如你2020年买入100元合成公司');
    expect(markup).not.toContain('SYN');
    expect(markup).toContain('当前市值');
    expect(markup).toContain('data-m2v-current-value-follow="true"');
    expect(markup).toContain('data-m2v-endpoint-callout="true"');
    expect(markup).toContain('data-m2v-endpoint-callout-backing="true"');
    expect(markup).toContain('fill="#080d17" stroke="#35445b"');
    expect(markup).not.toContain('100.00元');
    expect(markup).toContain('stroke="#55d58a"');
    expect(markup).toContain('data-m2v-live-date="true" x="940" y="442" text-anchor="end"');
    expect(markup).toContain('>100元</text>');
    expect(markup).not.toMatch(/美元|港元|人民币|USD/u);
  });

  it('colors positive returns and the portfolio line red, and negative returns green', () => {
    testFrame.value = 1679;
    const positive = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(positive).toContain('102元');
    expect(positive).not.toContain('收益率');
    expect(positive).toContain('stroke="#ff5d68"');

    const lossProps = { ...props, prices: { ...props.prices, points: [
      { date: '2020-01-02', close: 100 }, { date: '2020-01-03', close: 75 },
    ] } };
    const negative = renderToStaticMarkup(<FinancialTimeSeries {...lossProps} />);
    expect(negative).toContain('75元');
    expect(negative).not.toContain('收益率');
    expect(negative).toContain('stroke="#55d58a"');
  });

  it('uses the centered plot and unified safe area, thinner line, and small source notes', () => {
    testFrame.value = 1679;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(markup).toContain('x1="220" x2="928"');
    expect(markup).toContain('data-m2v-value-axis-label="true" x="206" y="1199" text-anchor="end" fill="#8b9ab0" font-size="14"');
    expect(markup).toContain('data-m2v-summary="true" x="140" y="1320" fill="#b9c7d9" font-size="24"');
    expect(markup).toContain('data-m2v-risk-disclaimer="true" x="140" y="1460" fill="#8b9ab0" font-size="20"');
    expect(markup).toContain('过往业绩不代表未来表现。本视频仅作信息展示，不构成投资建议。');
    expect(markup).toContain('stroke-width="3"');
    expect(markup).toContain('r="8"');
  });

  it('centers the actual content bounds on the canvas midpoint within symmetric layout bounds', () => {
    expect(canvasCenterOffset({ y: 360, height: 1200 })).toBe(0);
    expect(canvasCenterOffset({ y: 360, height: 1260 })).toBe(-30);
    expect(() => canvasCenterOffset({ y: 0, height: 1561 })).toThrow('金融画面整体内容高于纵向布局可用高度');
    testFrame.value = 1679;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(markup).toContain('data-m2v-content-layer="true"');
    expect(markup).toContain('data-m2v-content-offset-y="0" transform="translate(0 0)"');
    expect(markup).toContain('<rect x="220" y="520" width="708" height="670"');
    expect(markup).toContain('data-m2v-investment-title="true" x="540" y="270"');
    expect(markup).toContain('data-m2v-risk-disclaimer="true" x="140" y="1460"');
  });

  it.each([
    [9_999.999, '1 万元'],
    [10_000, '1 万元'],
    [100_000_000, '1 亿元'],
    [1_000_000_000_000, '1 万亿元'],
  ])('formats portfolio value and gain with Chinese magnitude units at %s', (value, expected) => {
    const largeValueProps: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, investment: { year: 2020, principal: 1 } },
      prices: { ...props.prices, points: [{ date: '2020-01-02', close: 1 }, { date: '2020-01-03', close: value }] },
    };
    testFrame.value = 1679;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...largeValueProps} />);
    expect(markup).toContain(`>${expected}</text>`);
    expect(markup).not.toContain('data-m2v-live-gain');
    expect(markup).toContain('data-m2v-value-axis-label="true"');
    expect(markup).not.toContain('B</text>');
    if (value >= 100_000_000_000) expect(markup).toContain('>1.08万亿</text>');
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
    expect(renderedTitle(markup)).toBe('假如你2020年按比例投资100元示例指数');
    expect(markup).toContain('data-m2v-investment-title="true" x="540" y="270" text-anchor="middle"');
    expect(markup).not.toContain('示例指数 · SYN');
    expect(markup).toContain('按点位比例模拟');
    expect(markup.match(/example\.invalid/g)).toHaveLength(1);
    expect(markup).toContain('market.example');
  });

  it('shrinks a long title to fit one line and blocks names that cannot remain readable', () => {
    const moderateName: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, instrument: { ...props.request.instrument, displayName: '中长名称'.repeat(2) } },
    };
    testFrame.value = 0;
    const markup = renderToStaticMarkup(<FinancialTimeSeries {...moderateName} />);
    expect(renderedTitle(markup)).toContain('买入100元');
    const titleFontSize = Number(markup.match(/data-m2v-investment-title="true"[^>]*font-size="([^"]+)"/u)?.[1]);
    expect(titleFontSize).toBeLessThan(48);
    expect(titleFontSize).toBeGreaterThanOrEqual(26);

    const longName: FinancialTimeSeriesProps = {
      ...props,
      request: { ...props.request, instrument: { ...props.request.instrument, displayName: '超长显示名称'.repeat(8) } },
    };
    expect(() => renderToStaticMarkup(<FinancialTimeSeries {...longName} />)).toThrow('投资假设标题过长');
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
    expect(markup).toContain('100元');
    expect(markup).not.toContain('99元');
    expect(markup).toContain('2020年4月1日');
    expect(markup).not.toContain('2020年4月3日');
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
    expect(opening.ticks.length).toBeGreaterThan(0);
    expect(opening.ticks).not.toEqual(final.ticks);
    expect(markupAt(1799)).toContain('data-m2v-visible-value-points="3"');
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
    expect(Number(financialView(1500, [], decades).ticks.at(-1)?.label)).toBeGreaterThan(2012);
    expect(financialView(1799, [], decades).ticks.map(({ label }) => label)).toContain('2026');
    const labelTrace = Array.from({ length: 1590 }, (_, index) => financialView(index + 90, [], decades).ticks.map(({ label }) => label));
    const labels = new Set(labelTrace.flat());
    for (const label of labels) {
      let visible = false;
      let appearances = 0;
      for (const frameLabels of labelTrace) {
        const current = frameLabels.includes(label);
        if (current && !visible) appearances++;
        visible = current;
      }
      expect(appearances, `year ${label} reappeared after disappearing`).toBeLessThanOrEqual(1);
    }
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
  it('matches Python v8 mapping on every frame and freezes the nonlinear ending', () => {
    const plan: FinancialTimeSeriesProps['plan'] = {
      ...props.plan, schemaVersion: 8,
      axis: { ...props.plan.axis, dateRange: ['1999-01-22', '2026-10-08'] },
      segments: [
        { frames: [0, 90], dates: ['1999-01-22', '1999-01-22'], kind: 'opening' },
        { frames: [90, 1620], dates: ['1999-01-22', '2026-10-08'], kind: 'advance' },
        { frames: [1620, 1800], dates: ['2026-10-08', '2026-10-08'], kind: 'ending' },
      ],
      pacing: { mode: 'volatility', anchors: [
        { frame: 90, date: '1999-01-22' }, { frame: 800, date: '2020-01-01' },
        { frame: 1400, date: '2023-01-01' }, { frame: 1619, date: '2026-10-08' },
      ] },
    };
    const python = execFileSync('uv', ['run', 'python', '-c',
      'import sys,json; from m2v.types.financial.financial import frame_date; p=json.load(sys.stdin); print(json.dumps([frame_date(p,f).isoformat() for f in range(1800)]))'],
      { cwd: '..', input: JSON.stringify(plan), encoding: 'utf8' });
    const expected: string[] = JSON.parse(python);
    const points = [{ date: '1999-01-22', close: 100 }, { date: '2020-01-01', close: 200 }, { date: '2026-10-08', close: 500 }];
    const ordered = expected.map((_, frame) => financialView(frame, points, plan, { year: 1999, principal: 100 }));
    for (let frame = 1799; frame >= 0; frame--) {
      const view = financialView(frame, points, plan, { year: 1999, principal: 100 });
      expect(view.currentDate).toBe(expected[frame]);
      expect(view).toEqual(ordered[frame]);
      if (frame > 0) expect(view.windowEndPosition).toBeGreaterThanOrEqual(ordered[frame - 1]!.windowEndPosition);
      expect(view.windowEndPosition).toBeGreaterThanOrEqual(view.position);
      if (frame >= 1620) expect(view).toEqual(ordered[1619]);
    }
    expect(ordered[1619]!.currentDate).toBe('2026-10-08');
    expect(ordered[1619]!.latest).toEqual(points[2]);
  });

  it('holds the final live-value layout unchanged throughout the ending', () => {
    testFrame.value = 885;
    const advance = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    expect(advance).toMatch(/data-m2v-live-year="true"[^>]*>2020<\/text>/u);
    expect(advance).toContain('font-size="64"');
    expect(advance).toContain('当前市值');
    expect(advance).not.toContain('收益率');

    testFrame.value = 1679;
    const lastAdvance = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    testFrame.value = 1680;
    const endingStart = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    testFrame.value = 1694;
    const endingAfterHalfSecond = renderToStaticMarkup(<FinancialTimeSeries {...props} />);
    testFrame.value = 1799;
    const endingLastFrame = renderToStaticMarkup(<FinancialTimeSeries {...props} />);

    expect(endingStart).toBe(lastAdvance);
    expect(endingAfterHalfSecond).toBe(lastAdvance);
    expect(endingLastFrame).toBe(lastAdvance);
    expect(lastAdvance).toContain('<text data-m2v-value-heading="true" x="940" y="330" text-anchor="end" fill="#b9c7d9" font-size="24">当前市值</text>');
    expect(lastAdvance).toContain('<text data-m2v-live-date="true" x="940" y="442"');
    expect(lastAdvance).toContain('2020年1月3日');
    expect(lastAdvance).not.toContain('本金 → 最终市值');
    expect(lastAdvance).not.toContain('100元 → 102元');
    expect(lastAdvance).not.toContain('累计收益率');
    expect(lastAdvance).not.toContain('opacity="0"');
  });

  it('completes axis expansion at the current boundary crossing, starting 15 frames earlier', () => {
    const plan: FinancialTimeSeriesProps['plan'] = {
      ...props.plan, schemaVersion: 8, axis: { ...props.plan.axis, dateRange: ['1999-01-22', '2026-10-08'] },
      segments: [
        { frames: [0, 90], dates: ['1999-01-22', '1999-01-22'], kind: 'opening' },
        { frames: [90, 1620], dates: ['1999-01-22', '2026-10-08'], kind: 'advance' },
        { frames: [1620, 1800], dates: ['2026-10-08', '2026-10-08'], kind: 'ending' },
      ],
      pacing: { mode: 'volatility', anchors: [{ frame: 90, date: '1999-01-22' }, { frame: 800, date: '2020-01-01' }, { frame: 1619, date: '2026-10-08' }] },
    };
    const current = epochDayForTest('2003-12-31');
    const next = epochDayForTest('2008-12-31');
    const crossing = Array.from({ length: 1530 }, (_, i) => i + 90).find(f => framePosition(f, plan) > current)!;
    expect(financialView(crossing - 16, [], plan).windowEndPosition).toBe(current);
    expect(financialView(crossing - 8, [], plan).windowEndPosition).toBeGreaterThan(current);
    expect(financialView(crossing - 8, [], plan).windowEndPosition).toBeLessThan(next);
    expect(financialView(crossing, [], plan).windowEndPosition).toBe(next);
  });

});
