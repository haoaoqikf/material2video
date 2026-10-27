/**
 * C 夜曲星点底：近黑底 + 中央深蓝光池 + 固定种子星点 + 暗角 + 细颗粒。
 * 星点闪烁只由帧号与固定种子决定；颗粒在首次渲染时生成后保持不变。
 */
import {useId, useMemo} from 'react';
import {T, color, randomFor, useNightFrame} from './kit';

export type NightBackdropProps = {
  width: number;
  height: number;
  /** 显式帧号；省略时取录制上下文。 */
  frame?: number;
  seed?: string;
  stars?: number;
  poolX?: number;
  poolY?: number;
  poolRx?: number;
  poolRy?: number;
  poolOpacity?: number;
  vignette?: number;
  grain?: number;
  role?: string;
};

type Star = {x: number; y: number; r: number; opacity: number; phase: number; ice: boolean};

export default function NightBackdrop({
  width, height, frame, seed = 'vibe-night-backdrop', stars,
  poolX = T.backdrop.poolX, poolY = T.backdrop.poolY,
  poolRx = T.backdrop.poolRx, poolRy = T.backdrop.poolRy,
  poolOpacity = T.canvas.poolOpacity, vignette = T.canvas.vignette, grain = 1, role,
}: NightBackdropProps) {
  const contextFrame = useNightFrame();
  const activeFrame = frame ?? contextFrame;
  const count = Math.max(0, Math.round(stars ?? T.backdrop.stars));
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const generated = useMemo(() => {
    const random = randomFor(seed);
    const points: Star[] = [];
    for (let index = 0; index < count; index += 1) {
      points.push({
        x: random() * width,
        y: random() * height,
        r: 0.55 + random() * 1.15,
        opacity: 0.14 + random() * 0.62,
        phase: random() * Math.PI * 2,
        ice: random() < 0.18,
      });
    }
    const grainRandom = randomFor(`${seed}:grain`);
    const dots = Array.from({length: Math.round(T.backdrop.grainDots * grain)}, () => ({
      x: grainRandom() * width,
      y: grainRandom() * height,
      opacity: 0.35 + grainRandom() * 0.65,
    }));
    return {points, dots};
  }, [seed, count, width, height, grain]);

  const poolFill = `url(#${uid}-pool)`;
  const vignetteFill = `url(#${uid}-vignette)`;
  return (
    <div data-m2v-role={role} style={{position: 'absolute', inset: 0, width, height, overflow: 'hidden', background: T.canvas.background}}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{position: 'absolute', inset: 0}}>
        <defs>
          <radialGradient id={`${uid}-pool`} gradientUnits="userSpaceOnUse" cx={poolX} cy={poolY} r={Math.max(1, poolRx)}
            gradientTransform={`translate(${poolX} ${poolY}) scale(1 ${Math.max(0.01, poolRy / Math.max(1, poolRx))}) translate(${-poolX} ${-poolY})`}>
            <stop offset="0" stopColor={T.canvas.poolColor} stopOpacity={poolOpacity}/>
            <stop offset="0.55" stopColor={T.canvas.poolColor} stopOpacity={poolOpacity * 0.55}/>
            <stop offset="1" stopColor={T.canvas.poolColor} stopOpacity={0}/>
          </radialGradient>
          <radialGradient id={`${uid}-vignette`} gradientUnits="userSpaceOnUse" cx={poolX} cy={poolY} r={Math.max(width, height) * 0.78}>
            <stop offset="0.42" stopColor="#000000" stopOpacity="0"/>
            <stop offset="0.78" stopColor="#000000" stopOpacity={vignette * 0.45}/>
            <stop offset="1" stopColor="#000000" stopOpacity={vignette}/>
          </radialGradient>
        </defs>
        <rect width={width} height={height} fill={T.canvas.background}/>
        <rect width={width} height={height} fill={poolFill}/>
        <g>
          {generated.points.map((star, index) => {
            const twinkle = 0.72 + 0.28 * Math.sin(activeFrame * 0.017 + star.phase);
            return (
              <circle
                key={index}
                cx={star.x}
                cy={star.y}
                r={star.r}
                fill={star.ice ? color('ice') : color('text')}
                opacity={star.opacity * twinkle * (star.ice ? 0.9 : 1)}
              />
            );
          })}
        </g>
        <g fill="#DDE6F2" opacity={T.grain.dotOpacity}>
          {generated.dots.map((dot, index) => (
            <circle key={index} cx={dot.x} cy={dot.y} r={0.7} opacity={dot.opacity}/>
          ))}
        </g>
        <rect width={width} height={height} fill={vignetteFill}/>
      </svg>
    </div>
  );
}
