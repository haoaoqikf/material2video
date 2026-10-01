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
});
