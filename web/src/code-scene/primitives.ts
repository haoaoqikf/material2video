/**
 * 共享动效原语：把作品给出的 0–1 进度映射成可绘制的数值与几何。
 *
 * 三条硬约束（与 `code-scene-runtime.md` 一致）：
 *
 * 1. `progress` 是唯一时间输入。原语不读取挂钟、帧号、上一帧状态或外部计时器，
 *    相同进度与参数每次求值都相同，因此逐帧录制、跳帧采样与重录结果一致。
 * 2. 不内置视觉主题。原语不返回颜色、字体或线宽；这些由调用方在绘制时决定。
 *    缓动曲线可传，缺省为恒等（线性），不是某种预设风格。
 * 3. 随机性只来自显式 `seed`，缺省使用固定种子；粒子不累积上一帧状态。
 *
 * 返回的数值是画面表达的原材料，不是完整场景：曲线与柱状图由调用方映射到像素，
 * 列表行由调用方排版，粒子由调用方决定用 SVG、Canvas 或三维对象绘制。
 */

/** 缓动曲线：把 0–1 进度映射到 0–1。调用方传入，原语不预设风格。 */
export type Easing = (t: number) => number;

/** 把进度限制到 0–1；非有限值按 0 处理，避免 NaN 进入绘制。 */
export function clampProgress(progress: number): number {
  if (!Number.isFinite(progress)) return 0;
  return Math.min(1, Math.max(0, progress));
}

function easedProgress(progress: number, easing: Easing): number {
  if (typeof easing !== 'function') throw new TypeError('easing 必须显式传入');
  const value = easing(clampProgress(progress));
  if (!Number.isFinite(value)) throw new RangeError('easing 必须返回有限数值');
  return value;
}

function finite(value: number, name: string): number {
  if (!Number.isFinite(value)) throw new RangeError(`${name} 必须是有限数值`);
  return value;
}

function nonNegative(value: number, name: string): number {
  return Math.max(0, finite(value, name));
}

function integer(value: number, name: string): number {
  if (!Number.isInteger(value) || value < 0) throw new RangeError(`${name} 必须是非负整数`);
  return value;
}

function groupDigits(text: string): string {
  const [whole, fraction] = text.split('.');
  const sign = whole.startsWith('-') ? '-' : '';
  const digits = sign ? whole.slice(1) : whole;
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return sign + grouped + (fraction === undefined ? '' : `.${fraction}`);
}

/**
 * 数字滚动：在 `from` 与 `to` 之间按进度推进，返回数值与可直接绘制的文本。
 *
 * `group` 只是千位分隔的排版选择，默认关闭；不使用与运行环境相关的本地化格式。
 */
export function rollNumber({
  from, to, progress, decimals = 0, easing, group = false,
}: {
  from: number; to: number; progress: number;
  decimals?: number; easing: Easing; group?: boolean;
}): {value: number; text: string} {
  finite(from, 'from'); finite(to, 'to');
  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 20) {
    throw new RangeError('decimals 必须是 0–20 之间的整数');
  }
  const t = easedProgress(progress, easing);
  const value = t === 1 ? to : from + (to - from) * t;
  const text = value.toFixed(decimals);
  return {value, text: group ? groupDigits(text) : text};
}

/**
 * 数据曲线与柱状生长：每个数据点从 `floor` 长到自身取值，一次性或按 `stagger` 依次展开。
 *
 * `ratios[i]` 是第 i 个点当前的生长比例，曲线可用它决定绘制到哪一段，柱状图可直接用于高度。
 * `stagger` 为 0 时所有点同步生长；接近 1 时从左到右依次展开，仍只由进度决定。
 */
export function growSeries({
  values, progress, floor = 0, easing, stagger = 0,
}: {
  values: readonly number[]; progress: number; floor?: number; easing: Easing; stagger?: number;
}): {values: number[]; ratios: number[]} {
  finite(floor, 'floor');
  const delay = Math.min(0.999999, nonNegative(stagger, 'stagger'));
  const t = easedProgress(progress, easing);
  const count = values.length;
  if (!count) return {values: [], ratios: []};
  values.forEach((value, index) => finite(value, `values[${index}]`));
  const ratios = values.map((_value, index) => {
    if (count === 1) return t;
    const start = (index / (count - 1)) * delay;
    return clampProgress((t - start) / (1 - delay));
  });
  const grown = values.map((value, index) =>
    ratios[index] === 1 ? value : floor + (value - floor) * ratios[index]);
  return {values: grown, ratios};
}

/**
 * 列表滚屏：把固定行高的列表按进度滚到末尾，返回可绘制行的索引与纵向位置。
 *
 * 调用方负责行内容、颜色与排版；原语只保证偏移量与行坐标只由进度决定。
 * `overscan` 为可视区外额外保留的行数，便于绘制淡入淡出或裁切边缘。
 */
