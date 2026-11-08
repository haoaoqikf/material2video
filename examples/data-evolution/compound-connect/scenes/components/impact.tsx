/**
 * 整屏冲击：把四个命名 preset 映射为透明粒子层的参数。
 *
 * 只接收 frame、画布尺寸与事件；不决定题材、文案或事件时刻。粒子层本身由
 * `m2v/code-scene` 的 `ScreenBurstLayer` 绘制，保持逐帧确定性。
 */
import type {ReactElement} from 'react';
import {ScreenBurstLayer} from '../../src/code-scene/effects/screen-burst';
import type {BurstSpec, DustSpec} from '../../src/code-scene/effects/screen-burst';
import {T} from './kit';

export type ImpactPreset = 'shatter' | 'reveal' | 'formula' | 'finale';
export type ImpactEvent = {
  id: string;
  preset: ImpactPreset;
  origin: {x: number; y: number};
  startFrame: number;
};

export type ImpactProps = {
  frame: number;
  width: number;
  height: number;
  events: readonly ImpactEvent[];
  totalFrames?: number;
  overscan?: number;
  /** 从该 y 坐标向下淡出粒子，保护字幕。 */
  maskBottom?: number;
};

export default function Impact({
  frame, width, height, events, totalFrames = 1740, overscan = 1, maskBottom,
}: ImpactProps): ReactElement {
  const bursts: BurstSpec[] = events.map(event => {
    const preset = T.light.impact[event.preset];
    return {
      id: event.id,
      origin: event.origin,
      startFrame: event.startFrame,
      durationFrames: preset.frames,
      count: preset.count,
      reach: preset.reach,
      color: {core: T.light.core, primary: T.light.gold, secondary: T.light.ivory},
      seed: event.id,
      bokehRatio: preset.bokeh,
      streakRatio: 0.09,
      dustRatio: 0.04,
      lifetime: 0.86,
      drag: 0.9,
      gravity: 32,
      rings: {
        count: preset.rings, travel: preset.ringTravel, thickness: 2.8, opacity: 0.55,
      },
      flash: preset.flash,
    };
  });
  const dust: DustSpec = {
    count: T.light.dust.count,
    opacity: T.light.dust.opacity,
    drift: T.light.dust.drift,
    size: T.light.dust.size,
    cycles: 4,
    seed: 'dark-proof-dust',
  };
  return (
    <ScreenBurstLayer
      frame={frame}
      width={width}
      height={height}
      bursts={bursts}
      dust={dust}
      totalFrames={totalFrames}
      overscan={overscan}
      maskBottom={maskBottom}
    />
  );
}
