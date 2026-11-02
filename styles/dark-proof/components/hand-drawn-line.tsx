/**
 * 手绘描线：按显式进度画出外部传入的 path。
 *
 * 默认用 `samplePath` 采样 + `perfect-freehand` 生成锥形手绘笔触；多子路径或
 * 采样失败时回退到普通 SVG 描边。回退路径的生长由共享的 `@remotion/paths`
 * 封装计算；路径与题材留在作品内，组件不读挂钟、不用滤镜或计时器。
 */
import {useMemo} from 'react';
import {getStroke, pathDrawProps, polygonPath, samplePath} from 'm2v/code-scene';
export type HandDrawnLineProps = {
  d: string;
  color?: string;
  width?: number;
  progress?: number;
  opacity?: number;
  /** 第二层淡笔的横向错位；0 时关闭双层。 */
  ghostOffset?: number;
  /** 只画轮廓的虚线；仍由进度控制生长。 */
  dashed?: boolean;
  /** 使用锥形手绘笔触；关闭时退化为普通描边。 */
  freehand?: boolean;
};

export default function HandDrawnLine({
  d, color = '#F3EDDC', width = 9, progress = 1, opacity = 1, ghostOffset = 1.4,
  dashed = false, freehand = true,
}: HandDrawnLineProps) {
  const value = Math.min(1, Math.max(0, progress));
  const sampled = useMemo(() => {
    if (!freehand || dashed || !d.trim()) return null;
    try {
      return samplePath(d, 140);
    } catch {
      return null;
    }
  }, [d, dashed, freehand]);
  const freehandPath = useMemo(() => {
    if (!sampled || sampled.length < 2 || value <= 0) return '';
    const visible = Math.max(2, Math.ceil(sampled.length * value));
    const stroke = getStroke(
      sampled.slice(0, visible).map(point => ({x: point.x, y: point.y, pressure: 1})),
      {
        size: width, thinning: 0.45, smoothing: 0.6, streamline: 0.35,
        simulatePressure: false, start: {taper: 0, cap: true},
        end: {taper: Math.max(1, width * 1.4), cap: true},
      },
    );
    return polygonPath(stroke.map(([x, y]) => ({x, y})));
  }, [sampled, width, value]);
  if (!d || value <= 0) return null;
  if (sampled && freehandPath) {
    return (
      <g opacity={opacity}>
        {ghostOffset !== 0 ? (
          <g transform={`translate(${ghostOffset} ${-ghostOffset * 0.6})`} opacity={0.28}>
            <path d={freehandPath} fill={color}/>
          </g>
        ) : null}
        <path d={freehandPath} fill={color}/>
      </g>
    );
  }
  const dash = dashed ? '0.014 0.012' : '1';
  const draw = dashed
    ? {pathLength: 1, strokeDasharray: dash, strokeDashoffset: 0}
    : pathDrawProps(d, value);
  return (
    <g opacity={opacity}>
      {ghostOffset !== 0 ? (
        <g transform={`translate(${ghostOffset} ${-ghostOffset * 0.6})`} opacity={0.32}>
          <path d={d} fill="none" stroke={color} strokeWidth={Math.max(1, width * 0.55)}
            strokeLinecap="round" strokeLinejoin="round" {...draw}/>
        </g>
      ) : null}
      <path d={d} fill="none" stroke={color} strokeWidth={width}
        strokeLinecap="round" strokeLinejoin="round" {...draw}/>
    </g>
  );
}
