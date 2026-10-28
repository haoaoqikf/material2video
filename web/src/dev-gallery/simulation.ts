export type Sample = readonly [number, number];
export type Estimate = {progress: number; value: number};

/** 固定种子、预计算数据、任意时刻可回放的蒙特卡洛演示模型。 */
export function createMonteCarlo(seed: number, count: number) {
  if (!Number.isInteger(seed) || !Number.isInteger(count) || count < 1)
    throw new RangeError('模拟种子和样本数必须是整数，样本数至少为 1');
  let state = seed >>> 0;
  const random = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 0x1_0000_0000; };
  const points: Sample[] = Array.from({length: count}, () => [random(), random()] as const);
  const insideCounts = new Uint32Array(count + 1);
  for (let i = 0; i < count; i++) {
    const [x, y] = points[i]!;
    insideCounts[i + 1] = insideCounts[i]! + Number(x*x + y*y <= 1);
  }
  const sampleCount = (progress: number) => {
    if (!Number.isFinite(progress)) throw new RangeError('模拟进度必须是有限数');
    return Math.floor(Math.max(0, Math.min(1, progress)) * count);
  };
  function at(progress: number) {
    const n = sampleCount(progress), inside = insideCounts[n]!;
    return {n, inside, estimate: n ? 4 * inside / n : 0};
  }
  function curve(progress: number, maxPoints = 80): Estimate[] {
    if (!Number.isInteger(maxPoints) || maxPoints < 2)
      throw new RangeError('曲线采样点数至少为 2');
    const n = sampleCount(progress);
    if (!n) return [];
    const step = Math.max(1, Math.ceil(n / (maxPoints - 1)));
    const result: Estimate[] = [];
    for (let i = 1; i <= n; i += step)
      result.push({progress: i / count, value: 4 * insideCounts[i]! / i});
    if (result[result.length - 1]!.progress !== n / count)
      result.push({progress: n / count, value: 4 * insideCounts[n]! / n});
    return result;
  }
  return {points, at, curve};
}
