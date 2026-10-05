import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { FinancialTimeSeries, type FinancialTimeSeriesProps } from './FinancialTimeSeries';

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
    axis: { dateRange: ['2020-01-01', '2020-01-03'], valueRange: [90, 110] },
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
});
