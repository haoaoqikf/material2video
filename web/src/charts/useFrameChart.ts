/**
 * 把 ECharts 实例的生命周期钉在「这一幕可见」上，并逐帧喂 option。
 *
 * 三个决定，每一条都服务于「画面是帧号的纯函数」：
 *
 * 1. **只在幕可见时持有实例**（`active` 门控）。契约页里所有幕都留在 DOM、
 *    用 `display: none` 切换——隐藏的元素量出来是 0，而 ECharts 挂在
 *    0 尺寸的容器上会得到一块 0 尺寸的画布。切幕即初始化/销毁，
 *    每次出现的首帧都由当帧 option 完整重画一遍，不依赖上一次的状态。
 * 2. **每帧 `setOption({ notMerge: true })`**。整份 option 由帧号推出
 *    （`options.ts` 是纯函数），整份替换意味着实例不携带任何跨帧状态——
 *    随机访问第 N 帧与顺序播放到第 N 帧给同一块画布。
 * 3. **不做 resize 跟随**。渲染与体检都在固定尺寸的页面里进行；
 *    容器尺寸变化的那条路（预览时拖窗口）不参与成片，也没有判定挂在它上面。
 *    为它引入每帧的布局读取，违背「不读实时布局」的既有纪律。
 *
 * effect 的顺序即初始化顺序：挂载 effect（本文件的 init）声明在前，
 * 喂 option 的 effect 声明在后，同一次 commit 里先 init 后 setOption。
 */
import { useLayoutEffect, useRef, type RefObject } from 'react';

import { echartsApi, frameOption, type ChartInstance, type ChartOption } from './echarts';

export function useFrameChart(
  option: ChartOption | null,
  active: boolean,
): RefObject<HTMLDivElement | null> {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ChartInstance | null>(null);

  // 挂载/销毁：跟「这一幕可见」走，而不是跟组件挂载走
  useLayoutEffect(() => {
    const host = hostRef.current;
    if (!host || !active) {
      return;
    }
    if (host.clientWidth === 0 || host.clientHeight === 0) {
      // 还没有布局尺寸（理论上只在刚切入的一瞬间可能发生）：等下一帧再挂，
      // 0 尺寸实例画不出东西，留着只会让「图在哪」变得不可解释
      return;
    }
    const echarts = echartsApi();
    const chart = echarts.init(host, undefined, { renderer: 'canvas' });
    chartRef.current = chart;
    return () => {
      chartRef.current = null;
      echarts.dispose(host);
    };
  }, [active]);

  // 逐帧喂 option：option 由帧号推出，每帧都是一份新的完整描述
  useLayoutEffect(() => {
    const chart = chartRef.current;
    if (!chart || !option) {
      return;
    }
    chart.setOption(frameOption(option), { notMerge: true });
  }, [option]);

  return hostRef;
}
