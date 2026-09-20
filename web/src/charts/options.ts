/**
 * 三种图表的 option 构造器：纯函数，输入（数据、切片、令牌色）决定输出。
 *
 * 为什么不把 option 写在组件里：任务 7.2 的验证要求「换分镜数据画面随之变化」
 * 与 7.1 要求「同一帧求值两次画面一致」——把构造器做成纯函数后，
 * 这两条都变成可直接断言的性质（同样输入两次构造结果逐值相等；
 * 换输入必有字段不同），不必为它们起浏览器。
 *
 * 颜色全部由调用方传入（组件在挂载时把 CSS 令牌解析成具体色值）：
 * canvas 不认识 `var(--fig-line)`，而令牌的解析结果随主题与预设变化，
 * 所以「读令牌」是组件挂载时做一次的测量，「用令牌」仍发生在这一层。
 */
import type { ChartOption } from './echarts';
import {
  lineSlice,
  valueExtent,
  type ChartPoint,
  type ChartType,
  type LinePoint,
} from './series';

/** 画面上会用到的令牌色。键与 `useTokenColors` 读的令牌名一一对应。 */
export interface ChartColors {
  /** 数据本体（柱面、折线、饼图主扇区） */
  accent: string;
  /** 强调色的深阶：饼图 ramp 的第二档 */
  accentDeep: string;
  /** 强调色的收尾阶：饼图 ramp 的第三档 */
  accentDeepSolid: string;
  /** 面填充：饼图 ramp 的过渡档 */
  water: string;
  /** 数据描边：饼图 ramp 的次要档 */
  lineData: string;
  /** 装饰描边：轴线、分隔线、饼图 ramp 的最弱档 */
  lineSoft: string;
  /** 图形内文本（轴标签、扇区名） */
  ink: string;
  /** 字体栈：canvas 不认 CSS 变量，由组件把解析结果传进来 */
  fontFamily: string;
}

/** 令牌名 → ChartColors 键。组件按这份表读取解析值。 */
export const CHART_COLOR_TOKENS: Record<keyof ChartColors, string> = {
  accent: '--a2v-accent',
  accentDeep: '--a2v-accent-deep',
  accentDeepSolid: '--a2v-accent-soft-solid',
  water: '--fig-water',
  lineData: '--fig-line-data',
  lineSoft: '--fig-line-soft',
  ink: '--fig-ink',
  fontFamily: '--a2v-font-sans',
};

/** 缺省色：令牌解析不到时用它们——与未启用预设时的默认值一致。 */
export const FALLBACK_COLORS: ChartColors = {
  accent: '#35e0c8',
  accentDeep: '#c2352a',
  accentDeepSolid: '#7d1c16',
  water: 'rgba(56, 132, 210, 0.22)',
  lineData: 'rgba(244, 247, 251, 0.44)',
  lineSoft: 'rgba(244, 247, 251, 0.16)',
  ink: '#e8eef6',
  fontFamily: "'A2V Sans', 'A2V Inter', sans-serif",
};

/**
 * 饼图的扇区色序：强调色打头，往后逐档变弱。
 * 一屏里饼图只有这一处用多色，色序固定才能保证「同数据同色」。
 */
const PIE_RAMP: ReadonlyArray<keyof ChartColors> = [
  'accent',
  'accentDeep',
  'water',
  'accentDeepSolid',
  'lineData',
  'lineSoft',
];

export function pieColors(colors: ChartColors, count: number): string[] {
  return Array.from({ length: count }, (_, index) => colors[PIE_RAMP[index % PIE_RAMP.length]!]);
}

/** 柱状图：轴固定，柱面随切片生长。 */
export function barOption(
  points: ChartPoint[],
  values: number[],
  extent: { min: number; max: number },
  colors: ChartColors,
): ChartOption {
  return {
    grid: CHART_GRID,
    xAxis: {
      type: 'category',
      data: points.map((point) => point.label),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: colors.lineSoft } },
      axisLabel: {
        color: colors.ink,
        fontFamily: colors.fontFamily,
        fontSize: AXIS_LABEL_PX,
        hideOverlap: true,
      },
    },
    yAxis: {
      type: 'value',
      min: extent.min,
      max: extent.max,
      splitLine: { lineStyle: { color: colors.lineSoft } },
      axisLabel: {
        color: colors.ink,
        fontFamily: colors.fontFamily,
        fontSize: AXIS_LABEL_PX,
      },
    },
    series: [
      {
        type: 'bar',
        data: values,
        barMaxWidth: BAR_MAX_WIDTH,
        itemStyle: { color: colors.accent, borderRadius: [6, 6, 0, 0] },
      },
    ],
  };
}

