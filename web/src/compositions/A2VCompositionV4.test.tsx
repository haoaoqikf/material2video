import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { A2VCompositionV4 } from './A2VCompositionV4';

const testFrame = vi.hoisted(() => ({ value: 0 }));
vi.mock('remotion', async (importOriginal) => {
  const actual = await importOriginal<typeof import('remotion')>();
  return { ...actual, AbsoluteFill: ({ children }: { children: React.ReactNode }) => <div>{children}</div>, useCurrentFrame: () => testFrame.value };
});
vi.mock('./CodeSceneHost', () => ({
  CodeSceneHost: ({ scene, v4Context, cameraOverride }: { scene: { renderer?: { module?: string } }; v4Context?: { stage: { id: string; startFrame: number; endFrame: number; progress: number }; world: { objects: unknown[] }; objectStates?: Record<string, Record<string, unknown>> }; cameraOverride?: { kind: string } }) => <div data-code-module={scene.renderer?.module ?? ''} data-v4-stage={v4Context?.stage.id} data-v4-range={`${v4Context?.stage.startFrame}-${v4Context?.stage.endFrame}`} data-v4-progress={v4Context?.stage.progress} data-v4-objects={v4Context?.world.objects.length} data-v4-player-state={String(v4Context?.objectStates?.player?.state)} data-v4-camera={cameraOverride?.kind} data-a2v-code-ready="1" />,
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
  });
});
