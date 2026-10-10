import type { StoryboardV4 } from '@/schema/storyboardV4';
import type { V4Timeline } from './timelineV4';
import type { CompiledStateTrack } from './stateTracksV4';
import { stateAt } from './stateTracksV4';
import { sceneGeometry } from './geometry';
import type { GeometryBox } from './motionPlan';

export interface CameraPose { x: number; y: number; scale: number }
export interface CompiledCameraSegment {
  id: string; kind: 'hold' | 'push-in' | 'pull-out' | 'pan' | 'reframe' | 'settle';
  startFrame: number; endFrame: number; focus: string; direction?: 'left' | 'right' | 'up' | 'down';
  intensity: number; from: CameraPose; to: CameraPose;
}
export interface CameraTimelineV4 { segments: CompiledCameraSegment[]; initial: CameraPose }
export interface CameraFrameV4 extends CameraPose { id: string | null; kind: CompiledCameraSegment['kind'] | 'hold'; focus: string; progress: number; velocity: number }

function bindingRange(binding: { beatId: string } | { stageId: string; phase: 'establish' | 'change' | 'result' | 'settle' }, timeline: V4Timeline): [number, number, string] | undefined {
  if ('beatId' in binding) {
    const beat = timeline.beats.find(({ id }) => id === binding.beatId);
    return beat ? [beat.startFrame, beat.endFrame, beat.stageId] : undefined;
  }
  const phase = timeline.phases.find((item) => item.stageId === binding.stageId && item.phase === binding.phase);
  return phase ? [phase.startFrame, phase.endFrame, binding.stageId] : undefined;
}

function isVisibleThroughSegment(target: string, start: number, end: number, tracks: readonly CompiledStateTrack[]): boolean {
  const lane = tracks.filter((track) => track.target === target && track.property === 'visible');
  const points = new Set([start, end - 1]);
  for (const track of lane) {
    if (start <= track.startFrame && track.startFrame < end) points.add(track.startFrame);
    if (start <= track.endFrame && track.endFrame < end) points.add(track.endFrame);
  }
  return [...points].every((frame) => stateAt(tracks, frame)[target]?.visible !== false);
}

function isBaseVisible(storyboard: StoryboardV4, target: string): boolean {
  const { world } = storyboard;
  if (world.renderer.kind === 'tree' && world.sceneTree) {
    const visit = (node: typeof world.sceneTree): boolean | undefined => {
      if (!node) return undefined;
      if (node.id === target) return (node as unknown as { visible?: boolean }).visible !== false;
      for (const child of node.children ?? []) {
        const found = visit(child);
        if (found !== undefined) return found;
      }
      return undefined;
    };
    return visit(world.sceneTree) !== false;
  }
  const objects = world.data.objects;
  const object = objects && typeof objects === 'object' ? (objects as Record<string, unknown>)[target] : undefined;
  return !object || typeof object !== 'object' || (object as Record<string, unknown>).visible !== false;
}

