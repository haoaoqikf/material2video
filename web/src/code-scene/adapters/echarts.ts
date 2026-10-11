/**
 * ECharts 代码场景适配器：把图表逐帧更新约束成确定性渲染。
 *
 * 三条硬规则（缺一不可，见 openspec 变更 design.md）：
 * - **SVG renderer**：canvas 逐帧重绘依赖内部时钟合成，SVG 是纯 DOM 输出，
 *   同一 option 永远产出同一棵节点树；
 * - **动画强制关闭**：`animation` 系列在用户 option **之后**覆盖，
 *   作品写 `animation: true` 也翻不回来——入场动画一律由帧号驱动；
 * - **实例随组件生命周期**：挂载时 init、卸载时 dispose，帧更新走
 *   `setOption`（同步落盘，不用 lazyUpdate，避免异步合并把帧画错）。
 */
import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import type { EChartsOption, ECharts as EChartsInstance } from 'echarts';
import * as echarts from 'echarts';

/**
 * 强制帧驱动选项：无论作品写什么，动画与异步合并都被关死。
 * 放在展开之后写入，作品侧无法重新打开。
 */
export function freezeFrameOption(option: EChartsOption): EChartsOption {
  return {
    ...option,
    animation: false,
    animationDuration: 0,
    animationDurationUpdate: 0,
    animationDelay: 0,
    animationDelayUpdate: 0,
    stateAnimation: { duration: 0, easing: 'linear' },
  };
}

export interface M2VFrameChart {
  /** 挂载目标：作品把它 ref 到一个有尺寸的容器上。 */
  ref: RefObject<HTMLDivElement | null>;
  /** echarts 实例（初始化完成后才有）；一般不需要直接操作。 */
  instance: EChartsInstance | null;
}

/**
 * 帧驱动图表 Hook。
 *
 * ```tsx
 * const chart = useFrameChart(
 *   () => ({ xAxis: { type: 'category', data: labels }, series: [{ type: 'bar', data: values(progress) }] }),
 *   [progress, labels],
 * );
 * return <div ref={chart.ref} style={{ width: 800, height: 600 }} />;
 * ```
 *
 * `watch` 里出现的值变化会在**同一帧内**同步 `setOption`；
 * 初次挂载与卸载分别对应 init / dispose。
 */
export function useFrameChart(
  build: () => EChartsOption,
  watch: readonly unknown[] = [],
): M2VFrameChart {
  const ref = useRef<HTMLDivElement>(null);
  const [instance, setInstance] = useState<EChartsInstance | null>(null);
  // build 以 ref 保存：帧更新只依赖 watch 的值，不因闭包身份变化重建实例
  const buildRef = useRef(build);
  buildRef.current = build;

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const created = echarts.init(element, null, { renderer: 'svg' });
    created.setOption(freezeFrameOption(buildRef.current()));
    setInstance(created);
    return () => {
      created.dispose();
      setInstance(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 实例只随挂载生死
  }, []);

  useEffect(() => {
    if (!instance) return;
    instance.setOption(freezeFrameOption(buildRef.current()));
  }, [instance, ...watch]); // eslint-disable-line react-hooks/exhaustive-deps -- watch 由调用方声明

  return { ref, instance };
}
