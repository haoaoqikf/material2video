/**
 * 共享节拍原语：把全片进度映射为节拍相位与脉冲。
 *
 * 只读 `progress`（0–1）与显式 `durationSeconds` / `bpm`，不读帧号、挂钟或
 * 上一帧状态；同一进度与参数每次求值相同。用于金点脉冲、点阵呼吸、计数器
 * tick 与字幕关键词的轻微强调，不内置颜色、字阶或题材。
 */
import {clampProgress} from './primitives';

function positive(value: number, name: string): number {
  if (!Number.isFinite(value) || value <= 0) throw new RangeError(`${name} 必须是正数`);
  return value;
}

function finite(value: number, name: string): number {
  if (!Number.isFinite(value)) throw new RangeError(`${name} 必须是有限数值`);
  return value;
}

/** 当前节拍相位（0–1）；`phase` 用于错开不同对象的重音。 */
export function beatPhase(
  progress: number, durationSeconds: number, bpm = 112, phase = 0,
): number {
  const beats = clampProgress(progress) * positive(durationSeconds, 'durationSeconds')
    * positive(bpm, 'bpm') / 60;
  const position = beats + finite(phase, 'phase');
  return position - Math.floor(position);
}

/**
 * 节拍脉冲：每拍起点为 1，在 `decayBeats` 拍内衰减到 0。
 *
 * 默认 112 BPM、衰减 0.18 拍，适合一次短促的亮度/尺度脉冲；不是动画计时器，
 * 不跨帧累计。
 */
export function beatPulse(
  progress: number, durationSeconds: number, bpm = 112, decayBeats = 0.18, phase = 0,
): number {
  const decay = positive(decayBeats, 'decayBeats');
  const local = beatPhase(progress, durationSeconds, bpm, phase);
  if (local >= decay) return 0;
  const rest = 1 - local / decay;
  return rest * rest;
}
