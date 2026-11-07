/**
 * 寓言舞台：一场一幅扁平插画的底色——天空渐变、地面色块、暖色暗角。
 * 只画环境层；角色、道具与三层视差由作品或 `parallax-band` 叠加。
 */
import {useId} from 'react';
import {T, alpha, palette} from './kit';

export type FableStageProps = {
  scene: string;
  width: number;
  height: number;
  /** 地平线高度占比；不同平行的地面透视不同。 */
  horizon?: number;
  /** 暗角强度；0 关闭。场景本身已有暖暗角，默认取 tokens。 */
  vignette?: number;
};

export default function FableStage({
  scene, width, height, horizon = 0.68, vignette = T.canvas.vignette, state,
}: FableStageProps) {
  const p = palette(scene);
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const skyY = Math.round(height * horizon);
  return (
    <div style={{
      position: 'absolute', inset: 0, width, height, overflow: 'hidden',
      background: T.canvas.background,
    }}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{position: 'absolute', inset: 0}}>
        <defs>
          <linearGradient id={`${uid}-sky`} gradientUnits="userSpaceOnUse" x1={0} y1={0} x2={0} y2={skyY}>
            <stop offset="0" stopColor={p.sky[0]}/>
            <stop offset="1" stopColor={p.sky[1]}/>
          </linearGradient>
          <linearGradient id={`${uid}-ground`} gradientUnits="userSpaceOnUse" x1={0} y1={skyY} x2={0} y2={height}>
            <stop offset="0" stopColor={p.ground}/>
            <stop offset="1" stopColor={alpha(p.ground, 0.86)}/>
          </linearGradient>
          <radialGradient id={`${uid}-vignette`} gradientUnits="userSpaceOnUse" cx={width / 2} cy={height * 0.55}
            r={Math.max(width, height) * 0.72}>
            <stop offset="0.44" stopColor={T.canvas.vignetteColor} stopOpacity="0"/>
            <stop offset="0.82" stopColor={T.canvas.vignetteColor} stopOpacity={vignette * 0.4}/>
            <stop offset="1" stopColor={T.canvas.vignetteColor} stopOpacity={vignette}/>
          </radialGradient>
        </defs>
        <rect width={width} height={height} fill={`url(#${uid}-sky)`}/>
        <rect y={skyY} width={width} height={height - skyY} fill={`url(#${uid}-ground)`}/>
        <rect width={width} height={height} fill={`url(#${uid}-vignette)`}/>
      </svg>
    </div>
  );
}
