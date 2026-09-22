/**
 * 语义节拍运行时：把「口播段 → 帧区间」解析成逐帧可求值的纯函数。
 *
 * 与 Python 端 `a2v/beats.py` 是同一套规则的等价实现：无声预览按声明时长
 * 与文本长度等比例解析，有声渲染直接用媒体准备写进 `resolvedBeats` 的真实
 * 词边界。两边由各自的单元测试用同一组样例固定行为。
 *
 * 三条纪律（与 `runtime/timeline.ts` 一致）：
 *
 * 1. **纯函数**：同一帧号永远得到同一份 `{current, progress, completed}`，
 *    与调用顺序无关——渲染是随机访问帧的，这里不许有缓存状态；
 * 2. **不读字幕 DOM、不读音频时钟**：时间只来自分镜与媒体；
 * 3. **不抛异常中断整片**：校验已在上游完成，渲染路径遇到非法输入时
 *    保守退化（忽略重复引用、退化为空时间轴），而不是让整片渲染失败。
 */
import type { Beat, NarrationSegment, ResolvedBeat, Scene } from '@/schema/storyboard';

/** 最后一个 beat 完成后场景结尾至少保留的稳定阅读帧数（与 Python 端同一常量）。 */
export const STABLE_READING_FRAMES = 12;

export interface BeatTimeline {
  beats: ResolvedBeat[];
  /** true 表示按声明时长等比例估算（无声预览），false 表示来自真实 TTS 词边界。 */
  estimated: boolean;
}

export interface BeatState {
  current: string | null;
  progress: number;
  completed: string[];
  estimated: boolean;
}

export interface NodeBeatState {
  /** 正在作用在这个节点上的 beat（区间内且以它为目标的第一个）。 */
  active: ResolvedBeat | null;
  /** 已经作用完的 beat（区间已结束且以它为目标的），按时间顺序。 */
  done: ResolvedBeat[];
  /** 活动 beat 的局部进度；已到终态为 1，还没开始为 0。 */
  progress: number;
  /** 这个节点是否被任何 beat 引用过。 */
  targeted: boolean;
  /** 整幕时间轴是否为无声估算。 */
  estimated: boolean;
}

/**
 * 注入场景树与代码场景的只读节拍上下文。
 *
 * `state` 是共享 composition 算好的整幕状态；`timeline` 让节点能查到自己
 * 被哪些 beat 引用。两者都只由分镜、媒体与当前帧决定。
 */
export interface BeatContext {
  timeline: BeatTimeline;
  state: BeatState;
}

/** 空时间轴：没有分段口播的幕（旧分镜、静音场景）用它，行为与改造前一致。 */
export const EMPTY_BEAT_TIMELINE: BeatTimeline = { beats: [], estimated: true };

/** 空节拍上下文：给「没有分段口播」的幕一份确定的初值，而不是 undefined。 */
export const EMPTY_BEAT_CONTEXT: BeatContext = {
  timeline: EMPTY_BEAT_TIMELINE,
  state: { current: null, progress: 0, completed: [], estimated: true },
};

/**
 * 把 `duration` 帧按文本长度等比例切给每段口播（最大余数法）。
 *
 * 先给每段保底 1 帧，再按小数部分从大到小补齐，因此总和恰好等于
 * `duration`、长句拿到更多帧、相同输入永远得到同一结果。
 * `duration < texts.length` 时上游校验已经拒绝；这里退化为空表。
 */
export function proportionalSpans(duration: number, texts: string[]): Array<[number, number]> {
  const count = texts.length;
  if (count === 0 || duration < count) return [];
  const weights = texts.map((text) => Math.max(text.trim().length, 1));
  const total = weights.reduce((sum, value) => sum + value, 0);
  const budget = duration - count;
  const exact = weights.map((weight) => (budget * weight) / total);
  const extra = exact.map((value) => Math.floor(value));
  let remainder = budget - extra.reduce((sum, value) => sum + value, 0);
  const order = exact
    .map((value, index) => ({ index, fraction: value - (extra[index] ?? 0) }))
    .sort((a, b) => b.fraction - a.fraction || a.index - b.index);
  for (const item of order) {
    if (remainder <= 0) break;
    extra[item.index] = (extra[item.index] ?? 0) + 1;
    remainder -= 1;
  }
  const spans: Array<[number, number]> = [];
  let cursor = 0;
  for (const value of extra) {
    spans.push([cursor, cursor + value + 1]);
    cursor += value + 1;
  }
  return spans;
}

