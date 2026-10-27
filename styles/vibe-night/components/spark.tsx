/**
 * 光点母题：小白核 + 两层色晕，可带十字射线。
 * 位置、大小与闪烁相位来自参数与固定种子，帧号只改变亮度。
 */
import {useId} from 'react';
import {hashSeed} from 'm2v/code-scene';
import {color, randomFor, useNightFrame} from './kit';

export type SparkProps = {
  x: number;
  y: number;
  /** 内核半径，单位像素。 */
  size?: number;
  color?: string;
  core?: string;
  intensity?: number;
  rays?: boolean;
  frame?: number;
  seed?: string;
  role?: string;
  state?: string;
};

export default function Spark({
  x, y, size = 5, color: haloColor = color('ice'), core = '#FFFFFF',
  intensity = 1, rays = false, frame, seed = 'spark', role, state,
}: SparkProps) {
  const contextFrame = useNightFrame();
  const activeFrame = frame ?? contextFrame;
  const phase = (hashSeed(seed) % 1000) / 1000 * Math.PI * 2;
  const twinkle = 0.78 + 0.22 * Math.sin(activeFrame * 0.05 + phase);
  const box = Math.max(28, Math.ceil(size * 9));
  const center = box / 2;
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const alpha = Math.min(1, Math.max(0, intensity)) * twinkle;
  return (
    <div data-m2v-role={role} data-m2v-state={state} style={{position: 'absolute', left: x - center, top: y - center, width: box, height: box, pointerEvents: 'none'}}>
      <svg width={box} height={box} viewBox={`0 0 ${box} ${box}`}>
        <defs>
          <radialGradient id={`${uid}-halo`}>
            <stop offset="0" stopColor={haloColor} stopOpacity={0.34 * alpha}/>
            <stop offset="0.45" stopColor={haloColor} stopOpacity={0.14 * alpha}/>
            <stop offset="1" stopColor={haloColor} stopOpacity={0}/>
          </radialGradient>
          <radialGradient id={`${uid}-core`}>
            <stop offset="0" stopColor={core} stopOpacity={alpha}/>
            <stop offset="0.55" stopColor={core} stopOpacity={0.72 * alpha}/>
            <stop offset="1" stopColor={core} stopOpacity={0}/>
          </radialGradient>
        </defs>
        <circle cx={center} cy={center} r={center} fill={`url(#${uid}-halo)`}/>
        <circle cx={center} cy={center} r={Math.max(2, size * 2.1)} fill={haloColor} opacity={0.16 * alpha}/>
        <circle cx={center} cy={center} r={Math.max(1.4, size * 1.05)} fill={`url(#${uid}-core)`}/>
        {rays ? (
          <g stroke={haloColor} strokeWidth={0.8} opacity={0.5 * alpha}>
            <line x1={center - size * 5} y1={center} x2={center + size * 5} y2={center}/>
            <line x1={center} y1={center - size * 5} x2={center} y2={center + size * 5}/>
          </g>
        ) : null}
      </svg>
    </div>
  );
}

/** 生成一簇固定种子的光点参数，供作品在场景里自行排布。 */
export function sparkCluster(seed: string, count: number, area: {x: number; y: number; width: number; height: number}, size = 4) {
  const random = randomFor(seed);
  return Array.from({length: count}, (_, index) => ({
    id: `${seed}-${index}`,
    x: area.x + random() * area.width,
    y: area.y + random() * area.height,
    size: size * (0.55 + random() * 0.9),
    seed: `${seed}-${index}`,
  }));
}
