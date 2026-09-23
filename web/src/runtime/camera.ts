import type { CSSProperties } from 'react';
import type { Scene } from '@/schema/storyboard';
import { beatTimeline, STABLE_READING_FRAMES } from './beats';
import type { CameraState, MotionPhase } from './motionPlan';
import { sceneGeometry } from './geometry';

const clamp = (value: number): number => Math.min(1, Math.max(0, value));
const ease = (value: number): number => 1 - (1 - clamp(value)) ** 3;
interface ResolvedSegment { kind: CameraState['kind']; startFrame: number; endFrame: number; focus: string; direction?: 'left'|'right'|'up'|'down'; intensity: number }

function phaseSpan(scene: Scene, phase: MotionPhase): { startFrame: number; endFrame: number } {
  const settle = Math.max(0, scene.durationInFrames - STABLE_READING_FRAMES); const timeline = beatTimeline(scene); const first = timeline.beats[0]; const last = timeline.beats[timeline.beats.length - 1];
  if (phase === 'settle') return { startFrame: settle, endFrame: scene.durationInFrames };
  if (phase === 'establish') return { startFrame: 0, endFrame: Math.min(settle, first?.endFrame ?? Math.floor(settle * .35)) };
  if (phase === 'change') return { startFrame: first?.endFrame ?? Math.floor(settle * .35), endFrame: Math.min(settle, last?.endFrame ?? Math.floor(settle * .75)) };
  return { startFrame: Math.min(settle, last?.endFrame ?? Math.floor(settle * .75)), endFrame: settle };
}

export function cameraSegments(scene: Scene): readonly ResolvedSegment[] {
  const camera = scene.camera; if (!camera) return []; const timeline = beatTimeline(scene);
  if (camera.segments) return camera.segments.map((segment) => { const beat = segment.beatId ? timeline.beats.find((item) => item.id === segment.beatId) : undefined; const span = beat ?? phaseSpan(scene, segment.phase ?? 'change'); return { kind: segment.kind, startFrame: span.startFrame, endFrame: span.endFrame, focus: segment.focus ?? camera.focus, direction: segment.direction, intensity: segment.intensity }; });
  const establish = phaseSpan(scene, 'establish'); const settle = phaseSpan(scene, 'settle'); const movement: CameraState['kind'] = camera.movement === 'static' ? 'hold' : camera.movement === 'orbit' ? 'reframe' : camera.movement === 'pan-left' || camera.movement === 'pan-right' ? 'pan' : camera.movement;
  return [{ kind: 'hold', startFrame: 0, endFrame: establish.endFrame, focus: camera.focus, intensity: 0 }, { kind: movement, startFrame: establish.endFrame, endFrame: settle.startFrame, focus: camera.focus, direction: camera.movement === 'pan-left' ? 'left' : camera.movement === 'pan-right' ? 'right' : undefined, intensity: .5 }, { kind: 'settle', startFrame: settle.startFrame, endFrame: settle.endFrame, focus: camera.focus, intensity: 0 }];
}

export function cameraState(scene: Scene, frame: number): CameraState {
  const segments = cameraSegments(scene); const segment = segments.find((item) => item.startFrame <= frame && frame < item.endFrame) ?? segments[segments.length - 1];
  if (!segment) return { kind: 'hold', progress: 1, focus: '', x: 0, y: 0, scale: 1, velocity: 0 };
  const raw = clamp((frame - segment.startFrame) / Math.max(1, segment.endFrame - segment.startFrame)); const p = ease(raw); const amount = segment.intensity; const direction = segment.direction;
  const focusBox = sceneGeometry(scene.sceneTree).get(segment.focus); const focusX = focusBox ? .5 - (focusBox.x + focusBox.width / 2) : 0; const focusY = focusBox ? .5 - (focusBox.y + focusBox.height / 2) : 0;
  const x = segment.kind === 'pan' ? (direction === 'left' ? -1 : direction === 'right' ? 1 : 0) * 56 * amount * p : segment.kind === 'reframe' ? focusX * 1080 * amount * p : 0; const y = segment.kind === 'pan' ? (direction === 'up' ? -1 : direction === 'down' ? 1 : 0) * 56 * amount * p : segment.kind === 'reframe' ? focusY * 1920 * amount * p : 0; const scale = segment.kind === 'push-in' ? 1 + .12 * amount * p : segment.kind === 'pull-out' ? 1.06 - .12 * amount * p : 1; const velocity = segment.kind === 'hold' || segment.kind === 'settle' || raw >= 1 ? 0 : 3 * (1 - raw) ** 2 / Math.max(1, segment.endFrame - segment.startFrame);
  return { kind: segment.kind, progress: p, focus: segment.focus, x, y, scale, velocity };
}

/** 所有旧 movement 也解析成含 hold/settle 的新版计划，避免整幕持续漂移。 */
export function cameraStyle(scene: Scene, frame: number): CSSProperties {
  const camera = scene.camera; if (!camera) return {}; const state = cameraState(scene, frame);
  return { transform: `translate(${state.x}px, ${state.y}px) scale(${state.scale})`, perspective: camera.depth === 'layered' ? '1200px' : undefined, transformOrigin: camera.composition === 'left' ? '30% 50%' : camera.composition === 'right' ? '70% 50%' : '50% 50%' };
}
