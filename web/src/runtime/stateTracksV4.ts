import type { StoryboardV4 } from '@/schema/storyboardV4';
import type { V4Timeline } from './timelineV4';

export interface CompiledStateTrack {
  id: string; target: string; property: 'visible' | 'state' | 'value' | 'contentRef' | 'sourceRef';
  startFrame: number; endFrame: number; startValue: unknown; endValue: unknown;
  interpolation: 'step-end' | 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
}
export type V4ObjectState = Record<string, Record<string, unknown>>;

function lookup(root: unknown, reference: string): unknown {
  return reference.split('.').reduce<unknown>((value, key) =>
    value && typeof value === 'object' && key in value ? (value as Record<string, unknown>)[key] : undefined, root);
}

function baseline(storyboard: StoryboardV4, target: string, property: string): unknown {
  const { world } = storyboard;
  let node: Record<string, unknown> | undefined;
  if (world.renderer.kind === 'tree') {
    const visit = (item: StoryboardV4['world']['sceneTree']): Record<string, unknown> | undefined => {
      if (!item) return undefined;
      if (item.id === target) return item as unknown as Record<string, unknown>;
      for (const child of item.children ?? []) {
        const found = visit(child);
        if (found) return found;
      }
      return undefined;
    };
    node = visit(world.sceneTree);
  } else {
    const objects = world.data.objects;
    const value = objects && typeof objects === 'object' ? (objects as Record<string, unknown>)[target] : undefined;
    node = value && typeof value === 'object' ? value as Record<string, unknown> : undefined;
  }
  if (property === 'visible') return node?.visible ?? true;
  const value = node?.[property];
  if (value === undefined && property === 'value' && world.renderer.kind === 'tree' && typeof node?.contentRef === 'string') {
    return lookup(world.data, node.contentRef);
  }
  return value;
}

export function compileStateTracks(storyboard: StoryboardV4, timeline: V4Timeline): CompiledStateTrack[] {
  const beatRanges = new Map(timeline.beats.map((beat) => [beat.id, [beat.startFrame, beat.endFrame] as const]));
  const pending = storyboard.world.stateTracks.map((track, index) => {
    let range: readonly [number, number] | undefined;
    if ('beatId' in track.binding) range = beatRanges.get(track.binding.beatId);
    else {
      const { stageId, phase: phaseName } = track.binding;
      const phase = timeline.phases.find((item) => item.stageId === stageId && item.phase === phaseName);
      if (phase) range = [phase.startFrame, phase.endFrame];
    }
    if (!range) throw new Error(`轨道 ${track.id} 引用了未知时间绑定`);
    return { index, track, startFrame: range[0], endFrame: range[1] };
  }).sort((a, b) => a.startFrame - b.startFrame || a.index - b.index);
  const previous = new Map<string, CompiledStateTrack>();
  const compiled: CompiledStateTrack[] = [];
  for (const item of pending) {
    const { track, startFrame, endFrame } = item;
    const lane = `${track.target}\0${track.property}`;
    const prior = previous.get(lane);
    if (prior && startFrame < prior.endFrame) throw new Error(`对象 ${track.target} 的属性 ${track.property} 轨道 ${prior.id} 与 ${track.id} 时间重叠`);
    const startValue = structuredClone(prior?.endValue ?? baseline(storyboard, track.target, track.property));
    if (startValue === undefined) throw new Error(`对象 ${track.target} 的属性 ${track.property} 缺少基础值`);
    const result: CompiledStateTrack = { id: track.id, target: track.target, property: track.property,
      startFrame, endFrame, startValue, endValue: structuredClone(track.to), interpolation: track.interpolation };
    compiled.push(result);
    previous.set(lane, result);
  }
  return compiled;
}

function ease(progress: number, mode: CompiledStateTrack['interpolation']): number {
  const value = Math.min(1, Math.max(0, progress));
  if (mode === 'ease-in') return value * value;
  if (mode === 'ease-out') return 1 - (1 - value) ** 2;
  if (mode === 'ease-in-out') return value < .5 ? 2 * value * value : 1 - ((-2 * value + 2) ** 2) / 2;
  return value;
}

function interpolate(start: unknown, end: unknown, progress: number): unknown {
  if (typeof start === 'number' && typeof end === 'number') return start + (end - start) * progress;
  if (Array.isArray(start) && Array.isArray(end) && start.length === end.length) {
    return start.map((value, index) => interpolate(value, end[index], progress));
  }
  if (start && end && typeof start === 'object' && typeof end === 'object'
    && Object.keys(start).sort().join('\0') === Object.keys(end).sort().join('\0')) {
    return Object.fromEntries(Object.keys(start).map((key) => [key,
      interpolate((start as Record<string, unknown>)[key], (end as Record<string, unknown>)[key], progress)]));
  }
  return structuredClone(start);
}

export function stateAt(tracks: readonly CompiledStateTrack[], frame: number): V4ObjectState {
  const result: V4ObjectState = {};
  for (const track of tracks) {
    const lane = result[track.target] ??= {};
    if (frame < track.startFrame) {
      lane[track.property] ??= structuredClone(track.startValue);
      continue;
    }
    let value: unknown;
    if (frame < track.endFrame && track.interpolation === 'step-end') value = track.startValue;
    else if (frame >= track.endFrame) value = track.endValue;
    else value = interpolate(track.startValue, track.endValue,
      ease((frame - track.startFrame) / Math.max(1, track.endFrame - track.startFrame), track.interpolation));
    lane[track.property] = structuredClone(value);
  }
  return result;
}
