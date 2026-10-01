import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { resolveStoryboardV4, stageAt } from './timelineV4';
import type { StoryboardV4 } from '@/schema/storyboardV4';

const vector = JSON.parse(readFileSync(resolve(process.cwd(), '../tests/fixtures/storyboard-v4-timeline-vectors.json'), 'utf8')) as {
  storyboard: StoryboardV4; expected: unknown;
};

describe('v4 全片全局时间轴共享向量', () => {
  it('阶段、beats 和静音 phase 在两个实现中保持一致', () => {
    const timeline = resolveStoryboardV4(vector.storyboard);
    expect(timeline).toEqual(vector.expected);
    expect(stageAt(timeline, 0)).toBe('opening');
    expect(stageAt(timeline, 100)).toBe('opening');
    expect(stageAt(timeline, 101)).toBe('middle');
    expect(stageAt(timeline, 309)).toBe('ending');
    expect(stageAt(timeline, 310)).toBeNull();
  });

  it('媒体派生 stage 时长和全局 WordBoundary beat 不重置后续帧', () => {
    const storyboard = structuredClone(vector.storyboard);
    storyboard.stages[1]!.narrationSegments = [{ id: 'line-middle', text: '继续', beatId: 'beat-middle' }];
    storyboard.stages[1]!.beats = [{ id: 'beat-middle', action: 'connect', targets: ['dart'], meaning: '状态延续' }];
    const declared = resolveStoryboardV4(storyboard);
    const added = 20;
    const media = {
      stages: storyboard.stages.map((stage, index) => ({
        id: stage.id, durationInFrames: stage.durationInFrames + (index === 0 ? added : 0), audio: `${stage.id}.wav`,
      })),
      resolvedBeats: declared.beats.map((beat) => ({
        ...beat,
        startFrame: beat.startFrame + (storyboard.stages.findIndex(({ id }) => id === beat.stageId) > 0 ? added : 0),
        endFrame: beat.endFrame + (storyboard.stages.findIndex(({ id }) => id === beat.stageId) > 0 ? added : 0),
      })),
    };
    const resolved = resolveStoryboardV4(storyboard, media);
    expect(resolved.totalFrames).toBe(declared.totalFrames + added);
    expect(resolved.stages[1]?.startFrame).toBe((declared.stages[1]?.startFrame ?? 0) + added);
    const laterDeclaredBeat = declared.beats.find(({ stageId }) => stageId === storyboard.stages[1]?.id)!;
    const laterMediaBeat = resolved.beats.find(({ stageId }) => stageId === storyboard.stages[1]?.id)!;
    expect(laterMediaBeat.startFrame).toBe(laterDeclaredBeat.startFrame + added);
    expect(resolved.estimated).toBe(false);
    expect(() => resolveStoryboardV4(storyboard, { ...media, stages: media.stages.slice(1) })).toThrow(/顺序、ID 或时长/);
  });
});
