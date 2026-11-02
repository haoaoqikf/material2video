/**
 * 共享动态几何原语：路径采样、拖尾、爆散、扩散环与互补溶解。
 *
 * 只把 `progress` 映射成可绘制的数值与几何；不读挂钟、`Math.random`、上一帧
 * 状态或外部资源。颜色、线宽、粒子数量与视觉风格由调用方决定。
 *
 * 路径采样使用 `svg-path-properties`（MIT，纯 JS，无 DOM）；手绘笔触由风格
 * 包通过 `m2v/code-scene` 导出的 `getStroke` 绘制，不在本文件里绑定视觉。
 */
import {svgPathProperties} from 'svg-path-properties';
import {clampProgress, type Easing} from './primitives';
import {hashSeed, random01} from './random';

export type Vec2 = {x: number; y: number};
export type TrailSample = {
  index: number; x: number; y: number; angle: number; age: number; opacity: number; width: number;
};
export type BurstParticle = {
  index: number; x: number; y: number; vx: number; vy: number;
  age: number; life: number; size: number; opacity: number;
};
export type RingSample = {index: number; radius: number; opacity: number; width: number};

function eased(progress: number, easing: Easing): number {
  if (typeof easing !== 'function') throw new TypeError('easing 必须显式传入');
  const value = easing(clampProgress(progress));
  if (!Number.isFinite(value)) throw new RangeError('easing 必须返回有限数值');
  return value;
}

function integer(value: number, name: string): number {
  if (!Number.isInteger(value) || value < 0) throw new RangeError(`${name} 必须是非负整数`);
  return value;
}

function finite(value: number, name: string): number {
  if (!Number.isFinite(value)) throw new RangeError(`${name} 必须是有限数值`);
  return value;
}

function nonNegative(value: number, name: string): number {
  return Math.max(0, finite(value, name));
}

/**
 * 按弧长把一条 SVG path 等距采样成点。
 *
 * 只接受单子路径；多子路径请分别传入每段 `d`，避免把 `M` 跳转误当连续运动。
 * 多段折线（如 `M...L...L...`）属于同一子路径，按整条弧长连续采样。
 */
export function samplePath(d: string, count: number): Vec2[] {
  if (typeof d !== 'string' || !d.trim()) return [];
  integer(count, 'count');
  if (count < 2) throw new RangeError('count 至少为 2');
  const moves = (d.match(/[Mm]/g) ?? []).length;
  if (moves > 1) throw new Error('samplePath 只接受单子路径；多子路径请分别传入');
  const properties = new svgPathProperties(d);
  const total = properties.getTotalLength();
  const points: Vec2[] = [];
  for (let index = 0; index < count; index += 1) {
    const point = properties.getPointAtLength(total * (index / (count - 1)));
    points.push({x: point.x, y: point.y});
  }
  return points;
}

/** 把多边形点列转成闭合 SVG path；供手绘笔触与拖尾填充复用。 */
export function polygonPath(points: readonly Vec2[], closed = true): string {
  if (!points.length) return '';
  const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(' ');
  return closed ? `${path} Z` : path;
}

/** 折线累计弧长；供轨迹采样与切向计算复用。 */
export function polylineLengths(points: readonly Vec2[]): number[] {
  const lengths = [0];
  for (let index = 1; index < points.length; index += 1) {
    lengths.push(lengths[index - 1] + Math.hypot(
      points[index].x - points[index - 1].x, points[index].y - points[index - 1].y));
  }
  return lengths;
}

/** 折线上 0–1 位置的点与切向角；位置按累计弧长插值。 */
export function pointAlongPolyline(points: readonly Vec2[], progress: number): {point: Vec2; angle: number} {
  if (!points.length) throw new RangeError('points 不得为空');
  if (points.length === 1) return {point: {...points[0]}, angle: 0};
  const lengths = polylineLengths(points);
  const total = lengths[lengths.length - 1] || 1;
  const target = clampProgress(progress) * total;
  let index = 1;
  while (index < lengths.length - 1 && lengths[index] < target) index += 1;
  const span = lengths[index] - lengths[index - 1] || 1;
  const ratio = (target - lengths[index - 1]) / span;
  const from = points[index - 1];
  const to = points[index];
  return {
    point: {x: from.x + (to.x - from.x) * ratio, y: from.y + (to.y - from.y) * ratio},
    angle: Math.atan2(to.y - from.y, to.x - from.x),
  };
}

/**
 * 轨迹残影：按年龄从头部向后采样 `length` 比例内的点。
 *
 * `age=0` 是头部，`age=1` 是尾端；透明度按 `(1-age)^2` 衰减，尾宽按
 * `width` 比例缩小。它近似 Remotion `<Trail>` 的 `layers/lagInFrames` 语义，
 * 但只依赖当前 `progress`，不渲染子组件、不累积上一帧。
 */
export function sampleTrail({
  points, progress, length = 0.2, count = 8, easing,
}: {
  points: readonly Vec2[]; progress: number; length?: number; count?: number; easing: Easing;
}): TrailSample[] {
  if (points.length < 2) return [];
  const head = eased(progress, easing);
  const span = Math.max(0.0001, nonNegative(length, 'length'));
  const samples = Math.max(2, integer(count, 'count'));
  return Array.from({length: samples}, (_, index) => {
    const age = index / (samples - 1);
    const at = head - age * span;
    const {point, angle} = pointAlongPolyline(points, Math.max(0, at));
    const visible = at >= 0 ? 1 : 0;
    return {
      index,
      x: point.x,
      y: point.y,
      angle,
      age,
      opacity: visible * (1 - age) ** 2,
      width: 1 - age * 0.7,
    };
  });
}

