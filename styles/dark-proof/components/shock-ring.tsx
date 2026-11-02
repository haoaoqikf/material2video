/**
 * 冲击环：只画向外扩散的圆环，不携带粒子或题材。
 *
 * 半径/透明度/线宽来自 `expandingRings`；虚线环的偏移也由进度求出，适合
 * 硬切冲击、取样窗打开与结果揭示。
 */
import {expandingRings, motionCurve} from 'm2v/code-scene';
import {T} from './kit';

export type ShockRingProps = {
  origin: {x: number; y: number};
  progress: number;
  count?: number;
  color?: string;
  baseRadius?: number;
  travel?: number;
  thickness?: number;
  dashes?: string;
  opacity?: number;
  role?: string;
};

export default function ShockRing({
  origin, progress, count = 1, color = T.light.gold, baseRadius = 6,
  travel = 140, thickness = T.light.ringThickness, dashes = '0.03 0.02',
  opacity = 1, role,
}: ShockRingProps) {
  const rings = expandingRings({
    count, progress, baseRadius, travel, thickness, life: 0.82, stagger: 0.28,
    easing: motionCurve('easeOutCubic'),
  });
  return (
    <g data-m2v-role={role} opacity={opacity} style={{mixBlendMode: 'screen'}}>
      {rings.map(ring => (
        <circle key={ring.index} cx={origin.x} cy={origin.y} r={ring.radius}
          fill="none" stroke={color} strokeWidth={ring.width}
          opacity={ring.opacity * T.light.ringOpacity}
          strokeDasharray={dashes}
          strokeDashoffset={-progress * travel * 0.6}/>
      ))}
    </g>
  );
}
