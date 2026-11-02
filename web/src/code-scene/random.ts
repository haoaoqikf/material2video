/**
 * 共享确定性随机源：FNV-1a 字符串哈希、mulberry32 序列与无状态按索引取值。
 *
 * 只服务逐帧录制：同一 seed 在任何时刻、任何调用顺序下给出同一串数值；
 * 不读挂钟、不读 `Math.random`、不依赖上一帧状态。视觉主题留在调用方。
 */

/** 32 位字符串哈希；把事件 ID、作品 slug 或几何名称变成稳定种子。 */
export function hashSeed(text: string): number {
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

/** 确定性序列；适合一次性初始化星空、环带或固定几何。 */
export function seededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * 无状态按 `(seed, index, channel)` 取随机值。
 *
 * 粒子可以在任意顺序、任意子集求值，不需要顺序推进序列；同参数总是同值。
 */
export function random01(seed: number | string, index: number, channel: number): number {
  const base = typeof seed === 'number' ? (Math.trunc(seed) >>> 0) || 0x9e3779b9 : hashSeed(seed);
  let value = (base ^ Math.imul(index + 1, 0x9e3779b1) ^ Math.imul(channel + 1, 0x85ebca6b)) >>> 0;
  value ^= value >>> 16;
  value = Math.imul(value, 0x7feb352d);
  value ^= value >>> 15;
  value = Math.imul(value, 0x846ca68b);
  value ^= value >>> 16;
  return (value >>> 0) / 4294967296;
}
