/**
 * 轨迹采样：画面、车距标注与图表共用同一份离线数据。
 *
 * `assets/traffic/traffic.json` 由 `generate.py` 生成，车辆位置按环路累计弧长记录，
 * 场景只做插值，不使用挂钟时间或随机数。所有数值都是示意，不是真实测量。
 */
import data from '../assets/traffic/traffic.json';

export type GroupName = 'high' | 'low';

export interface CarState {
  id: number;
  s: number;
  speed: number;
  brake: boolean;
  x: number;
  y: number;
  heading: number;
}

interface RawGroup {
  cars: number;
  spacing: number;
  frames: {t: number; cars: [number, number][]}[];
}

interface LoopPoint {
  s: number;
  x: number;
  y: number;
  heading: number;
}

export const TRAFFIC = data as unknown as {
  fps: number;
  sampleHz: number;
  durationSeconds: number;
  cruise: number;
  car: {length: number; width: number};
  loop: {rx: number; ry: number; perimeter: number; table: LoopPoint[]};
  disturbance: {start: number; duration: number; leaderAmplitude: number; delayPerCar: number};
  thresholds: {brakeRatio: number; slowRatio: number};
  groups: Record<GroupName, RawGroup>;
};

const LOOP = TRAFFIC.loop;

export function groupSpec(name: GroupName): RawGroup {
  return TRAFFIC.groups[name];
}

/** 按录制时钟采样某一组车辆；超出数据范围时停在首/尾关键帧。 */
export function sample(name: GroupName, seconds: number): CarState[] {
  const group = groupSpec(name);
  const frames = group.frames;
  const position = Math.max(0, Math.min(frames.length - 1, seconds * TRAFFIC.sampleHz));
  const first = Math.floor(position);
  const second = Math.min(frames.length - 1, first + 1);
  const fraction = position - first;
  const cruise = TRAFFIC.cruise;
  return frames[first].cars.map(([fromS, fromV], index) => {
    const [toS, toV] = frames[second].cars[index];
    const delta = fromS + (toS - fromS) * fraction;
    const speed = fromV + (toV - fromV) * fraction;
    const s = -index * group.spacing + delta;
    const point = loopPoint(s);
    return {
      id: index + 1,
      s,
      speed,
      brake: speed < cruise * TRAFFIC.thresholds.brakeRatio,
      x: point.x,
      y: point.y,
      heading: point.heading,
    };
  });
}

/** 累计弧长 → 环路中心线坐标与切线方向。 */
export function loopPoint(s: number): LoopPoint {
  const perimeter = LOOP.perimeter;
  let value = s % perimeter;
  if (value < 0) value += perimeter;
  const table = LOOP.table;
  let low = 0;
  let high = table.length - 1;
  while (low < high - 1) {
    const middle = (low + high) >> 1;
    if (table[middle].s <= value) low = middle;
    else high = middle;
  }
  const a = table[low];
  const b = table[high];
  const span = Math.max(1e-6, b.s - a.s);
  const t = Math.max(0, Math.min(1, (value - a.s) / span));
  return {
    s: value,
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t,
    heading: a.heading + angleDelta(b.heading, a.heading) * t,
  };
}

function angleDelta(to: number, from: number): number {
  let delta = to - from;
  while (delta > Math.PI) delta -= 2 * Math.PI;
  while (delta < -Math.PI) delta += 2 * Math.PI;
  return delta;
}

/** 沿行进方向的带符号距离：`value - reference`，落在 ±半圈内。 */
export function wrapDelta(value: number, reference: number): number {
  let delta = (value - reference) % LOOP.perimeter;
  if (delta > LOOP.perimeter / 2) delta -= LOOP.perimeter;
  if (delta < -LOOP.perimeter / 2) delta += LOOP.perimeter;
  return delta;
}

/** 低速区域的弧长中心；没有车辆低于阈值时返回 null。 */
export function slowCenter(cars: CarState[]): number | null {
  const slow = cars.filter(car => car.speed < TRAFFIC.cruise * TRAFFIC.thresholds.slowRatio);
  if (!slow.length) return null;
  const reference = slow[0].s;
  const mean = slow.reduce((sum, car) => sum + wrapDelta(car.s, reference), 0) / slow.length;
  return reference + mean;
}

/** 与前方车辆的中心距离，单位是画布像素（沿路弧长）。 */
export function gapToAhead(cars: CarState[], index: number): number {
  if (index <= 0) return Number.POSITIVE_INFINITY;
  return wrapDelta(cars[index - 1].s, cars[index].s);
}

/** 把车距换算成「车位」：中心距减去车长，再除以车长。 */
export function gapUnits(gap = Number.POSITIVE_INFINITY): number {
  return Math.max(0, (gap - TRAFFIC.car.length) / TRAFFIC.car.length);
}

export function speedRatio(speed: number): number {
  return speed / TRAFFIC.cruise;
}
