/** 可数对象的通用布局：柱、行、网格与货架；题材专属的丘/取出组由作品实现。 */
import {tokens} from 'm2v/style';

export type Point = {x: number; y: number};

export type LayoutTokens = {
  disc: {pitch: number; gap: number};
};

const T = tokens as unknown as LayoutTokens;

/** 柱：从底向上叠放，间距小于直径，像一摞硬币。 */
export function column(x: number, baseY: number, count: number, pitch = T.disc.pitch): Point[] {
  return Array.from({length: count}, (_, index) => ({x, y: baseY - index * pitch}));
}

/** 一行圆片：从左到右等距。 */
export function row(count: number, x0: number, y: number, gap = T.disc.gap): Point[] {
  return Array.from({length: count}, (_, index) => ({x: x0 + index * gap, y}));
}

/** 网格：从左下开始，按行优先填充。 */
export function grid(count: number, x0: number, y0: number, cols: number, gap = T.disc.gap): Point[] {
  return Array.from({length: count}, (_, index) => ({
    x: x0 + (index % cols) * gap,
    y: y0 - Math.floor(index / cols) * gap,
  }));
}

/** 货架：从左到右、从下到上填充；用于“已离开系统”的分离堆放。 */
export function shelf(count: number, x0: number, y0: number, cols = 10, gap = T.disc.gap): Point[] {
  return Array.from({length: count}, (_, index) => ({
    x: x0 + (index % cols) * gap,
    y: y0 - Math.floor(index / cols) * gap,
  }));
}
