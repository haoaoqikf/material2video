/**
 * 三层视差带：远景、角色层与前景按不同系数随镜头推进平移。
 *
 * 推拉只来自 `frame`：同一帧的位移恒定，不依赖挂钟或上一帧状态。
 * 三个插槽都是可选渲染函数，不传即该层为空。
 */
import type {ReactNode} from 'react';
import {T, frameProgress} from './kit';

export type ParallaxBandProps = {
  frame: number;
  startFrame: number;
  durationFrames: number;
  /** 推镜终点相对起点的平移量（像素）；负值向左。 */
  shift?: number;
  /** 同时轻微缩放；1 表示不缩放。 */
  zoom?: number;
  far?: ReactNode;
  character?: ReactNode;
  near?: ReactNode;
  role?: string;
  state?: string;
};

export default function ParallaxBand({
  frame, startFrame, durationFrames, shift = -40, zoom = 1.03,
  far, character, near, role, state,
}: ParallaxBandProps) {
  const progress = frameProgress(frame, startFrame, durationFrames);
  const layer = (factor: number): React.CSSProperties => ({
    position: 'absolute', inset: 0, pointerEvents: 'none',
    transform: `translate3d(${(shift * factor).toFixed(3)}px, 0, 0) scale(${(1 + (zoom - 1) * factor * progress).toFixed(5)})`,
  });
  return (
    <div data-m2v-role={role} data-m2v-state={state} style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
      <div style={layer(T.motion.parallax.far)}>{far}</div>
      <div style={layer(T.motion.parallax.character)}>{character}</div>
      <div style={layer(T.motion.parallax.near)}>{near}</div>
    </div>
  );
}