/**
 * 解析式爆散粒子：每颗粒子独立出生、寿命、方向、速度、阻力与重力。
 *
 * 位置直接由 `progress` 求值，不依赖上一帧；端点透明。与 `particleField` 的
 * 返回键不同，避免破坏既有原语契约。`speed` 是寿命结束时的最大位移近似，
 * `drag` 让扩散先快后慢，`gravity` 让粒子在末端下坠。
 */
export function burstField({
  count, progress, seed = 'm2v', origin = {x: 0, y: 0}, angle = 0, cone = Math.PI * 2,
  speed = 1, speedJitter = 0.5, drag = 0, gravity = 0, lifetime = 0.7,
  size = 1, opacity = 1, easing,
}: {
  count: number; progress: number; seed?: string | number;
  origin?: Vec2; angle?: number; cone?: number; speed?: number; speedJitter?: number;
  drag?: number; gravity?: number; lifetime?: number; size?: number; opacity?: number; easing: Easing;
}): BurstParticle[] {
  integer(count, 'count');
  finite(origin.x, 'origin.x'); finite(origin.y, 'origin.y');
  finite(angle, 'angle'); finite(cone, 'cone');
  nonNegative(speed, 'speed'); nonNegative(speedJitter, 'speedJitter');
  nonNegative(drag, 'drag'); finite(gravity, 'gravity');
  nonNegative(size, 'size'); finite(opacity, 'opacity');
  if (!Number.isFinite(lifetime) || lifetime <= 0 || lifetime > 1) {
    throw new RangeError('lifetime 必须在 (0, 1] 内');
  }
  const t = eased(progress, easing);
  const hash = typeof seed === 'number' ? seed : hashSeed(seed);
  return Array.from({length: count}, (_, index) => {
    const birth = random01(hash, index, 0) * (1 - lifetime);
    const life = lifetime * (0.6 + 0.4 * random01(hash, index, 1));
    const age = clampProgress((t - birth) / life);
    const direction = angle + (random01(hash, index, 2) - 0.5) * cone;
    const velocity = speed * (1 - speedJitter * random01(hash, index, 3));
    const travel = drag > 0 ? (1 - Math.exp(-drag * age)) / drag : age;
    const reach = velocity * travel;
    const fade = age <= 0 || age >= 1 ? 0 : Math.sin(Math.PI * age) ** 0.7;
    return {
      index,
      x: origin.x + Math.cos(direction) * reach,
      y: origin.y + Math.sin(direction) * reach + 0.5 * gravity * age * age,
      vx: Math.cos(direction) * velocity,
      vy: Math.sin(direction) * velocity,
      age,
      life,
      size: size * (0.35 + 0.65 * random01(hash, index, 4)) * (0.75 + 0.25 * fade),
      opacity: clampProgress(opacity * fade),
    };
  });
}

/**
 * 扩散圆环：每环独立出生，半径按调用方缓动增长，透明度与线宽在寿命内衰减。
 *
 * `stagger` 是总错峰比例（0 = 同时出生，1 = 最后一环在寿命结束时刚好出生并结束）。
 * 端点透明，适合冲击波、取样窗打开与结果揭示。
 */
export function expandingRings({
  count, progress, baseRadius = 0, travel = 100, thickness = 2,
  life = 0.8, stagger = 0.2, easing,
}: {
  count: number; progress: number; baseRadius?: number; travel?: number; thickness?: number;
  life?: number; stagger?: number; easing: Easing;
}): RingSample[] {
  integer(count, 'count');
  nonNegative(baseRadius, 'baseRadius');
  nonNegative(travel, 'travel');
  nonNegative(thickness, 'thickness');
  if (!Number.isFinite(life) || life <= 0 || life > 1) throw new RangeError('life 必须在 (0, 1] 内');
  const spread = Math.min(1, Math.max(0, finite(stagger, 'stagger')));
  const t = clampProgress(progress);
  return Array.from({length: count}, (_, index) => {
    const birth = count > 1 ? (index / (count - 1)) * (1 - life) * spread : 0;
    const age = clampProgress((t - birth) / life);
    const fade = age <= 0 || age >= 1 ? 0 : Math.sin(Math.PI * age) ** 0.6;
    return {
      index,
      radius: baseRadius + travel * eased(age, easing),
      opacity: fade,
      width: thickness * (0.35 + 0.65 * (1 - age)),
    };
  });
}

/** 互补溶解：旧层 `1-p`、新层 `p`，两者之和恒为 1，不再互相抬高。 */
export function dissolvePair(progress: number, easing: Easing): {out: number; in: number} {
  const value = eased(progress, easing);
  return {out: 1 - value, in: value};
}

/**
 * 字符/元素错峰：返回每项 0–1 的揭示进度，步长自动压缩到窗口内。
 *
 * `stagger` 是总错峰比例；进度 0 时全部 0，进度 1 时全部 1。缓动由调用方
 * 显式传入，适合逐字字幕、逐列点阵或逐点标记。
 */
export function staggerReveal({
  count, progress, stagger = 0.4, easing,
}: {
  count: number; progress: number; stagger?: number; easing: Easing;
}): number[] {
  const amount = integer(count, 'count');
  if (!amount) return [];
  const spread = Math.min(1, Math.max(0, finite(stagger, 'stagger')));
  const t = clampProgress(progress);
  return Array.from({length: amount}, (_, index) => {
    const start = amount === 1 ? 0 : (index / (amount - 1)) * spread;
    return eased(clampProgress((t - start) / Math.max(0.000001, 1 - spread)), easing);
  });
}