/**
 * 折线图：x 用数值轴，线头因此能落在两档之间连续生长；
 * 轴的刻度仍按档位标注（formatter 把下标映射回分镜里的标签）。
 */
export function lineOption(
  points: ChartPoint[],
  slice: LinePoint[],
  extent: { min: number; max: number },
  colors: ChartColors,
): ChartOption {
  return {
    grid: CHART_GRID,
    xAxis: {
      type: 'value',
      min: 0,
      max: Math.max(points.length - 1, 1),
      interval: 1,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: colors.lineSoft } },
      axisLabel: {
        color: colors.ink,
        fontFamily: colors.fontFamily,
        fontSize: AXIS_LABEL_PX,
        formatter: (value: number) => points[Math.round(value)]?.label ?? '',
      },
    },
    yAxis: {
      type: 'value',
      min: extent.min,
      max: extent.max,
      splitLine: { lineStyle: { color: colors.lineSoft } },
      axisLabel: {
        color: colors.ink,
        fontFamily: colors.fontFamily,
        fontSize: AXIS_LABEL_PX,
      },
    },
    series: [
      {
        type: 'line',
        data: slice.map((item) => ({
          value: [item.x, item.y],
          symbol: item.tip ? 'none' : 'circle',
          symbolSize: SYMBOL_SIZE,
        })),
        lineStyle: { color: colors.accent, width: LINE_WIDTH },
        itemStyle: { color: colors.accent },
      },
    ],
  };
}

/** 饼图：扇区随切片张开，半径固定（半径跟着数值变的饼图读不出占比）。 */
export function pieOption(
  points: ChartPoint[],
  values: number[],
  colors: ChartColors,
): ChartOption {
  return {
    series: [
      {
        type: 'pie',
        radius: PIE_RADIUS,
        center: PIE_CENTER,
        data: points.map((point, index) => ({
          name: point.label,
          value: values[index] ?? 0,
          itemStyle: { color: pieColors(colors, points.length)[index] },
        })),
        label: {
          color: colors.ink,
          fontFamily: colors.fontFamily,
          fontSize: AXIS_LABEL_PX,
          formatter: '{b}',
        },
        labelLine: { lineStyle: { color: colors.lineSoft } },
        padAngle: 1.5,
      },
    ],
  };
}

/** 按 `data.chart` 分发。switch 写全三种，漏一种会被 TS 的穷尽检查挡住。 */
export function buildChartOption(
  type: ChartType,
  points: ChartPoint[],
  reveals: number[],
  colors: ChartColors,
): ChartOption {
  const extent = valueExtent(points);
  switch (type) {
    case 'bar':
      return barOption(points, barSliceOf(points, reveals), extent, colors);
    case 'line':
      return lineOption(points, lineSlice(points, reveals), extent, colors);
    case 'pie':
      return pieOption(points, pieSliceOf(points, reveals), colors);
  }
}

function barSliceOf(points: ChartPoint[], reveals: number[]): number[] {
  return points.map((point, index) => point.value * (reveals[index] ?? 0));
}

function pieSliceOf(points: ChartPoint[], reveals: number[]): number[] {
  return barSliceOf(points, reveals);
}

/** 画布内边距：给轴标签与扇区名留位，数值区不被裁切。 */
const CHART_GRID = { left: 96, right: 72, top: 48, bottom: 96, containLabel: false } as const;

const AXIS_LABEL_PX = 30;
const BAR_MAX_WIDTH = 96;
const SYMBOL_SIZE = 14;
const LINE_WIDTH = 6;
const PIE_RADIUS = '58%';
const PIE_CENTER: [string, string] = ['50%', '46%'];
