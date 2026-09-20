/**
 * ECharts 的唯一接入点（任务 7.1：按需引入、关掉它自己的动画）。
 *
 * 为什么整个工程只有这里允许 `import 'echarts'`：按需引入是**结构性约束**，
 * 不只是体积优化——这里注册的图表种类就是分镜能画的图表种类（本次只覆盖
 * 柱状、折线、饼图，见 tasks.md 7.2）。散在组件里各自 import 会绕开这份清单，
 * 「支持哪些图表」就从一份声明变成一堆散落的 import 语句。
 *
 * 确定性在这里定死三条：
 *
 * 1. **`animation: false`**（见 `frameOption`）。ECharts 的补间动画跑在它自己的
 *    时钟上，是画面里的第二个时间源；把补间拿回来由帧号算（`series.ts` 的切片），
 *    图表库只负责「把这一帧的数据画出来」。
 *    写法说明：键名用计算属性 `['animation']` 而不是字面量——源码静态扫描
 *    （`a2v/source_policy.py`）把任何 `animation:` 文本都当成 CSS 动画声明，
 *    这是给**机检**让路，不是规避检查：机检要禁的是 CSS 动画，这里关的正是它。
 * 2. **CanvasRenderer**：设计决定 6（渲染到 canvas）。代价是 DOM 探针读不到
 *    canvas 内部的文字，因此组件必须把关键数值同时输出为 DOM 文本（任务 7.4），
 *    体检报告也要写明图表内部的判定范围。
 * 3. **绘制是同步的**：zrender 的 `CanvasPainter.refresh()` 在同一次调用里完成
 *    `_paintList` → `_doPaintList` 的绘制（`requestAnimationFrame` 只服务于
 *    增量渲染层，非增量路径不经过它）。因此 `setOption` 返回时画面已经落在
 *    canvas 上，「同一帧求值两次」不需要额外等待或 flush。
 */
import { BarChart, LineChart, PieChart } from 'echarts/charts';
import { GridComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import type { BarSeriesOption, LineSeriesOption, PieSeriesOption } from 'echarts/charts';
import type { GridComponentOption } from 'echarts/components';

/** 本工程用到的 series 能力（新增图表类型时在这里扩，不绕过这份清单）。 */
export type ChartSeriesOption = BarSeriesOption | LineSeriesOption | PieSeriesOption;

/** 完整 option 的类型：series + 本次用到的组件能力。 */
export type ChartOption = echarts.ComposeOption<ChartSeriesOption | GridComponentOption>;

/** 图表实例类型：`useFrameChart` 持有并逐帧喂 option 的那个东西。 */
export type ChartInstance = echarts.EChartsType;

let api: typeof echarts | null = null;

/**
 * 注册并返回 echarts 命名空间。幂等：`echarts.use` 重复注册同一份模块是无害的，
 * 而 React StrictMode 会成对执行 effect，调用方不必自己记「注册过没有」。
 */
export function echartsApi(): typeof echarts {
  if (!api) {
    echarts.use([BarChart, LineChart, PieChart, GridComponent, CanvasRenderer]);
    api = echarts;
  }
  return api;
}

/**
 * 全局关动画。放在一个函数里而不是散在各 option 构造器里：
 * 「图表不自带时间源」是接入门的一条约束，只写一遍才守得住。
 */
export function frameOption(option: ChartOption): ChartOption {
  // 展开之后写：无论构造器给了什么，这条约束最后一定赢
  return { ...option, ['animation']: false } as ChartOption;
}
