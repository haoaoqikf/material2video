/**
 * 光轨：沿外部点列生长的锥形尾迹 + 头部光晕 + 少量尾尘。
 *
 * 几何来自 `sampleTrail`，笔触轮廓来自 `perfect-freehand`，两者都是纯函数；
 * 组件只接收路径、进度、颜色、宽度与强度，不内置题材或事件时刻。
 */
import {useId} from 'react';
import {
  getStroke, motionCurve, particleField, polygonPath, sampleTrail, type Vec2,
} from 'm2v/code-scene';
import {T} from './kit';

export type LightTrailProps = {
  points: readonly Vec2[];
  progress: number;
  color?: string;
  width?: number;
  /** 尾迹占整条路径的比例。 */
  length?: number;
  /** 采样数；越大越平滑。 */
  samples?: number;
  opacity?: number;
  /** 头部光晕半径相对线宽的比例；0 关闭。 */
  glow?: number;
  /** 尾尘粒子数；0 关闭。 */
  dust?: number;
  seed?: string;
  widthPx?: number;
  heightPx?: number;
  role?: string;
};

export default function LightTrail({
  points, progress, color = T.light.gold, width = T.light.trailWidth,
  length = T.light.trailLengthRatio, samples = T.light.trailSamples, opacity = 1,
  glow = 3.2, dust = 3, seed = 'light-trail', widthPx = T.layout.width,
  heightPx = T.layout.height, role,
}: LightTrailProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  if (points.length < 2) return null;
  const trail = sampleTrail({points, progress, length, count: samples, easing: motionCurve('easeInOutSine')});
  if (!trail.length) return null;
  const stroke = getStroke(
    trail.map(sample => ({x: sample.x, y: sample.y, pressure: Math.max(0, sample.opacity)})),
    {
      size: width, thinning: 0.65, smoothing: 0.55, streamline: 0.35,
      simulatePressure: false, start: {taper: 0, cap: true},
      end: {taper: Math.max(1, width * 1.5), cap: true},
    },
  );
  const d = polygonPath(stroke.map(([x, y]) => ({x, y})));
  const head = trail[0];
  const tail = trail[trail.length - 1];
  const particles = dust > 0
    ? particleField({
      count: dust, progress, seed, origin: {x: head.x, y: head.y},
      distance: Math.max(8, width * 3.2), lifetime: 0.7, size: Math.max(1.2, width * 0.5),
      opacity: 0.65, easing: motionCurve('easeOutCubic'),
    })
    : [];
  return (
    <g data-m2v-role={role} opacity={opacity} style={{mixBlendMode: 'screen'}}>
      <defs>
        <linearGradient id={`${uid}-trail`} gradientUnits="userSpaceOnUse"
          x1={head.x} y1={head.y} x2={tail.x} y2={tail.y}>
          <stop offset="0" stopColor={color} stopOpacity={0.95}/>
          <stop offset="0.65" stopColor={color} stopOpacity={0.35}/>
          <stop offset="1" stopColor={color} stopOpacity={0}/>
        </linearGradient>
        <radialGradient id={`${uid}-head`}>
          <stop offset="0" stopColor={T.light.core} stopOpacity={0.95}/>
          <stop offset="0.35" stopColor={color} stopOpacity={0.55}/>
          <stop offset="1" stopColor={color} stopOpacity={0}/>
        </radialGradient>
      </defs>
      <path d={d} fill={`url(#${uid}-trail)`}/>
      {glow > 0 ? (
        <circle cx={head.x} cy={head.y} r={Math.max(6, width * glow)}
          fill={`url(#${uid}-head)`} opacity={0.85}/>
      ) : null}
      {particles.map(particle => (
        <circle key={particle.index} cx={particle.x} cy={particle.y} r={particle.size}
          fill={color} opacity={particle.opacity * 0.7}/>
      ))}
      <title>{`light trail ${Math.round(progress * 100)}%`}</title>
    </g>
  );
}
