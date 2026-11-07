/** 波形：把采样峰值重采样成固定数量的柱，显隐只由进度决定。 */
import type {CSSProperties} from 'react';
import {clampProgress, type Easing} from '../primitives';

const IDENTITY: Easing = value => value;

/** 按桶取绝对峰值；空输入返回空数组，桶数至少为 1。 */
export function resamplePeaks(samples: readonly number[], buckets: number): number[] {
  const size = Math.max(1, Math.floor(buckets));
  if (!samples.length) return [];
  const step = samples.length / size;
  return Array.from({length: size}, (_, index) => {
    const start = Math.floor(index * step);
    const end = Math.max(start + 1, Math.floor((index + 1) * step));
    let peak = 0;
    for (let cursor = start; cursor < end && cursor < samples.length; cursor += 1) {
      peak = Math.max(peak, Math.abs(samples[cursor]));
    }
    return peak;
  });
}

export type WaveformMode = 'mirror' | 'bottom';

export type WaveformProps = {
  /** 归一化或原始采样值；内部按绝对峰值取包络。 */
  samples: readonly number[];
  progress?: number;
  easing?: Easing;
  width?: number;
  height?: number;
  bars?: number;
  gap?: number;
  color?: string;
  mode?: WaveformMode;
  className?: string;
  style?: CSSProperties;
};

/** 音频波形；对称模式从中线向上下生长，底对齐模式从底部向上。 */
export function Waveform({
  samples, progress = 1, easing = IDENTITY, width = 640, height = 120, bars = 64, gap = 2,
  color = '#F3EDDC', mode = 'mirror', className, style,
}: WaveformProps) {
  const peaks = resamplePeaks(samples, bars);
  let largest = 1e-6;
  for (const peak of peaks) largest = Math.max(largest, peak);
  const barWidth = peaks.length
    ? Math.max(0, (width - gap * (peaks.length - 1)) / peaks.length)
    : 0;
  const revealed = easing(clampProgress(progress)) * peaks.length;
  return (
    <svg className={className} width={width} height={height}
      viewBox={`0 0 ${width} ${height}`} style={{overflow: 'visible', ...style}}>
      {peaks.map((peak, index) => {
        const amount = Math.max(0, Math.min(1, revealed - index));
        const barHeight = (peak / largest) * (mode === 'bottom' ? height : height / 2) * amount;
        const y = mode === 'bottom' ? height - barHeight : (height - barHeight) / 2;
        return (
          <rect key={index} x={index * (barWidth + gap)} y={y} width={barWidth}
            height={barHeight} rx={Math.min(barWidth / 2, 2)} fill={color}/>
        );
      })}
    </svg>
  );
}
