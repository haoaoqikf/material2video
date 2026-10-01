import type { StoryboardV4 } from '@/schema/storyboardV4';

export interface V4FrameRange { id: string; startFrame: number; endFrame: number }
export interface V4BeatRange {
  id: string; stageId: string; action: string; targets: string[]; meaning: string;
  startFrame: number; endFrame: number;
}
export interface V4PhaseRange { stageId: string; phase: 'establish' | 'change' | 'result' | 'settle'; startFrame: number; endFrame: number }
export interface V4Timeline {
  fps: number; totalFrames: number; stages: V4FrameRange[]; beats: V4BeatRange[];
  phases: V4PhaseRange[]; estimated: boolean;
}
export interface V4MediaTimeline {
  stages: Array<{ id: string; durationInFrames: number; audio: string | null }>;
  resolvedBeats: V4BeatRange[];
}

function phaseSpans(start: number, duration: number, beats: V4BeatRange[]): Array<[number, number]> {
  const settle = start + Math.max(0, duration - 12);
  let firstEnd: number;
  let changeEnd: number;
  if (beats.length) {
    firstEnd = Math.min(settle, beats[0]!.endFrame);
    changeEnd = Math.min(settle, beats.at(-1)!.endFrame);
  } else {
    const active = settle - start;
    firstEnd = start + Math.floor(active * .35);
    changeEnd = start + Math.floor(active * .75);
  }
  return [[start, firstEnd], [firstEnd, changeEnd], [changeEnd, settle], [settle, start + duration]];
}

function proportionalSpans(duration: number, texts: string[]): Array<[number, number]> {
  if (!texts.length || duration < texts.length) return [];
  const weights = texts.map((text) => Math.max(Array.from(text.trim()).length, 1));
  const budget = duration - texts.length;
  const total = weights.reduce((sum, weight) => sum + weight, 0);
  const exact = weights.map((weight) => (budget * weight) / total);
  const extra = exact.map(Math.floor);
  let remainder = budget - extra.reduce((sum, count) => sum + count, 0);
  const order = exact.map((value, index) => ({ index, fraction: value - (extra[index] ?? 0) }))
    .sort((a, b) => b.fraction - a.fraction || a.index - b.index);
  for (const { index } of order.slice(0, remainder)) extra[index] = (extra[index] ?? 0) + 1;
  let cursor = 0;
  return extra.map((count) => {
    const start = cursor;
    cursor += count + 1;
    return [start, cursor];
  });
}

export function resolveStoryboardV4(storyboard: StoryboardV4, media?: V4MediaTimeline): V4Timeline {
  if (media && (media.stages.length !== storyboard.stages.length
    || media.stages.some((item, index) => item.id !== storyboard.stages[index]?.id
      || !Number.isInteger(item.durationInFrames) || item.durationInFrames < 1))) {
    throw new Error('v4 media stage 顺序、ID 或时长与分镜不匹配');
  }
  let cursor = 0;
  const stages: V4FrameRange[] = [];
  const beats: V4BeatRange[] = [];
  const phases: V4PhaseRange[] = [];
  const phaseNames = ['establish', 'change', 'result', 'settle'] as const;
  for (const [stageIndex, stage] of storyboard.stages.entries()) {
    const start = cursor;
    const mediaStage = media?.stages[stageIndex];
    const duration = mediaStage?.id === stage.id ? mediaStage.durationInFrames : stage.durationInFrames;
    const end = start + duration;
    stages.push({ id: stage.id, startFrame: start, endFrame: end });
    const segments = stage.narrationSegments ?? [];
    const stageBeats: V4BeatRange[] = [];
    if (media) {
      for (const beat of media.resolvedBeats.filter((item) => item.stageId === stage.id)) {
        beats.push({ ...beat, targets: [...beat.targets] });
        stageBeats.push(beat);
      }
    } else if (segments.length) {
      let budget = duration - 12;
      if (budget < segments.length) budget = stage.durationInFrames;
      const spans = proportionalSpans(budget, segments.map(({ text }) => text));
      const byId = new Map((stage.beats ?? []).map((beat) => [beat.id, beat]));
      segments.forEach((segment, index) => {
        const span = spans[index];
        const beat = byId.get(segment.beatId);
        if (!span || !beat) return;
        const prior = beats.at(-1);
        if (prior?.id === segment.beatId && prior.stageId === stage.id) prior.endFrame = start + span[1];
        else {
          const resolved = { id: segment.beatId, stageId: stage.id, action: beat.action,
          targets: [...beat.targets], meaning: beat.meaning,
          startFrame: start + span[0], endFrame: start + span[1] };
          beats.push(resolved);
          stageBeats.push(resolved);
        }
      });
    }
    phaseSpans(start, duration, stageBeats).forEach(([phaseStart, phaseEnd], index) => {
      phases.push({ stageId: stage.id, phase: phaseNames[index]!, startFrame: phaseStart, endFrame: phaseEnd });
    });
    cursor = end;
  }
  return { fps: storyboard.fps, totalFrames: cursor, stages, beats, phases, estimated: !media };
}

export function stageAt(timeline: V4Timeline, frame: number): string | null {
  return timeline.stages.find(({ startFrame, endFrame }) => startFrame <= frame && frame < endFrame)?.id ?? null;
}
