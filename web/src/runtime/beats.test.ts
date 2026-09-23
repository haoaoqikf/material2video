import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import {
  STABLE_READING_FRAMES,
  beatStateAt,
  beatTimeline,
  codeSceneBeatState,
  nodeBeatState,
  proportionalSpans,
  resolveSilentTimeline,
} from '@/runtime/beats';
import type { Scene } from '@/schema/storyboard';
import { sceneSchema } from '@/schema/storyboard';
import type { BeatTimeline } from '@/runtime/beats';

/** 一幕带论证结构证据的非文字幕，声明两个 beat 与两段口播。 */
function beatScene(): Scene {
  return sceneSchema.parse({
    id: 'loop',
    type: 'process',
    durationInFrames: 120,
    data: { values: [{ label: '一月', value: 3 }] },
    visualIntent: {
      relation: 'cause',
      focus: 'chart',
      composition: 'center',
      density: 'sparse',
      tone: 'neutral',
      mode: 'chart', claim: '累积改变结果', showWithoutText: '柱形逐步升高', primaryObject: '柱形图', motionMeaning: '按拍推进柱高',
    },
    renderer: { kind: 'tree' },
    camera: { shot: 'medium', composition: 'center', depth: 'flat', focus: 'chart', segments: [{ kind: 'hold', beatId: 'b1', focus: 'chart' }] },
    sceneTree: {
      id: 'root',
      type: 'stack',
      children: [
        { id: 'chart', type: 'chart', contentRef: 'data.values', chart: 'bar', schematic: true },
      ],
    },
    motions: [],
    beats: [
      { id: 'b1', action: 'establish', targets: ['chart'], meaning: '先建立基线' },
      { id: 'b2', action: 'accumulate', targets: ['chart'], meaning: '数值逐段累积' },
    ],
    narrationSegments: [
      { id: 'n1', text: '先看基线。', beatId: 'b1' },
      { id: 'n2', text: '再看累积到临界点。', beatId: 'b2' },
    ],
  });
}

describe('无声等比例解析', () => {
  it('按文本长度等比例覆盖口播预算，并把余量留给结尾阅读', () => {
    const timeline = resolveSilentTimeline(beatScene());
    expect(timeline.estimated).toBe(true);
    expect(timeline.beats[0]!.startFrame).toBe(0);
    expect(timeline.beats[timeline.beats.length - 1]!.endFrame).toBe(120 - STABLE_READING_FRAMES);
    // 长句拿到更多帧
    const first = timeline.beats[0]!;
    const second = timeline.beats[1]!;
    expect(second.endFrame - second.startFrame).toBeGreaterThan(first.endFrame - first.startFrame);
  });

  it('比例切分总和恰好等于预算且每段至少一帧', () => {
    const spans = proportionalSpans(37, ['甲', '乙', '丙', '丁', '戊']);
    expect(spans[0]![0]).toBe(0);
    expect(spans[spans.length - 1]![1]).toBe(37);
    expect(spans.every(([start, end]) => end - start >= 1)).toBe(true);
    expect(spans).toEqual(proportionalSpans(37, ['甲', '乙', '丙', '丁', '戊']));
  });

  it('装不下时退化为空时间轴而不是抛异常中断渲染', () => {
    expect(proportionalSpans(2, ['甲', '乙', '丙'])).toEqual([]);
  });

  it('媒体派生时间轴优先于估算', () => {
    const scene = beatScene();
    scene.resolvedBeats = [
      { id: 'b1', action: 'establish', targets: ['chart'], meaning: '建立', startFrame: 0, endFrame: 30 },
      { id: 'b2', action: 'accumulate', targets: ['chart'], meaning: '累积', startFrame: 30, endFrame: 80 },
    ];
    const timeline = beatTimeline(scene);
    expect(timeline.estimated).toBe(false);
    expect(timeline.beats[1]!.endFrame).toBe(80);
  });

  it('连续引用同一 beat 的段落合并成一个区间', () => {
    const scene = beatScene();
    scene.narrationSegments = [
      { id: 'n1', text: '第一句，', beatId: 'b1' },
      { id: 'n2', text: '还是同一拍。', beatId: 'b1' },
      { id: 'n3', text: '第二拍。', beatId: 'b2' },
    ];
    const timeline = resolveSilentTimeline(scene);
    expect(timeline.beats.map((beat) => beat.id)).toEqual(['b1', 'b2']);
  });
});

