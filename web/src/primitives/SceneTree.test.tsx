import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  cycleChildStyle,
  fitRoleDown,
  layoutStyle,
  motionStyle,
  quantityFactor,
  quantityValue,
  resolveContent,
  ROLE_LADDER,
  SceneTree,
  stageProgress,
  stageState,
} from './SceneTree';
import { EMPTY_STORYBOARD, type ResolvedBeat, type Scene, type SceneNode } from '@/schema/storyboard';
import type { BeatTimeline, NodeBeatState } from '@/runtime/beats';

describe('场景树运行时', () => {
  it('只解析 data 内容引用', () => {
    expect(resolveContent({ title: '甲', nested: { value: 2 } }, 'data.nested.value')).toBe(2);
    expect(resolveContent({ title: '甲' }, 'visual.title')).toBeUndefined();
  });
  it('支持下标引用且与校验器同一语义', () => {
    expect(resolveContent({ steps: ['甲', '乙'] }, 'data.steps[1]')).toBe('乙');
    expect(resolveContent({ steps: ['甲'] }, 'data.steps[3]')).toBeUndefined();
    expect(resolveContent({ steps: ['甲'] }, 'data.steps[0]')).toBe('甲');
  });
  it('同一帧的动效样式可复现且不改变布局声明', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.motions = [{ target: 'text', recipe: 'rise', startFrame: 0, durationFrames: 20 }];
    expect(motionStyle(scene, 'text', 7)).toEqual(motionStyle(scene, 'text', 7));
    expect(motionStyle(scene, 'text', 7, '', 'cinematic').transform).not.toEqual(motionStyle(scene, 'text', 7).transform);
    expect(scene.sceneTree!.children).toHaveLength(1);
  });
});

describe('预设字号取档', () => {
  const fitsFor = (tooWide: string[]) => (role: string) => !tooWide.includes(role);

  it('放得下时保持声明档位', () => {
    expect(fitRoleDown('title', fitsFor([]))).toEqual({ role: 'title', measured: true });
  });
  it('放不下时沿阶梯向下取档', () => {
    expect(fitRoleDown('hero', fitsFor(['hero', 'headline']))).toEqual({ role: 'title', measured: true });
    expect(fitRoleDown('body', fitsFor(ROLE_LADDER as unknown as string[]))).toEqual({ role: 'caption', measured: true });
  });
  it('同一输入重复取档结果一致', () => {
    const fits = fitsFor(['hero']);
    expect(fitRoleDown('hero', fits)).toEqual(fitRoleDown('hero', fits));
  });
  it('阶梯必须从大到小', () => {
    expect(ROLE_LADDER[0]).toBe('hero');
    expect(ROLE_LADDER[ROLE_LADDER.length - 1]).toBe('caption');
  });
});

const stageNodes = (count: number): SceneNode[] =>
  Array.from({ length: count }, (_, index) => ({ id: `stage-${index}`, type: 'text', contentRef: 'data.text' }) as SceneNode);

const stageTimeline: BeatTimeline = {
  beats: [
    { id: 'b1', action: 'connect', targets: ['stage-0'], meaning: '第一步', startFrame: 10, endFrame: 30 },
    { id: 'b2', action: 'accumulate', targets: ['stage-1'], meaning: '第二步', startFrame: 30, endFrame: 50 },
  ],
  estimated: false,
};

const beatState = (over: Partial<NodeBeatState>): NodeBeatState => ({
  active: null, done: [], progress: 0, targeted: true, estimated: false, ...over,
});

const resolvedBeat = (action: string): ResolvedBeat => ({
  id: 'b', action: action as ResolvedBeat['action'], targets: ['x'], meaning: '含义', startFrame: 0, endFrame: 10,
});

describe('中层原语的阶段状态', () => {
  it('当前阶段由当前帧的活动 beat 决定', () => {
    const nodes = stageNodes(3);
    expect(stageState(nodes, stageTimeline, 5)).toEqual({ active: -1, done: [false, false, false] });
    expect(stageState(nodes, stageTimeline, 20).active).toBe(0);
    expect(stageState(nodes, stageTimeline, 40).active).toBe(1);
    expect(stageState(nodes, stageTimeline, 40).done).toEqual([true, false, false]);
    expect(stageState(nodes, stageTimeline, 80)).toEqual({ active: -1, done: [true, true, false] });
  });

  it('同帧重复求值结果一致', () => {
    const nodes = stageNodes(3);
    expect(stageState(nodes, stageTimeline, 40)).toEqual(stageState(nodes, stageTimeline, 40));
  });

  it('阶段推进比例只增不减且落在 0..1', () => {
    const nodes = stageNodes(4);
    const values = [0, 20, 40, 80].map((frame) => stageProgress(stageState(nodes, stageTimeline, frame), 4));
    expect(values).toEqual([...values].sort((a, b) => a - b));
    for (const value of values) expect(value).toBeGreaterThanOrEqual(0);
    expect(values[values.length - 1]).toBeLessThanOrEqual(1);
  });

  it('布局冻结：帧号只改变阶段强调，不产出几何', () => {
    const nodes = stageNodes(4);
    const geometry = nodes.map((_, index) => cycleChildStyle(index, nodes.length, 'cw'));
    expect(stageState(nodes, stageTimeline, 0).active).toBe(-1);
    expect(stageState(nodes, stageTimeline, 40).active).toBe(1);
    expect(Object.keys(stageState(nodes, stageTimeline, 40)).sort()).toEqual(['active', 'done']);
    expect(nodes.map((_, index) => cycleChildStyle(index, nodes.length, 'cw'))).toEqual(geometry);
  });
});

