import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { A2VCompositionV4 } from './A2VCompositionV4';
import { resolveStoryboardV4 } from '@/runtime/timelineV4';

const testFrame = vi.hoisted(() => ({ value: 0 }));
vi.mock('remotion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('remotion')>();
  return { ...actual, AbsoluteFill: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, useCurrentFrame: () => testFrame.value };
});
vi.mock('./CodeSceneHost', () => ({
  CodeSceneHost: ({ scene, v4Context, cameraOverride, beats }: { scene: { renderer?: { module?: string } }; beats?: { timeline: { beats: Array<{ id: string; startFrame: number; endFrame: number }> } }; v4Context?: { stage: { id: string; startFrame: number; endFrame: number; progress: number }; world: { objects: unknown[] }; objectStates?: Record<string, Record<string, unknown>> }; cameraOverride?: { kind: string } }) => <div data-code-module={scene.renderer?.module ?? ''} data-v4-stage={v4Context?.stage.id} data-v4-range={`${v4Context?.stage.startFrame}-${v4Context?.stage.endFrame}`} data-v4-progress={v4Context?.stage.progress} data-v4-objects={v4Context?.world.objects.length} data-v4-player-state={String(v4Context?.objectStates?.player?.state)} data-v4-camera={cameraOverride?.kind} data-v4-beats={beats?.timeline.beats.map(({ id }) => id).join(',')} data-a2v-code-ready="1" />,
}));

const vectors = JSON.parse(readFileSync(resolve(process.cwd(), '../tests/fixtures/storyboard-v4-vectors.json'), 'utf8')) as { valid: Record<string, any> };

function twoStages(): any {
  const storyboard = structuredClone(vectors.valid);
  const [first] = storyboard.stages;
  first.durationInFrames = 525;
  first.narrationSegments[0].text = first.narrationSegments[0].text.slice(0, 65);
  const second = structuredClone(first);
  second.id = 'ending';
  second.durationInFrames = 525;
  second.narrationSegments[0].id = 'line-ending';
  second.narrationSegments[0].beatId = 'throw-ending';
  second.beats[0].id = 'throw-ending';
  second.narrationSegments[0].text = vectors.valid.stages[0].narrationSegments[0].text.slice(65);
  storyboard.stages.push(second);
  return storyboard;
}

describe('v4 全片单一 composition', () => {
  it('阶段切换只更新上下文，树和安全区仍由同一 world 根承载', () => {
    const storyboard = twoStages();
    testFrame.value = 0;
    const first = renderToStaticMarkup(<A2VCompositionV4 {...storyboard} />);
    testFrame.value = 526;
    const second = renderToStaticMarkup(<A2VCompositionV4 {...storyboard} subtitleCues={[{ start: 17, end: 18, text: '持续字幕' }]} />);
    for (const markup of [first, second]) {
      expect((markup.match(/data-a2v-world-id="dart-world"/g) ?? [])).toHaveLength(1);
      expect((markup.match(/data-a2v-node-id="root"/g) ?? [])).toHaveLength(1);
      expect(markup).toContain('class="a2v-safe"');
      expect(markup).toContain('data-scene-tree-version="4"');
    }
    expect(first).toContain('data-a2v-stage-id="opening"');
    expect(second).toContain('data-a2v-stage-id="ending"');
    expect(second).toContain('data-a2v-subtitle="">持续字幕</div>');
    expect(first.match(/data-a2v-node-id="(root|player|dart|target)"/g)).toEqual(second.match(/data-a2v-node-id="(root|player|dart|target)"/g));
  });

  it('把 tree world 的 value 轨道投影到 composition 使用的内容数据', () => {
    const storyboard = twoStages();
    storyboard.world.data.count = 2;
    storyboard.world.sceneTree.children.push({ id: 'counter', type: 'number', contentRef: 'data.count' });
    storyboard.world.objects.push({ id: 'counter', role: 'supporting', description: '投掷累计' });
    storyboard.world.stateTracks.push({ id: 'counter-growth', target: 'counter', property: 'value',
      binding: { stageId: 'ending', phase: 'result' }, to: 11, interpolation: 'step-end' });

    testFrame.value = 0;
    const before = renderToStaticMarkup(<A2VCompositionV4 {...storyboard} />);
    testFrame.value = 1049;
    const after = renderToStaticMarkup(<A2VCompositionV4 {...storyboard} />);

    expect(before).toContain('data-a2v-node-id="counter"');
    expect(before).toContain('>2</');
    expect(after).toContain('data-a2v-node-id="counter"');
    expect(after).toContain('>11</');
  });

  it('全片 code 模式的同一模块宿主在阶段切换时保持单一', () => {
    const storyboard = twoStages();
    storyboard.world.renderer = { kind: 'code', module: 'darts-trial' };
    delete storyboard.world.sceneTree;
    storyboard.world.data.objects = { player: { state: 'rest' } };
    storyboard.world.stateTracks = [{ id: 'player-focus', target: 'player', property: 'state',
      binding: { stageId: 'opening', phase: 'establish' }, to: 'focus', interpolation: 'step-end' }];
    testFrame.value = 0;
    const first = renderToStaticMarkup(<A2VCompositionV4 {...storyboard} />);
    testFrame.value = 526;
    const second = renderToStaticMarkup(<A2VCompositionV4 {...storyboard} />);
    for (const markup of [first, second]) {
      expect((markup.match(/data-a2v-world-id="dart-world"/g) ?? [])).toHaveLength(1);
      expect((markup.match(/data-code-module="darts-trial"/g) ?? [])).toHaveLength(1);
      expect(markup).toContain('class="a2v-safe"');
    }
    expect(first).toContain('data-v4-stage="opening"');
    expect(second).toContain('data-v4-stage="ending"');
    expect(second).toContain('data-v4-range="525-1050"');
    expect(first).toContain('data-v4-player-state="rest"');
    expect(second).toContain('data-v4-player-state="focus"');
    expect(second).toContain('data-v4-objects="3"');
    expect(second).toContain('data-v4-camera="hold"');
    expect(second).toContain('data-v4-beats="throw-1,throw-ending"');
  });

  it('实际媒体延长首阶段后，随机寻到的全局帧仍处于正确阶段与媒体 beat 轴', () => {
    const storyboard = twoStages();
    const declared = resolveStoryboardV4(storyboard);
    const mediaTimeline = {
      stages: [{ id: 'opening', durationInFrames: 600, audio: 'opening.wav' },
        { id: 'ending', durationInFrames: 450, audio: 'ending.wav' }],
      resolvedBeats: declared.beats.map((beat) => ({ ...beat,
        startFrame: beat.startFrame + (beat.stageId === 'ending' ? 75 : 0),
        endFrame: beat.endFrame + (beat.stageId === 'ending' ? 75 : 0),
      })),
    };
    testFrame.value = 550;
    const beforeBoundary = renderToStaticMarkup(<A2VCompositionV4 {...storyboard} mediaTimeline={mediaTimeline} />);
    testFrame.value = 610;
    const afterBoundary = renderToStaticMarkup(<A2VCompositionV4 {...storyboard} mediaTimeline={mediaTimeline} />);
    expect(beforeBoundary).toContain('data-a2v-stage-id="opening"');
    expect(beforeBoundary).toContain('data-a2v-stage-end="600"');
    expect(afterBoundary).toContain('data-a2v-stage-id="ending"');
    expect(afterBoundary).toContain('data-a2v-stage-start="600"');
    expect(afterBoundary).toContain('data-a2v-beat-estimated="0"');
  });
});
