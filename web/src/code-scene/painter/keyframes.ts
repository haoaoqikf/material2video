export type NumericKey = {at: number; value: number};
export type NumericInterpolation = 'linear' | 'hold' | 'smooth';

/** 无状态数值轨道。关键帧时间必须严格递增；轨道首尾之外保持端值。 */
export function keyframeAt(keys: readonly NumericKey[], at: number,
                           interpolation: NumericInterpolation = 'linear'): number {
  if (!Number.isFinite(at)) throw new RangeError('轨道时间必须是有限数');
  if (!['linear', 'hold', 'smooth'].includes(interpolation))
    throw new RangeError(`未知插值方式：${interpolation}`);
  if (!keys.length) throw new RangeError('数值轨道至少需要一个关键帧');
  for (let index = 0; index < keys.length; index++) {
    const key = keys[index]!;
    if (!Number.isFinite(key.at) || !Number.isFinite(key.value))
      throw new RangeError('关键帧时间和值必须是有限数');
    if (index && key.at <= keys[index - 1]!.at)
      throw new RangeError('关键帧时间必须严格递增');
  }
  if (at <= keys[0]!.at) return keys[0]!.value;
  const last = keys[keys.length - 1]!;
  if (at >= last.at) return last.value;
  let right = 1;
  while (keys[right]!.at < at) right++;
  const left = keys[right - 1]!;
  if (interpolation === 'hold') return left.value;
  const next = keys[right]!;
  const span = next.at - left.at;
  const t = (at - left.at) / span;
  if (interpolation === 'linear') return left.value + (next.value - left.value) * t;
  const before = keys[Math.max(0, right - 2)]!;
  const after = keys[Math.min(keys.length - 1, right + 1)]!;
  const m0 = (next.value - before.value) / (next.at - before.at) * span;
  const m1 = (after.value - left.value) / (after.at - left.at) * span;
  const t2 = t * t, t3 = t2 * t;
  // 非均匀时间上的 Hermite 形式 Catmull-Rom；不隐式夹断过冲。
  return (2*t3 - 3*t2 + 1) * left.value + (t3 - 2*t2 + t) * m0
    + (-2*t3 + 3*t2) * next.value + (t3 - t2) * m1;
}
