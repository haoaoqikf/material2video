import type { CSSProperties } from 'react';
import type { BeatTimeline } from './beats';
import type { Scene } from '@/schema/storyboard';

export const STABLE_READING_FRAMES = 12;
export type MotionPhase = 'establish' | 'change' | 'result' | 'settle';
export interface FrameSpan { startFrame: number; endFrame: number }
export interface PlannedMotion extends FrameSpan { target: string; recipe: Scene['motions'][number]['recipe']; phase: MotionPhase; sourceIndex: number }
export interface CameraState { kind: 'hold'|'push-in'|'pull-out'|'pan'|'reframe'|'settle'; progress: number; focus: string; x: number; y: number; scale: number; velocity: number }
export interface GeometryBox { x: number; y: number; width: number; height: number; radius: number }
export interface VisualMix { focus: number; muted: number; done: number }
export interface SceneMotionPlan { motions: readonly PlannedMotion[]; phases: Readonly<Record<MotionPhase, FrameSpan>>; settleStart: number }

const clamp = (value: number, min = 0, max = 1): number => Math.min(max, Math.max(min, value));
const ease = (value: number): number => 1 - (1 - clamp(value)) ** 3;

export function defaultPhases(duration: number, timeline: BeatTimeline): Record<MotionPhase, FrameSpan> {
  const settleStart = Math.max(0, duration - STABLE_READING_FRAMES);
  const beats = timeline.beats;
  if (beats.length) {
    const firstEnd = Math.min(settleStart, beats[0]!.endFrame);
    const changeEnd = Math.min(settleStart, beats[beats.length - 1]!.endFrame);
    return { establish: { startFrame: 0, endFrame: firstEnd }, change: { startFrame: firstEnd, endFrame: changeEnd }, result: { startFrame: changeEnd, endFrame: settleStart }, settle: { startFrame: settleStart, endFrame: duration } };
  }
  const active = settleStart;
  const a = Math.floor(active * .35), b = Math.floor(active * .75);
  return { establish: { startFrame: 0, endFrame: a }, change: { startFrame: a, endFrame: b }, result: { startFrame: b, endFrame: settleStart }, settle: { startFrame: settleStart, endFrame: duration } };
}

export function staggerOrder(targets: readonly string[], kind: 'forward'|'reverse'|'center'|'path', path?: readonly string[]): string[] {
  if (kind === 'path') { if (!path || path.length < 2 || path.some((id) => !targets.includes(id))) throw new Error('路径传播必须提供覆盖目标的有效 path'); return [...path]; }
  if (kind === 'reverse') return [...targets].reverse();
  if (kind === 'center') return [...targets].map((id, index) => ({ id, index, distance: Math.abs(index - (targets.length - 1) / 2) })).sort((a,b) => a.distance - b.distance || a.index - b.index).map((item) => item.id);
  return [...targets];
}

export function sceneMotionPlan(scene: Scene, timeline: BeatTimeline): SceneMotionPlan {
  const phases = defaultPhases(scene.durationInFrames, timeline); const settleStart = phases.settle.startFrame;
  const beats = new Map(timeline.beats.map((beat) => [beat.id, beat])); const motions: PlannedMotion[] = [];
  scene.motions.forEach((motion, sourceIndex) => {
    const phase = motion.phase ?? 'change';
    const bound = motion.beatId ? beats.get(motion.beatId) : undefined;
    const base = bound ?? phases[phase]; const duration = Math.max(1, Math.min(motion.durationFrames ?? Math.max(1, base.endFrame - base.startFrame), Math.max(1, base.endFrame - base.startFrame), settleStart - base.startFrame));
    const targets = motion.targets ?? (motion.target ? [motion.target] : []); const ordered = motion.stagger ? staggerOrder(targets, motion.stagger.kind, motion.stagger.path) : targets;
    const interval = motion.stagger?.intervalFrames ?? 0;
    ordered.forEach((target, index) => { const startFrame = Math.min(settleStart - 1, base.startFrame + index * interval); motions.push({ target, recipe: motion.recipe, phase, sourceIndex, startFrame, endFrame: Math.min(settleStart, startFrame + duration) }); });
  });
  return { motions, phases, settleStart };
}

export function motionProgress(item: FrameSpan, frame: number): number { return ease((frame - item.startFrame) / Math.max(1, item.endFrame - item.startFrame)); }
export function visualMix(state: 'rest'|'focus'|'muted'|'done'|undefined, progress = 1): VisualMix { const p = ease(progress); return { focus: state === 'focus' ? p : 0, muted: state === 'muted' ? p : 0, done: state === 'done' ? p : 0 }; }
export function channelStyle(parts: { base?: string; beat?: string; motion?: string; continuity?: string; opacity?: number; mix?: VisualMix }): CSSProperties {
  const transform = [parts.base, parts.beat, parts.motion, parts.continuity].filter(Boolean).join(' ');
  return { ...(transform ? { transform } : {}), ...(parts.opacity !== undefined ? { opacity: parts.opacity } : {}), '--a2v-focus-mix': String(parts.mix?.focus ?? 0), '--a2v-muted-mix': String(parts.mix?.muted ?? 0), '--a2v-done-mix': String(parts.mix?.done ?? 0) } as CSSProperties;
}
