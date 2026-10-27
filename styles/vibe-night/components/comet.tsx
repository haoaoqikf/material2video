/**
 * 彗尾母题：头部是光点，尾部是渐隐描边，可带少量固定种子的尾尘。
 * `angle` 为运动方向（度，0 向右）；尾巴朝反方向展开。
 */
import {useId, useMemo} from 'react';
import {color, randomFor, useNightFrame} from './kit';

export type CometProps = {
  x: number;
  y: number;
  angle?: number;
  length?: number;
  width?: number;
  color?: string;
  intensity?: number;
  curve?: number;
  frame?: number;
  seed?: string;
  role?: string;
  state?: string;
};

export default function Comet({
  x, y, angle = 0, length = 240, width = 2.6, color: tailColor = color('ice'),
  intensity = 1, curve = 28, frame, seed = 'comet', role, state,
}: CometProps) {
  const contextFrame = useNightFrame();
  const activeFrame = frame ?? contextFrame;
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const box = Math.max(48, Math.ceil(length * 2.3));
  const center = box / 2;
  const alpha = Math.min(1, Math.max(0, intensity)) * (0.9 + 0.1 * Math.sin(activeFrame * 0.04));
  const dust = useMemo(() => {
    const random = randomFor(`${seed}:dust`);
    return Array.from({length: 7}, () => ({
      along: 0.18 + random() * 0.7,
      offset: (random() - 0.5) * 12,
      radius: 0.7 + random() * 1.4,
    }));
  }, [seed]);
  const tail = `M${center},${center} Q${center - length * 0.45},${center - curve} ${center - length},${center}`;
  return (
    <div style={{position: 'absolute', left: x - center, top: y - center, width: box, height: box, pointerEvents: 'none'}}>
      <svg width={box} height={box} viewBox={`0 0 ${box} ${box}`} style={{overflow: 'visible'}}>
        <defs>
          <linearGradient id={`${uid}-tail`} gradientUnits="userSpaceOnUse" x1={center} y1={center} x2={center - length} y2={center}>
            <stop offset="0" stopColor={tailColor} stopOpacity={0.8 * alpha}/>
            <stop offset="0.45" stopColor={tailColor} stopOpacity={0.28 * alpha}/>
            <stop offset="1" stopColor={tailColor} stopOpacity={0}/>
          </linearGradient>
          <radialGradient id={`${uid}-head`}>
            <stop offset="0" stopColor="#FFFFFF" stopOpacity={alpha}/>
            <stop offset="0.35" stopColor={tailColor} stopOpacity={0.85 * alpha}/>
            <stop offset="1" stopColor={tailColor} stopOpacity={0}/>
          </radialGradient>
        </defs>
        <g transform={`rotate(${angle} ${center} ${center})`}>
          <path d={tail} fill="none" stroke={`url(#${uid}-tail)`} strokeWidth={width * 3.2} strokeLinecap="round" opacity={0.28 * alpha}/>
          <path d={tail} fill="none" stroke={`url(#${uid}-tail)`} strokeWidth={width} strokeLinecap="round"/>
          <g fill={tailColor} opacity={0.55 * alpha}>
            {dust.map((particle, index) => {
              const px = center - length * particle.along;
              const py = center - curve * 4 * particle.along * (1 - particle.along) + particle.offset * (1 - particle.along);
              return <circle key={index} cx={px} cy={py} r={particle.radius} opacity={1 - particle.along}/>;
            })}
          </g>
          <circle cx={center} cy={center} r={Math.max(5, width * 4.6)} fill={`url(#${uid}-head)`}/>
          <circle cx={center} cy={center} r={Math.max(1.8, width * 0.9)} fill="#FFFFFF" opacity={alpha}/>
        </g>
      </svg>
      {role ? (
        <div data-m2v-role={role} data-m2v-state={state} style={{
          position: 'absolute', left: center, top: center, width: length, height: Math.max(10, width * 4),
          transformOrigin: '100% 50%', transform: `translate(-100%, -50%) rotate(${angle}deg)`,
          pointerEvents: 'none',
        }}/>
      ) : null}
    </div>
  );
}