/** Compile ordered local declarations to one continuous global pose trajectory. */
export function compileCameraV4(
  storyboard: StoryboardV4, timeline: V4Timeline, stateTracks: readonly CompiledStateTrack[] = [],
  measuredGeometry?: ReadonlyMap<string, GeometryBox>,
): CameraTimelineV4 {
  const { world } = storyboard;
  const objectIds = new Set(world.objects.map(({ id }) => id));
  const pending = world.camera.segments.map((segment, index) => {
    const range = bindingRange(segment.binding, timeline);
    if (!range) throw new Error(`镜头段 ${segment.id} 引用了未知时间绑定`);
    const [startFrame, endFrame, stageId] = range;
    if (endFrame <= startFrame) throw new Error(`镜头段 ${segment.id} 的绑定区间为空`);
    const focus = segment.focus ?? world.camera.focus;
    if (!objectIds.has(focus)) throw new Error(`镜头段 ${segment.id} 引用了未知焦点 ${focus}`);
    if (!isBaseVisible(storyboard, focus)) throw new Error(`镜头段 ${segment.id} 的焦点 ${focus} 在基础状态中不可见`);
    if (!isVisibleThroughSegment(focus, startFrame, endFrame, stateTracks)) throw new Error(`镜头段 ${segment.id} 的焦点 ${focus} 在绑定期间不可见`);
    if (!['hold', 'settle'].includes(segment.kind)) {
      const stage = timeline.stages.find(({ id }) => id === stageId);
      if (stage && endFrame > stage.endFrame - 12) throw new Error(`镜头段 ${segment.id} 的主要运动侵入稳定阅读窗`);
    }
    return { index, segment, startFrame, endFrame, focus };
  }).sort((a, b) => a.startFrame - b.startFrame || a.index - b.index);
  const initial: CameraPose = { x: 0, y: 0, scale: 1 };
  const geometry = measuredGeometry ?? (world.renderer.kind === 'tree' && world.sceneTree
    ? sceneGeometry(world.sceneTree as unknown as import('@/schema/storyboard').SceneNode) : new Map());
  let pose = initial;
  let previousEnd = -1;
  const segments: CompiledCameraSegment[] = [];
  for (const item of pending) {
    if (item.startFrame < previousEnd) throw new Error(`镜头段 ${item.segment.id} 与前一段时间重叠`);
    const segment = item.segment;
    const intensity = segment.intensity ?? .5;
    const from = { ...pose };
    const to = { ...pose };
    if (segment.kind === 'push-in') to.scale += .12 * intensity;
    if (segment.kind === 'pull-out') to.scale = Math.max(.5, to.scale - .12 * intensity);
    if (segment.kind === 'pan') {
      to.x += (segment.direction === 'left' ? -1 : segment.direction === 'right' ? 1 : 0) * 56 * intensity;
      to.y += (segment.direction === 'up' ? -1 : segment.direction === 'down' ? 1 : 0) * 56 * intensity;
    }
    if (segment.kind === 'reframe') {
      const box = geometry.get(item.focus);
      if (!box) throw new Error(`镜头段 ${segment.id} 无法解析焦点 ${item.focus} 的全局几何`);
      to.x += (.5 - (box.x + box.width / 2)) * storyboard.width * intensity;
      to.y += (.5 - (box.y + box.height / 2)) * storyboard.height * intensity;
    }
    segments.push({ id: segment.id, kind: segment.kind, startFrame: item.startFrame, endFrame: item.endFrame,
      focus: item.focus, direction: segment.direction, intensity, from, to });
    pose = to;
    previousEnd = item.endFrame;
  }
  return { segments, initial };
}

const ease = (raw: number): number => 1 - (1 - Math.min(1, Math.max(0, raw))) ** 3;

export function cameraStateV4(timeline: CameraTimelineV4, frame: number): CameraFrameV4 {
  const active = timeline.segments.find(({ startFrame, endFrame }) => startFrame <= frame && frame < endFrame);
  if (active) {
    const progress = ease((frame - active.startFrame) / Math.max(1, active.endFrame - active.startFrame));
    const raw = (frame - active.startFrame) / Math.max(1, active.endFrame - active.startFrame);
    return { id: active.id, kind: active.kind, focus: active.focus, progress,
      x: active.from.x + (active.to.x - active.from.x) * progress,
      y: active.from.y + (active.to.y - active.from.y) * progress,
      scale: active.from.scale + (active.to.scale - active.from.scale) * progress,
      velocity: active.kind === 'hold' || active.kind === 'settle' || raw >= 1 ? 0 : 3 * (1 - raw) ** 2 / Math.max(1, active.endFrame - active.startFrame) };
  }
  const prior = [...timeline.segments].reverse().find(({ endFrame }) => endFrame <= frame);
  const pose = prior?.to ?? timeline.initial;
  return { ...pose, id: null, kind: 'hold', focus: prior?.focus ?? '', progress: 1, velocity: 0 };
}
