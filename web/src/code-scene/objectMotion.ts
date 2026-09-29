import type { A2VBeatInfo } from './index';

export interface Point { x: number; y: number }
const finite = (value: number): number => { if (!Number.isFinite(value)) throw new Error('动画参数必须有限'); return value; };
const clamp = (value: number): number => Math.min(1, Math.max(0, finite(value)));

/** 局部动作可提前完成；区间后保持结果，不依赖上一帧。 */
export function beatActionProgress(plan: readonly A2VBeatInfo[], id: string, frame: number, finishAt = 1): number {
  const beat = plan.find((item) => item.id === id);
  if (!beat) throw new Error(`缺少节拍 ${id}`);
  if (!(finishAt > 0 && finishAt <= 1) || beat.endFrame <= beat.startFrame) throw new Error('节拍区间或完成比例非法');
  return clamp((frame - beat.startFrame) / ((beat.endFrame - beat.startFrame) * finishAt));
}

/** SVG 路径的预采样坐标；弧长仅编译一次，查询二分定位。 */
export function compilePath(points: readonly Point[]): (progress: number, phase?: number) => Point {
  if (points.length < 2) throw new Error('路径至少两个点');
  const frozen = points.map((point) => ({ x: finite(point.x), y: finite(point.y) }));
  const lengths = [0];
  for (let i = 1; i < frozen.length; i++) lengths.push(lengths[i - 1]! + Math.hypot(frozen[i]!.x - frozen[i - 1]!.x, frozen[i]!.y - frozen[i - 1]!.y));
  const total = lengths[lengths.length - 1]!;
  if (total === 0) throw new Error('路径不能为零长度');
  return (progress, phase = 0) => {
    const value = phase === 0 ? clamp(progress) : ((finite(progress) + finite(phase)) % 1 + 1) % 1;
    const distance = value * total; let lo = 1; let hi = lengths.length - 1;
    while (lo < hi) { const mid = (lo + hi) >>> 1; if (lengths[mid]! < distance) lo = mid + 1; else hi = mid; }
    const a = frozen[lo - 1]!; const b = frozen[lo]!; const span = lengths[lo]! - lengths[lo - 1]!;
    const t = span === 0 ? 0 : (distance - lengths[lo - 1]!) / span;
    return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
  };
}

export interface FlowInterval { duration: number; inflow: number; outflow: number }
export interface ReservoirState { level: number; overflow: number; drained: number; input: number }
/** 分段恒流解析积分。出流为最大处理能力，空箱时不凭空产生水。 */
export function compileReservoir(capacity: number, initial: number, intervals: readonly FlowInterval[]): (time: number) => ReservoirState {
  if (!(finite(capacity) > 0) || initial < 0 || finite(initial) > capacity || !intervals.length) throw new Error('容器参数非法');
  const states: ReservoirState[] = [{ level: initial, overflow: 0, drained: 0, input: 0 }]; const ends = [0];
  const advance = (base: ReservoirState, interval: FlowInterval, duration: number): ReservoirState => {
    const incoming = interval.inflow * duration; const net = (interval.inflow - interval.outflow) * duration;
    const level = Math.max(0, Math.min(capacity, base.level + net));
    const overflow = Math.max(0, base.level + net - capacity);
    return { level, overflow: base.overflow + overflow, drained: base.drained + base.level + incoming - level - overflow, input: base.input + incoming };
  };
  const frozen = intervals.map((item) => ({ ...item }));
  for (const item of frozen) {
    if (!(finite(item.duration) > 0) || finite(item.inflow) < 0 || finite(item.outflow) < 0) throw new Error('流量区间非法');
    ends.push(ends[ends.length - 1]! + item.duration); states.push(advance(states[states.length - 1]!, item, item.duration));
  }
  return (time) => {
    const t = Math.max(0, finite(time)); if (t >= ends[ends.length - 1]!) return { ...states[states.length - 1]! };
    let lo = 0; let hi = frozen.length - 1;
    while (lo < hi) { const mid = (lo + hi) >>> 1; if (ends[mid + 1]! <= t) lo = mid + 1; else hi = mid; }
    return advance(states[lo]!, frozen[lo]!, t - ends[lo]!);
  };
}

export interface ObjectPose { id: string; from: Point; to: Point }
export function decomposeObjects(objects: readonly ObjectPose[], progress: number, reverse = false): Array<Point & { id: string }> {
  const seen = new Set<string>(); const p = reverse ? 1 - clamp(progress) : clamp(progress);
  return objects.map(({ id, from, to }) => {
    if (!id || seen.has(id)) throw new Error('对象 ID 必须唯一非空'); seen.add(id);
    return { id, x: finite(from.x) + (finite(to.x) - from.x) * p, y: finite(from.y) + (finite(to.y) - from.y) * p };
  });
}
