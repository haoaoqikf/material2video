/**
 * 爆散：径向粒子 + 核心光晕 + 向外扩散的圆环。
 *
 * 粒子来自 `burstField`，圆环来自 `expandingRings`；两者都只依赖进度与种子。
 * 组件不决定何时爆散，也不内置事件、文案或题材。
 */
import {useId} from 'react';
import {burstField, expandingRings} from '../../src/code-scene/dynamics';
import {motionCurve} from '../../src/code-scene/motion';
import {T} from './kit';

export type BurstProps = {
  origin: {x: number; y: number};
  progress: number;
  count?: number;
  color?: string;
  secondaryColor?: string;
  seed?: string;
  distance?: number;
  size?: number;
  opacity?: number;
  rings?: number;
  ringTravel?: number;
  ringThickness?: number;
};

export default function Burst({
  origin, progress, count = T.light.burstCount, color = T.light.gold,
  secondaryColor = T.light.ivory, seed = 'burst', distance = T.light.burstDistance,
  size = 6, opacity = 1, rings = T.light.ringCount, ringTravel = T.light.ringTravel,
  ringThickness = T.light.ringThickness, }: BurstProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const clamped = Math.min(1, Math.max(0, progress));
  const coreOpacity = clamped <= 0 || clamped >= 1 ? 0 : Math.sin(Math.PI * clamped) * 0.55;
  const particles = burstField({
    count, progress, seed, origin, speed: distance, speedJitter: 0.55, drag: 1.2,
    lifetime: T.light.burstLifetime, size, opacity, easing: motionCurve('easeOutCubic'),
  });
  const ringSamples = rings > 0
    ? expandingRings({
      count: rings, progress, baseRadius: 6, travel: ringTravel, thickness: ringThickness,
      life: 0.82, stagger: 0.35, easing: motionCurve('easeOutCubic'),
    })
    : [];
  return (
    <g opacity={opacity} style={{mixBlendMode: 'screen'}}>
      <defs>
        <radialGradient id={`${uid}-core`}>
          <stop offset="0" stopColor={T.light.core} stopOpacity={0.95}/>
          <stop offset="0.4" stopColor={color} stopOpacity={0.5}/>
          <stop offset="1" stopColor={color} stopOpacity={0}/>
        </radialGradient>
        <radialGradient id={`${uid}-particle`}>
          <stop offset="0" stopColor={T.light.core} stopOpacity={0.95}/>
          <stop offset="0.45" stopColor={color} stopOpacity={0.7}/>
          <stop offset="1" stopColor={color} stopOpacity={0}/>
        </radialGradient>
        <radialGradient id={`${uid}-secondary`}>
          <stop offset="0" stopColor={secondaryColor} stopOpacity={0.85}/>
          <stop offset="0.5" stopColor={secondaryColor} stopOpacity={0.35}/>
          <stop offset="1" stopColor={secondaryColor} stopOpacity={0}/>
        </radialGradient>
      </defs>
      <circle cx={origin.x} cy={origin.y} r={Math.max(14, distance * 0.32)}
        fill={`url(#${uid}-core)`} opacity={coreOpacity}/>
      {ringSamples.map(ring => (
        <circle key={ring.index} cx={origin.x} cy={origin.y} r={ring.radius}
          fill="none" stroke={color} strokeWidth={ring.width}
          opacity={ring.opacity * T.light.ringOpacity}/>
      ))}
      {particles.map(particle => (
        <circle key={particle.index} cx={particle.x} cy={particle.y}
          r={particle.size * 2.2} opacity={particle.opacity}
          fill={`url(#${uid}-${particle.index % 3 === 0 ? 'secondary' : 'particle'})`}/>
      ))}
    </g>
  );
}
