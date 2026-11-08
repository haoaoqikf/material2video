/** 点列几何的唯一入口；样式、时间轴和业务刻度由调用方负责。 */
import {area, curveCatmullRomOpen, curveLinear, curveMonotoneX, curveStep, line, type CurveFactory} from 'd3-shape';

export type ChartPoint = readonly [number, number];
export type ChartCurve = 'linear' | 'monotone' | 'step' | 'catmull-rom';
const curves: Record<ChartCurve, CurveFactory> = {
  linear: curveLinear, monotone: curveMonotoneX, step: curveStep,
  // alpha=0 是原风格的均匀 Catmull-Rom，而非默认的向心参数化。
  'catmull-rom': curveCatmullRomOpen.alpha(0),
};

export function chartLinePath(points: readonly ChartPoint[], curve: ChartCurve = 'linear'): string {
  const data = curve === 'catmull-rom' && points.length ? [points[0], ...points, points[points.length - 1]] : points;
  return line<ChartPoint>().defined(p => p.every(Number.isFinite)).x(p => p[0]).y(p => p[1])
    .curve(curves[curve])(data) ?? '';
}

export function chartAreaPath(points: readonly ChartPoint[], baseline: number,
  curve: ChartCurve = 'linear'): string {
  const data = curve === 'catmull-rom' && points.length ? [points[0], ...points, points[points.length - 1]] : points;
  return area<ChartPoint>().defined(p => p.every(Number.isFinite)).x(p => p[0]).y0(baseline).y1(p => p[1])
    .curve(curves[curve])(data) ?? '';
}
