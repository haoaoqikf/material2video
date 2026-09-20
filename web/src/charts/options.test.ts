/**
 * option 构造器的确定性断言：同一输入两次构造逐值相等，
 * 换输入必有字段不同（任务 7.1 / 7.2 的验证要求在这里变成可机检的性质）。
 *
 * 另一条被钉住的是「轴不参与动画」：series 的数据随帧变，
 * 轴的范围必须钉在完整数据上——否则柱子还没长、刻度先在动，
 * 观众每帧读到的数值参照系都不一样。
 */

import { describe, expect, it } from 'vitest';

import { frameOption, type ChartOption } from '@/charts/echarts';
import { buildChartOption, FALLBACK_COLORS } from '@/charts/options';
import { revealProgresses, type ChartPoint } from '@/charts/series';

const POINTS: ChartPoint[] = [
  { label: '四月', value: 12 },
  { label: '五月', value: 30 },
  { label: '六月', value: 18 },
];

const COLORS = FALLBACK_COLORS;

function seriesData(option: ChartOption): unknown {
  const series = option.series as Array<{ data?: unknown }> | undefined;
  return series?.[0]?.data;
}

describe('buildChartOption：确定性', () => {
  it('同一帧两次构造逐值相等', () => {
    const first = buildChartOption('bar', POINTS, revealProgresses({ localFrame: 40, sceneDurationFrames: 180, motion: 'normal' }, POINTS.length), COLORS);
    const second = buildChartOption('bar', POINTS, revealProgresses({ localFrame: 40, sceneDurationFrames: 180, motion: 'normal' }, POINTS.length), COLORS);
    expect(first).toEqual(second);
  });

  it('换帧必有字段不同：图表内容随帧号变化', () => {
    const early = buildChartOption('bar', POINTS, revealProgresses({ localFrame: 0, sceneDurationFrames: 180, motion: 'normal' }, POINTS.length), COLORS);
    const late = buildChartOption('bar', POINTS, revealProgresses({ localFrame: 170, sceneDurationFrames: 180, motion: 'normal' }, POINTS.length), COLORS);
    expect(early).not.toEqual(late);
    expect(seriesData(early)).not.toEqual(seriesData(late));

    const earlyLine = buildChartOption('line', POINTS, revealProgresses({ localFrame: 0, sceneDurationFrames: 180, motion: 'normal' }, POINTS.length), COLORS);
    const lateLine = buildChartOption('line', POINTS, revealProgresses({ localFrame: 170, sceneDurationFrames: 180, motion: 'normal' }, POINTS.length), COLORS);
    expect(earlyLine).not.toEqual(lateLine);

    const earlyPie = buildChartOption('pie', POINTS, revealProgresses({ localFrame: 0, sceneDurationFrames: 180, motion: 'normal' }, POINTS.length), COLORS);
    const latePie = buildChartOption('pie', POINTS, revealProgresses({ localFrame: 170, sceneDurationFrames: 180, motion: 'normal' }, POINTS.length), COLORS);
    expect(earlyPie).not.toEqual(latePie);
  });

  it('换分镜数据画面随之变化：数值列换一组，series 数据整体不同', () => {
    const other: ChartPoint[] = [
      { label: '周一', value: 3 },
      { label: '周二', value: 9 },
    ];
    const full = [1, 1];
    expect(seriesData(buildChartOption('bar', POINTS, full, COLORS))).not.toEqual(
      seriesData(buildChartOption('bar', other, full, COLORS)),
    );
  });

  it('动画被全局关闭：构造层忘了关也会被 frameOption 压回去', () => {
    for (const type of ['bar', 'line', 'pie'] as const) {
      const option = frameOption(
        buildChartOption(type, POINTS, [1, 1, 1], COLORS),
      );
      expect((option as { animation?: unknown }).animation).toBe(false);
    }
  });
});

describe('轴不参与动画', () => {
  it('柱状：x 轴类目与 y 轴范围在两帧之间完全一致', () => {
    const early = buildChartOption('bar', POINTS, [0, 0, 0], COLORS);
    const late = buildChartOption('bar', POINTS, [1, 1, 1], COLORS);
    const earlyAxis = early.xAxis as { data?: string[] };
    const lateAxis = late.xAxis as { data?: string[] };
    expect(earlyAxis.data).toEqual(POINTS.map((point) => point.label));
    expect(earlyAxis.data).toEqual(lateAxis.data);
    const earlyY = early.yAxis as { max?: number };
    const lateY = late.yAxis as { max?: number };
    expect(earlyY.max).toBe(lateY.max);
  });

  it('折线：x 轴上限钉在点数上，刻度映射回分镜标签', () => {
    const option = buildChartOption('line', POINTS, [1, 1, 1], COLORS);
    const axisLabel = (
      option.xAxis as {
        max?: number;
        axisLabel?: { formatter?: (value: number) => string };
      }
    ).axisLabel;
    expect(
      (option.xAxis as { max?: number }).max,
    ).toBe(POINTS.length - 1);
    expect(axisLabel?.formatter?.(1)).toBe('五月');
  });

  it('饼图：扇区色序固定，同数据同色；半径不随数值变化', () => {
    const full = buildChartOption('pie', POINTS, [1, 1, 1], COLORS);
    const series = (
      full.series as Array<{
        radius?: string;
        data?: Array<{ name: string; itemStyle?: { color?: string } }>;
      }>
    )[0]!;
    expect(series.radius).toBe('58%');
    expect(series.data?.map((item) => item.name)).toEqual(['四月', '五月', '六月']);
    // 同下标的扇区在两次构造里颜色一致：色序是常量，不随显影进度漂移
    const again = buildChartOption('pie', POINTS, [1, 1, 1], COLORS);
    const againSeries = (
      again.series as Array<{ data?: Array<{ itemStyle?: { color?: string } }> }>
    )[0]!;
    expect(series.data?.map((item) => item.itemStyle?.color)).toEqual(
      againSeries.data?.map((item) => item.itemStyle?.color),
    );
  });
});
