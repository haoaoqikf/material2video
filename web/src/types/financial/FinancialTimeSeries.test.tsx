import {renderToStaticMarkup} from 'react-dom/server';
import {describe, expect, it, vi} from 'vitest';
import {FinancialTimeSeries, financialView, framePosition, type FinancialTimeSeriesProps} from './FinancialTimeSeries';

const current = vi.hoisted(() => ({frame: 0}));
vi.mock('../../code-scene/context', () => ({
  useSceneContext: () => ({elapsedSeconds: current.frame / 30}),
}));

const props: FinancialTimeSeriesProps = {
  request: {instrument: {kind: 'stock', name: '合成公司', code: 'SYN', market: 'TEST', unit: 'USD'},
    displayRange: ['2020-01-01', '2020-01-03'], investment: {year: 2020, principal: 100}},
  prices: {schemaVersion: 3, points: [{date: '2020-01-02', close: 100}, {date: '2020-01-03', close: 102}],
    unit: 'USD', priceBasis: 'split-adjusted', adjustmentDefinition: '仅拆合股调整',
    sources: [{url: 'https://example.invalid/prices'}]},
  plan: {schemaVersion: 8, chartType: 'line', durationSeconds: 15, fps: 30,
    canvas: {width: 1080, height: 1920},
    axis: {dateRange: ['2020-01-01', '2020-01-03'], dateScale: 'staged-expanding', valueScale: 'revealed-linear'},
    segments: [
      {frames: [0, 30], dates: ['2020-01-01', '2020-01-01'], kind: 'opening'},
      {frames: [30, 390], dates: ['2020-01-01', '2020-01-03'], kind: 'advance'},
      {frames: [390, 450], dates: ['2020-01-03', '2020-01-03'], kind: 'ending'},
    ],
    pacing: {mode: 'uniform', anchors: [{frame: 30, date: '2020-01-01'}, {frame: 389, date: '2020-01-03'}]},
    rationale: '测试夹具'},
  durationInFrames: 450, fps: 30, width: 1080, height: 1920,
};

describe('金融来源场景', () => {
  it('按保存的锚点映射关键帧，seek 顺序不改变数值', () => {
    const frames = [0, 30, 180, 389, 449];
    const first = frames.map(frame => framePosition(frame, props.plan));
    const reversed = [...frames].reverse().map(frame => framePosition(frame, props.plan)).reverse();
    expect(first).toEqual(reversed);
    expect(first[0]).toBe(first[1]);
    expect(first[3]).toBe(first[4]);
    expect(first[3]).toBeGreaterThan(first[2]!);
  });

  it('只在真实收盘价到达后更新投资市值', () => {
    const opening = financialView(0, props.prices.points, props.plan, props.request.investment!);
    const ending = financialView(449, props.prices.points, props.plan, props.request.investment!);
    expect(opening.latest).toBeNull();
    expect(ending.latest?.date).toBe('2020-01-03');
    expect(ending.visiblePoints).toHaveLength(2);
  });

  it('按当前代码场景帧绘制标题、折线和结尾数值', () => {
    current.frame = 449;
    const a = renderToStaticMarkup(<FinancialTimeSeries {...props}/>);
    const b = renderToStaticMarkup(<FinancialTimeSeries {...props}/>);
    expect(a).toBe(b);
    expect(a).toContain('data-m2v-investment-subject');
    expect(a).toContain('data-m2v-summary');
    expect(a).toContain('<path');
  });
});