describe('中层原语的方向关系', () => {
  it('flow 与 timeline 按 direction 排列，取值为受控枚举', () => {
    const node = (direction: string) => ({ id: 'f', type: 'flow', direction, children: stageNodes(3) }) as unknown as SceneNode;
    expect(layoutStyle(node('ltr')).flexDirection).toBe('row');
    expect(layoutStyle(node('rtl')).flexDirection).toBe('row-reverse');
    expect(layoutStyle(node('ttb')).flexDirection).toBe('column');
    expect(layoutStyle(node('btt')).flexDirection).toBe('column-reverse');
    // 缺省方向确定：不写 direction 与写 ltr 完全一致
    expect(layoutStyle(node(undefined as unknown as string))).toEqual(layoutStyle(node('ltr')));
  });

  it('cycle 的正逆时针位置集合相同、行进方向相反', () => {
    const clockwise = [0, 1, 2, 3].map((index) => cycleChildStyle(index, 4, 'cw'));
    const counter = [0, 1, 2, 3].map((index) => cycleChildStyle(index, 4, 'ccw'));
    // 两种方向都从正上方起步，第二步分别走向相反的一侧
    expect(counter[0]).toEqual(clockwise[0]);
    expect(counter[1]).toEqual(clockwise[3]);
    expect(counter[3]).toEqual(clockwise[1]);
    // 位置集合完全相同：换方向只改顺序，不改几何
    expect(new Set(counter.map((style) => JSON.stringify(style)))).toEqual(
      new Set(clockwise.map((style) => JSON.stringify(style))),
    );
  });

  it('圆周位置只由第几个与共几个决定', () => {
    expect(cycleChildStyle(1, 4)).toEqual(cycleChildStyle(1, 4, 'cw'));
    expect(cycleChildStyle(1, 5, 'cw')).not.toEqual(cycleChildStyle(1, 4, 'cw'));
  });

  it('阶段状态锚点不占用画布的 data-a2v-stage', () => {
    // 画布容器用 [data-a2v-stage] 声明 1080×1920 + overflow:hidden（base.css）；
    // 节点上一旦同名，每个阶段子节点都会被撑成整块画布并把标题挤出安全区。
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]) as Scene;
    scene.sceneTree = {
      id: 'flow', type: 'flow', direction: 'ltr',
      children: [
        { id: 'stage-0', type: 'surface', children: [{ id: 'a-text', type: 'text', contentRef: 'data.text' }] },
        { id: 'stage-1', type: 'surface', children: [{ id: 'b-text', type: 'text', contentRef: 'data.text' }] },
      ],
    } as SceneNode;
    const markup = renderToStaticMarkup(
      <SceneTree
        scene={scene}
        frame={40}
        beats={{ timeline: stageTimeline, state: { current: 'b2', progress: 0.5, completed: ['b1'], estimated: false } }}
      />,
    );
    expect(markup).toContain('data-a2v-stage-state="done"');
    expect(markup).toContain('data-a2v-stage-state="active"');
    expect(markup).not.toContain('data-a2v-stage=');
  });
});

describe('量级类原语的节拍驱动', () => {
  it('累积类从 0 推到满值，消耗类从满值退到 0', () => {
    expect(quantityFactor(beatState({ active: resolvedBeat('accumulate'), progress: 0.25 }))).toBeCloseTo(0.25);
    expect(quantityFactor(beatState({ active: resolvedBeat('deplete'), progress: 0.25 }))).toBeCloseTo(0.75);
    expect(quantityFactor(beatState({ active: resolvedBeat('highlight'), progress: 0.25 }))).toBe(1);
  });

  it('结束后留下确定的终值', () => {
    expect(quantityFactor(beatState({ done: [resolvedBeat('accumulate')] }))).toBe(1);
    expect(quantityFactor(beatState({ done: [resolvedBeat('deplete')] }))).toBe(0);
    // 还没轮到它：起点为零，而不是直接显示终值
    expect(quantityFactor(beatState({}))).toBe(0);
    // 没有任何 beat 引用它：旧分镜行为不变，显示满值
    expect(quantityFactor(beatState({ targeted: false }))).toBe(1);
  });

  it('内容值限定在 0–100，非法值退化为 0', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]) as Scene;
    const node = { id: 'g', type: 'gauge', contentRef: 'data.ratio' } as SceneNode;
    for (const [value, expected] of [[42, 42], [120, 100], [-5, 0], ['x', 0], [undefined, 0]] as const) {
      (scene.data as Record<string, unknown>).ratio = value;
      expect(quantityValue(scene, node)).toBe(expected);
    }
  });
});
