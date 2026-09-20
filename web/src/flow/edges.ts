/**
 * flow 连线的几何：折线路径、箭镞与总长度（任务 8.3 的「长度只测一次」那半）。
 *
 * 全部是**纯几何计算**，没有一个函数碰 DOM：
 *
 * - 连线画成折线（dagre 返回的点串直接连起来）。不追 bezier 圆角：
 *   直角转折在「因果 / 步骤」这类语义里反而清楚，而且折线长度是**解析值**
 *   （各段长度之和），不需要 `getTotalLength()`——那是隐藏元素才量得到的东西，
 *   而描边进度每帧都要用总长度，逐帧去量等于逐帧重排。
 * - 箭镞是一个实心三角形，顶点落在目标节点边框上；线段在箭镞底部截断，
 *   否则线会从三角里穿出来。
 *
 * 长度在布局确定时算一次并随布局缓存（`FlowLayout` 的消费方把
 * `edgeGeometry.length` 与 `path` 一起记住），每帧只按进度算
 * `stroke-dasharray` / `stroke-dashoffset`（`drawPathStyle` 原语）——
 * 这就是「长度只测一次并缓存、每帧不做实时测量」的落法。
 */
import type { FlowPoint } from './layout';

/** 箭镞的尺寸（px，布局坐标系）。令牌 `--fig-arrow-len` / `--fig-arrow-half`
 * 的兜底值（tokens.css 第 330–331 行）；与飞轮节点半径同理：参与几何计算、
 * 必须落成 SVG 坐标的部分取兜底值，令牌名与取值注明在此。 */
export const FLOW_ARROW = {
  /** 箭镞长度（沿连线方向） */
  LEN: 34,
  /** 箭镞半高（垂直连线方向） */
  HALF: 16,
} as const;

/** 折线 `d` 属性：点串直接连起来，坐标保留两位小数（与旧实现同一精度）。 */
export function polylinePath(points: readonly FlowPoint[]): string {
  if (points.length === 0) {
    return '';
  }
  const parts = points.map(
    (point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(2)} ${point.y.toFixed(2)}`,
  );
  return parts.join(' ');
}

/** 两点的欧氏距离。 */
function distance(a: FlowPoint, b: FlowPoint): number {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

/** 折线总长度：各段长度之和（解析值，不是量出来的）。 */
export function polylineLength(points: readonly FlowPoint[]): number {
  let total = 0;
  for (let index = 1; index < points.length; index += 1) {
    total += distance(points[index - 1]!, points[index]!);
  }
  return total;
}

/**
 * 把折线的末端截掉 `cut` 长度：箭镞要占住最后一段，线不能从它底下穿出去。
 *
 * 从终点往回走 `cut`，落在哪一段就断在哪一段；`cut` 比整条线还长时
 * 只返回第一个点（退化成点，画不出来也不抛错——长度是调用方算的，
 * 这里只保证不产生 NaN）。
 */
export function trimPolylineEnd(points: readonly FlowPoint[], cut: number): FlowPoint[] {
  if (points.length < 2 || cut <= 0) {
    return [...points];
  }
  let remaining = cut;
  const out: FlowPoint[] = [];
  for (let index = 0; index < points.length - 1; index += 1) {
    const from = points[index]!;
    const to = points[index + 1]!;
    const segment = distance(from, to);
    if (segment <= remaining) {
      remaining -= segment;
      continue;
    }
    const t = 1 - remaining / segment;
    const head = { x: from.x + (to.x - from.x) * t, y: from.y + (to.y - from.y) * t };
    out.push(from, ...points.slice(index + 1, points.length - 1), head);
    return out;
  }
  // 剩余长度吃掉了整条折线：只剩起点（画不出线，箭镞也顶在起点上）
  return [points[0]!];
}

/** 沿折线末端方向放置的箭镞三角形：返回三角形的三个顶点。 */
export function arrowHead(points: readonly FlowPoint[]): FlowPoint[] {
  const tip = points[points.length - 1]!;
  const before = points[points.length - 2] ?? tip;
  const dx = tip.x - before.x;
  const dy = tip.y - before.y;
  const length = Math.hypot(dx, dy);
  if (length === 0) {
    // 退化（重合点）：画不出方向的箭镞就不画
    return [tip, tip, tip];
  }
  const ux = dx / length;
  const uy = dy / length;
  // 垂直方向（左手旋转 90°）
  const vx = -uy;
  const vy = ux;
  const baseX = tip.x - ux * FLOW_ARROW.LEN;
  const baseY = tip.y - uy * FLOW_ARROW.LEN;
  return [
    { x: tip.x, y: tip.y },
    { x: baseX + vx * FLOW_ARROW.HALF, y: baseY + vy * FLOW_ARROW.HALF },
    { x: baseX - vx * FLOW_ARROW.HALF, y: baseY - vy * FLOW_ARROW.HALF },
  ];
}

/** 一条连线画到进度 `p` 时需要的全部几何（布局确定时算好，逐帧复用）。 */
export interface FlowEdgeGeometry {
  /** 线的 `d`（已按箭镞截短） */
  path: string;
  /** 线的解析总长度（描边原语的输入） */
  length: number;
  /** 箭镞三角形的三个顶点 */
  arrow: FlowPoint[];
}

/**
 * 由布局点串算出一条连线的全部几何。
 *
 * 调用方（flow 组件）在布局变化时对每条边调一次，结果随布局一起进 useMemo；
 * 每帧只把帧号换算成进度，然后 `drawPathStyle(progress, geometry.length)`。
 */
export function edgeGeometry(points: readonly FlowPoint[]): FlowEdgeGeometry {
  const length = polylineLength(points);
  const arrow = arrowHead(points);
  const trimmed = trimPolylineEnd(points, FLOW_ARROW.LEN * 0.9);
  return {
    path: polylinePath(trimmed),
    length: Math.max(length - FLOW_ARROW.LEN * 0.9, 1),
    arrow,
  };
}
