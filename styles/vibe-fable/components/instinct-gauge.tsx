/**
 * 本能读数仪表：左上角的半圆表盘，0–150，过 100 进红区并标「超常」。
 *
 * 它是全片的一把尺子：同一读数在不同场景里可比较。指针与读数只由 `value`
 * 与 `frame` 的插值决定，不做装饰性摆动。
 */
import {useId} from 'react';
import {T, alpha, color, frameProgress} from './kit';

export type InstinctGaugeProps = {
  /** 目标读数；与 `startValue` 之间按 `frame` 插值。 */
  value: number;
  /** 起始读数；省略时等于 `value`（不播动画）。 */
  startValue?: number;
  /** 被测对象名，面板下一行黑体小字。 */
  object: string;
  frame: number;
  /** 插值起止帧；省略时直接显示 `value`。 */
  startFrame?: number;
  durationFrames?: number;
  /** 面板可见度。 */
  opacity?: number;
  x?: number;
  y?: number;
  role?: string;
  state?: string;
};

const ARC_START = Math.PI;
const ARC_END = 0;

function pointOnArc(cx: number, cy: number, radius: number, t: number): [number, number] {
  const angle = ARC_START + (ARC_END - ARC_START) * t;
  return [cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius];
}

function arcPath(cx: number, cy: number, radius: number, from: number, to: number): string {
  const [x0, y0] = pointOnArc(cx, cy, radius, from);
  const [x1, y1] = pointOnArc(cx, cy, radius, to);
  const large = Math.abs(to - from) > 0.5 ? 1 : 0;
  return `M ${x0.toFixed(2)},${y0.toFixed(2)} A ${radius},${radius} 0 ${large} 1 ${x1.toFixed(2)},${y1.toFixed(2)}`;
}

export default function InstinctGauge({
  value, startValue, object, frame, startFrame = 0, durationFrames = 0,
  opacity = 1, x = T.layout.gauge.x, y = T.layout.gauge.y, role, state,
}: InstinctGaugeProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const {min, max, redFrom, ticks, label, overLabel} = T.gauge;
  const progress = durationFrames > 0 ? frameProgress(frame, startFrame, durationFrames) : 1;
  const from = startValue ?? value;
  const current = from + (value - from) * progress;
  const ratio = Math.min(1, Math.max(0, (current - min) / (max - min)));
  const redRatio = Math.min(1, Math.max(0, (redFrom - min) / (max - min)));
  const width = T.layout.gauge.width;
  const height = T.layout.gauge.height;
  const cx = width / 2;
  const cy = height * 0.62;
  const radius = Math.min(width * 0.42, height * 0.5);
  const over = current >= redFrom;
  const readoutColor = over ? color('red') : color('gold');
  const [needleX, needleY] = pointOnArc(cx, cy, radius * 0.86, ratio);
  return (
    <div data-m2v-role={role} data-m2v-state={state} style={{
      position: 'absolute', left: x, top: y, width, height, opacity,
      borderRadius: 22, background: alpha(T.colors.panel, 0.9),
      boxShadow: '0 6px 22px rgba(0,0,0,.28)', pointerEvents: 'none',
      overflow: 'hidden',
    }}>
      <svg width={width} height={height * 0.78} viewBox={`0 0 ${width} ${height * 0.78}`}>
        <path d={arcPath(cx, cy, radius, 0, 1)} fill="none" stroke={alpha(color('dim'), 0.35)} strokeWidth={10}
          strokeLinecap="round"/>
        <path d={arcPath(cx, cy, radius, redRatio, 1)} fill="none" stroke={color('red')} strokeWidth={10}
          strokeLinecap="round"/>
        <line x1={cx} y1={cy} x2={needleX} y2={needleY} stroke={readoutColor} strokeWidth={5} strokeLinecap="round"/>
        <circle cx={cx} cy={cy} r={7} fill={readoutColor}/>
        {ticks.map(tick => {
          const t = (tick - min) / (max - min);
          const [tx0, ty0] = pointOnArc(cx, cy, radius - 16, t);
          const [tx1, ty1] = pointOnArc(cx, cy, radius - 4, t);
          return <line key={tick} x1={tx0} y1={ty0} x2={tx1} y2={ty1} stroke={alpha(color('dim'), 0.55)} strokeWidth={2}/>;
        })}
      </svg>
      <div style={{
        position: 'absolute', left: 0, right: 0, top: height * 0.3, textAlign: 'center',
        fontFamily: T.type.fontStack, fontSize: T.type.gaugeReadout, fontWeight: 700,
        color: readoutColor, lineHeight: 1, fontVariantNumeric: 'tabular-nums',
      }}>{Math.round(current)}</div>
      <div style={{
        position: 'absolute', left: 18, top: 12, fontFamily: T.type.fontStack,
        fontSize: 22, letterSpacing: '0.08em', color: alpha(color('ink'), 0.8),
      }}>{label}</div>
      <div style={{
        position: 'absolute', right: 18, top: 14, fontFamily: T.type.fontStack,
        fontSize: 20, letterSpacing: '0.1em', color: alpha(color('red'), over ? 1 : 0.5),
      }}>{overLabel}</div>
      <div style={{
        position: 'absolute', left: 18, right: 18, bottom: 8, fontFamily: T.type.fontStack,
        fontSize: T.type.gaugeObject, color: alpha(color('ink'), 0.72), whiteSpace: 'nowrap',
        overflow: 'hidden', textOverflow: 'ellipsis',
      }}>对象：{object}</div>
    </div>
  );
}