/** 把「逐段帧区间」合并成「逐 beat 帧区间」；重复引用只取第一次的区间。 */
function mergeRuns(
  segments: NarrationSegment[],
  spans: Array<[number, number]>,
  beatsById: Map<string, Beat>,
): ResolvedBeat[] {
  const merged: ResolvedBeat[] = [];
  const position = new Map<string, number>();
  segments.forEach((segment, index) => {
    const span = spans[index];
    const beat = beatsById.get(segment.beatId);
    if (!span || !beat) return;
    const existing = position.get(segment.beatId);
    if (existing !== undefined) {
      // 连续引用同一 beat：取并集；不连续（校验已拒绝）时保持原区间，
      // 让时间轴仍然单调，而不是造出重叠区间。
      const previous = merged[existing]!;
      if (existing === merged.length - 1) {
        merged[existing] = { ...previous, endFrame: span[1] };
      }
      return;
    }
    position.set(segment.beatId, merged.length);
    merged.push({
      id: beat.id,
      action: beat.action,
      targets: [...beat.targets],
      meaning: beat.meaning,
      startFrame: span[0],
      endFrame: span[1],
    });
  });
  return merged;
}

/**
 * 无声预览的等比例时间轴：口播预算取 `durationInFrames - STABLE_READING_FRAMES`，
 * 余下的帧留给最后一个 beat 完成后的稳定阅读；场景本身太短时预算退化为整幕时长。
 */
export function resolveSilentTimeline(scene: Scene): BeatTimeline {
  const segments = scene.narrationSegments ?? [];
  if (segments.length === 0) return { beats: [], estimated: true };
  const beatsById = new Map((scene.beats ?? []).map((beat) => [beat.id, beat]));
  let budget = scene.durationInFrames - STABLE_READING_FRAMES;
  if (budget < segments.length) budget = scene.durationInFrames;
  const spans = proportionalSpans(budget, segments.map((segment) => segment.text));
  return { beats: mergeRuns(segments, spans, beatsById), estimated: true };
}

/** 一幕的 beat 时间轴：有效分镜带 `resolvedBeats` 时以它为准，否则等比例估算。 */
export function beatTimeline(scene: Scene): BeatTimeline {
  if (scene.resolvedBeats) return { beats: scene.resolvedBeats, estimated: false };
  return resolveSilentTimeline(scene);
}

/** 逐帧纯函数：`{current, progress, completed, estimated}`。 */
export function beatStateAt(timeline: BeatTimeline, frame: number): BeatState {
  const current = timeline.beats.find((beat) => beat.startFrame <= frame && frame < beat.endFrame) ?? null;
  const frames = current ? current.endFrame - current.startFrame : 0;
  const progress = current && frames > 0
    ? Math.min(1, Math.max(0, (frame - current.startFrame) / frames))
    : 0;
  return {
    current: current ? current.id : null,
    progress,
    completed: timeline.beats.filter((beat) => beat.endFrame <= frame).map((beat) => beat.id),
    estimated: timeline.estimated,
  };
}

/** 单个节点视角的 beat 状态：中层原语据此决定自己该显示什么状态。 */
export function nodeBeatState(timeline: BeatTimeline, frame: number, nodeId: string): NodeBeatState {
  const targeting = timeline.beats.filter((beat) => beat.targets.includes(nodeId));
  const active = targeting.find((beat) => beat.startFrame <= frame && frame < beat.endFrame) ?? null;
  const done = targeting.filter((beat) => beat.endFrame <= frame);
  const frames = active ? active.endFrame - active.startFrame : 0;
  const progress = active && frames > 0
    ? Math.min(1, Math.max(0, (frame - active.startFrame) / frames))
    : done.length > 0 ? 1 : 0;
  return { active, done, progress, targeted: targeting.length > 0, estimated: timeline.estimated };
}

/**
 * 代码场景视角的节拍状态。
 *
 * 前四个字段与场景树解释器拿到的是**同一份值**（都来自共享 composition 算好的
 * `state`），这里只补上当前 beat 的完整声明与整幕计划，让作品能按 id 分支，
 * 而不必自己去解析字幕或挂钟。
 */
export function codeSceneBeatState(context: BeatContext): {
  current: string | null;
  progress: number;
  completed: readonly string[];
  estimated: boolean;
  active: ResolvedBeat | null;
  plan: readonly ResolvedBeat[];
} {
  return {
    current: context.state.current,
    progress: context.state.progress,
    completed: context.state.completed,
    estimated: context.state.estimated,
    active: context.timeline.beats.find((beat) => beat.id === context.state.current) ?? null,
    plan: context.timeline.beats,
  };
}
