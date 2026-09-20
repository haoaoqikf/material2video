/**
 * 令牌 → canvas 色值的一次性解析（任务 7.2 的「颜色一律引用令牌」在 canvas 上的落法）。
 *
 * ECharts 画在 canvas 上，而 canvas 的绘制上下文不认识 `var(--fig-line)`——
 * 必须把令牌**解析后的值**喂给它。解析结果只随主题与预设变化，
 * 这两者在一幕之内不变，因此「这一幕可见时读一次」就够：
 * 测量发生在激活的那一刻（首次 seek 之后），此时 `data-a2v-theme` /
 * `data-a2v-preset` 已经由 composition 写在根元素上，读到的是本片的主题。
 *
 * 挂在根元素上读而不是组件自己的节点：令牌定义与覆写都写在
 * `:root` / `[data-a2v-preset]` 作用域上，那里才是它们的真源。
 */
import { useLayoutEffect, useState } from 'react';

import { CHART_COLOR_TOKENS, FALLBACK_COLORS, type ChartColors } from './options';

const COLOR_KEYS = Object.keys(CHART_COLOR_TOKENS) as Array<keyof ChartColors>;

function sameColors(left: ChartColors, right: ChartColors): boolean {
  return COLOR_KEYS.every((key) => left[key] === right[key]);
}

export function useTokenColors(active: boolean): ChartColors {
  const [colors, setColors] = useState<ChartColors>(FALLBACK_COLORS);
  useLayoutEffect(() => {
    if (!active || typeof document === 'undefined') {
      return;
    }
    const style = getComputedStyle(document.documentElement);
    const next = {} as ChartColors;
    for (const key of COLOR_KEYS) {
      const value = style.getPropertyValue(CHART_COLOR_TOKENS[key]).trim();
      // 解析不到（令牌被改名/删除）时落回默认值：画面不变丑，但
      // `tests/test_web_charts.py` 会盯住「用到的令牌名都存在」这件事
      next[key] = value || FALLBACK_COLORS[key];
    }
    setColors((previous) => (sameColors(previous, next) ? previous : next));
  }, [active]);
  return colors;
}