export function scrollList({
  count, rowExtent, viewport, progress, easing, overscan = 0,
}: {
  count: number; rowExtent: number; viewport: number; progress: number;
  easing: Easing; overscan?: number;
}): {offset: number; rows: {index: number; y: number}[]} {
  integer(count, 'count');
  if (finite(rowExtent, 'rowExtent') <= 0) throw new RangeError('rowExtent 必须大于 0');
  nonNegative(viewport, 'viewport');
  integer(overscan, 'overscan');
  const t = easedProgress(progress, easing);
  const maxOffset = Math.max(0, count * rowExtent - viewport);
  const offset = t === 1 ? maxOffset : maxOffset * t;
  if (!count || viewport === 0) return {offset, rows: []};
  const first = Math.max(0, Math.floor(offset / rowExtent) - overscan);
  const last = Math.min(count - 1, Math.ceil((offset + viewport) / rowExtent) - 1 + overscan);
  const rows: {index: number; y: number}[] = [];
  for (let index = first; index <= last; index += 1) rows.push({index, y: index * rowExtent - offset});
  return {offset, rows};
}

/**
 * 主体状态插值：在若干关键状态之间按进度插值，适合长度、数量、日期或形态参数。
 *
 * 所有状态必须具有同一组数值字段，缺字段或非有限值会明确报错，不静默变成 NaN。
 * 进度 0 返回第一个状态，进度 1 返回最后一个状态，中间按等距关键帧线性插值。
 */
export function interpolateState<T extends Record<string, number>>({
  states, progress, easing,
}: {
  states: readonly T[]; progress: number; easing: Easing;
}): T {
  if (!states.length) throw new RangeError('states 至少需要一个状态');
  const keys = Object.keys(states[0]);
  states.forEach((state, index) => {
    const stateKeys = Object.keys(state);
    if (stateKeys.length !== keys.length || keys.some(key => !(key in state))) {
      throw new TypeError(`states[${index}] 与首个状态的字段不一致`);
    }
    keys.forEach(key => finite(state[key], `states[${index}].${key}`));
  });
  const t = easedProgress(progress, easing);
  if (t === 0 || states.length === 1) return {...states[0]};
  if (t === 1) return {...states[states.length - 1]};
  const position = t * (states.length - 1);
  const index = Math.min(states.length - 2, Math.floor(position));
  const fraction = position - index;
  const from = states[index];
  const to = states[index + 1];
  const result: Record<string, number> = {};
  keys.forEach(key => {
    result[key] = fraction === 0 ? from[key] : from[key] + (to[key] - from[key]) * fraction;
  });
  return result as T;
}

export type Particle = {
  index: number; x: number; y: number; size: number; opacity: number;
};

function seedHash(seed: string | number): number {
  if (typeof seed === 'number') {
    return (Math.trunc(seed) >>> 0) || 0x9e3779b9;
  }
  let hash = 2166136261;
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) || 0x9e3779b9;
}

function random01(seed: number, index: number, channel: number): number {
  let value = (seed ^ Math.imul(index + 1, 0x9e3779b1) ^ Math.imul(channel + 1, 0x85ebca6b)) >>> 0;
  value ^= value >>> 16;
  value = Math.imul(value, 0x7feb352d);
  value ^= value >>> 15;
  value = Math.imul(value, 0x846ca68b);
  value ^= value >>> 16;
  return (value >>> 0) / 4294967296;
}

/**
 * 签名粒子：按显式种子生成一组从原点向外扩散、随后淡出的粒子。
 *
 * 位置、大小与透明度全部由 `progress` 和种子算出，不读取上一帧，也不使用隐式随机源。
 * 颜色、发光方式与图层关系由调用方绘制；`spread` 只改变扩散方向的比例。
 * 进度 0 与 1 时粒子完全透明，便于统一处理入场与收束。
 */
export function particleField({
  count, progress, seed = 'm2v', origin = {x: 0, y: 0}, spread = {x: 1, y: 1},
  distance = 1, lifetime = 0.7, size = 1, opacity = 1, easing,
}: {
  count: number; progress: number; seed?: string | number;
  origin?: {x: number; y: number}; spread?: {x: number; y: number};
  distance?: number; lifetime?: number; size?: number; opacity?: number; easing: Easing;
}): Particle[] {
  integer(count, 'count');
  finite(origin.x, 'origin.x'); finite(origin.y, 'origin.y');
  finite(spread.x, 'spread.x'); finite(spread.y, 'spread.y');
  nonNegative(distance, 'distance'); nonNegative(size, 'size');
  finite(opacity, 'opacity');
  if (!Number.isFinite(lifetime) || lifetime <= 0 || lifetime > 1) {
    throw new RangeError('lifetime 必须在 (0, 1] 内');
  }
  const t = easedProgress(progress, easing);
  const hash = seedHash(seed);
  const particles: Particle[] = [];
  for (let index = 0; index < count; index += 1) {
    const birth = random01(hash, index, 0) * (1 - lifetime);
    const life = lifetime * (0.6 + 0.4 * random01(hash, index, 1));
    const age = clampProgress((t - birth) / life);
    const angle = random01(hash, index, 2) * Math.PI * 2;
    const reach = distance * Math.sqrt(random01(hash, index, 3)) * age;
    // 端点显式归零：sin(π) 在浮点下不是精确的 0，边界帧必须稳定透明。
    const fade = age <= 0 || age >= 1 ? 0 : Math.sin(Math.PI * age) ** 0.7;
    particles.push({
      index,
      x: origin.x + Math.cos(angle) * reach * spread.x,
      y: origin.y + Math.sin(angle) * reach * spread.y,
      size: size * (0.35 + 0.65 * random01(hash, index, 4)) * (0.75 + 0.25 * fade),
      opacity: clampProgress(Math.max(0, opacity) * fade),
    });
  }
  return particles;
}