describe('逐帧状态', () => {
  const timeline: BeatTimeline = {
    beats: [
      { id: 'b1', action: 'establish', targets: ['a'], meaning: '建立', startFrame: 10, endFrame: 40 },
      { id: 'b2', action: 'deplete', targets: ['a'], meaning: '消耗', startFrame: 40, endFrame: 70 },
    ],
    estimated: false,
  };

  it('首帧、边界帧、末帧与区间外结果一致', () => {
    expect(beatStateAt(timeline, 0)).toEqual({ current: null, progress: 0, completed: [], estimated: false });
    expect(beatStateAt(timeline, 10)).toEqual({ current: 'b1', progress: 0, completed: [], estimated: false });
    expect(beatStateAt(timeline, 25).progress).toBeCloseTo(0.5);
    expect(beatStateAt(timeline, 39).current).toBe('b1');
    expect(beatStateAt(timeline, 40)).toEqual({ current: 'b2', progress: 0, completed: ['b1'], estimated: false });
    expect(beatStateAt(timeline, 70)).toEqual({ current: null, progress: 0, completed: ['b1', 'b2'], estimated: false });
  });

  it('随机寻帧：先访问后面的帧再回来，结果不变', () => {
    const later = beatStateAt(timeline, 95);
    expect(beatStateAt(timeline, 25).progress).toBeCloseTo(0.5);
    expect(beatStateAt(timeline, 95)).toEqual(later);
  });

  it('节点视角：活动 beat、已完成集合与进度', () => {
    expect(nodeBeatState(timeline, 5, 'a').progress).toBe(0);
    expect(nodeBeatState(timeline, 25, 'a').progress).toBeCloseTo(0.5);
    // 第二个 beat 进行中：进度跟着当前 beat 走，而不是停留在上一个的终值
    expect(nodeBeatState(timeline, 50, 'a').progress).toBeCloseTo(1 / 3);
    expect(nodeBeatState(timeline, 80, 'a').progress).toBe(1);
    expect(nodeBeatState(timeline, 80, 'a').done.map((beat) => beat.id)).toEqual(['b1', 'b2']);
    expect(nodeBeatState(timeline, 25, 'missing').targeted).toBe(false);
  });

  it('代码场景与场景树在同一帧拿到同一份节拍状态', () => {
    for (const frame of [0, 10, 25, 39, 40, 69, 70, 95]) {
      const state = beatStateAt(timeline, frame);
      const code = codeSceneBeatState({ timeline, state });
      expect(code.current).toBe(state.current);
      expect(code.progress).toBe(state.progress);
      expect(code.completed).toEqual(state.completed);
      expect(code.estimated).toBe(state.estimated);
      expect(code.active?.id ?? null).toBe(state.current);
      expect(code.plan).toHaveLength(2);
    }
  });

  it('估算时间轴的标记原样传给代码场景', () => {
    const estimated = { ...timeline, estimated: true };
    const state = beatStateAt(estimated, 25);
    expect(codeSceneBeatState({ timeline: estimated, state }).estimated).toBe(true);
  });
});

describe('与 Python 共用同一批向量', () => {
  // 无声估算在两侧各有一份实现：Python 做闸门采样，这里渲染预览与无声成片。
  // 两边漂移的话，验收过的边界和画面上跑的边界就不是同一批。
  const vectors = JSON.parse(
    readFileSync(new URL('../../../tests/fixtures/beat-vectors.json', import.meta.url), 'utf-8'),
  ) as {
    spans: Array<{ why: string; duration: number; texts: string[]; expected: Array<[number, number]> }>;
    scenes: Array<{
      why: string;
      durationInFrames: number;
      texts: string[];
      beatIds: string[];
      expected: Array<{ id: string; startFrame: number; endFrame: number }>;
    }>;
  };

  it('等比例切分与 Python 一致', () => {
    expect(vectors.spans.length).toBeGreaterThan(0);
    for (const vector of vectors.spans) {
      expect(proportionalSpans(vector.duration, vector.texts), vector.why).toEqual(vector.expected);
    }
  });

  it('无声时间轴与 Python 一致', () => {
    expect(vectors.scenes.length).toBeGreaterThan(0);
    for (const vector of vectors.scenes) {
      const scene = sceneSchema.parse({
        ...beatScene(),
        durationInFrames: vector.durationInFrames,
        beats: [...new Set(vector.beatIds)].map((id, index) => ({
          id, action: 'transform', targets: ['chart'], meaning: `第 ${index + 1} 步`,
        })),
        narrationSegments: vector.texts.map((text, index) => ({
          id: `n${index + 1}`, text, beatId: vector.beatIds[index]!,
        })),
      });
      const actual = resolveSilentTimeline(scene).beats.map((beat) => ({
        id: beat.id, startFrame: beat.startFrame, endFrame: beat.endFrame,
      }));
      expect(actual, vector.why).toEqual(vector.expected);
    }
  });
});
