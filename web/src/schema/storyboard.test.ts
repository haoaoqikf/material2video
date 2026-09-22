import { describe, expect, it } from 'vitest';
import { EMPTY_STORYBOARD, parseStoryboard, sceneSchema, visualIntentSchema } from '@/schema/storyboard';

describe('v2 分镜 schema', () => {
  it('接受最小有效场景树', () => expect(parseStoryboard(EMPTY_STORYBOARD).version).toBe(2));
  it('拒绝旧分镜并给出迁移提示', () => expect(() => parseStoryboard({ version: 1 })).toThrow(/migrate_storyboard/));
  it('拒绝重复节点 id', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.sceneTree!.children!.push({ id: 'text', type: 'shape' });
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝不存在的动效目标', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.motions.push({ target: 'missing', recipe: 'fade', startFrame: 0 });
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝自由样式字段', () => {
    const input = structuredClone(EMPTY_STORYBOARD) as unknown as { scenes: Array<{ sceneTree: Record<string, unknown> }> };
    input.scenes[0]!.sceneTree.style = { color: 'red' };
    expect(() => parseStoryboard(input)).toThrow(/style/);
  });
  it('拒绝指向 data 之外的内容引用', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.sceneTree!.children![0]!.contentRef = 'visual.text';
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝原语未注册的属性', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.sceneTree!.ratio = '1:1';
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝原语不支持的动效配方', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.motions = [{ target: 'text', recipe: 'count', startFrame: 0 }];
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝超出场景时长的动效', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.motions = [{ target: 'text', recipe: 'reveal', startFrame: 29, durationFrames: 5 }];
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
  it('拒绝超出节点数上限的场景树', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    scene.sceneTree!.children = Array.from({ length: 48 }, (_, i) => ({ id: `n${i}`, type: 'shape' as const }));
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });
});

describe('视觉论证字段', () => {
  const intent = (extra: Record<string, unknown>) => ({
    ...structuredClone(EMPTY_STORYBOARD.scenes[0].visualIntent),
    ...extra,
  });

  it('接受逐幕视觉论证声明（旧运行时按同一契约解析新版分镜）', () => {
    const parsed = visualIntentSchema.parse(
      intent({
        mode: 'process',
        claim: '先有反馈，才有下一次调整',
        showWithoutText: '三段状态被两支箭头串起，方向说明前一步导致后一步',
        primaryObject: '三段推进链与两支连接箭头',
        motionMeaning: '箭头逐段画出，把推进过程演一遍',
      }),
    );
    expect(parsed.mode).toBe('process');
  });

  it('缺少视觉论证字段的旧分镜仍然解析（兼容模式）', () => {
    expect(visualIntentSchema.safeParse(intent({})).success).toBe(true);
  });

  it('拒绝受控枚举之外的视觉模式', () => {
    expect(visualIntentSchema.safeParse(intent({ mode: 'slide' })).success).toBe(false);
  });

  it('拒绝空白的论证字段', () => {
    expect(visualIntentSchema.safeParse(intent({ mode: 'chart', claim: '   ' })).success).toBe(false);
  });
});

describe('语义节拍与分段口播', () => {
  /** 用例按需局部改动，因此这里用宽松形状而不是解析后的精确类型。 */
  interface BeatFixture {
    id: string;
    type: string;
    durationInFrames: number;
    data: Record<string, unknown>;
    visualIntent: Record<string, unknown>;
    sceneTree: { id: string; type: string; children: Array<Record<string, unknown>> };
    motions: unknown[];
    beats: Array<{ id: string; action: string; targets: string[]; meaning: string }>;
    narrationSegments: Array<{ id: string; text: string; beatId: string }>;
    narration?: string;
    resolvedBeats?: Array<Record<string, unknown>>;
  }

  /** 一幕带结构证据的非文字幕，声明两个 beat 与两段口播。 */
  const beatScene = (): BeatFixture => ({
    id: 'loop',
    type: 'process',
    durationInFrames: 120,
    data: { values: [{ label: '一月', value: 3 }] },
    visualIntent: structuredClone(EMPTY_STORYBOARD.scenes[0]!.visualIntent),
    sceneTree: {
      id: 'root',
      type: 'stack',
      children: [{ id: 'chart', type: 'chart', contentRef: 'data.values', chart: 'bar', schematic: true }],
    },
    motions: [],
    beats: [
      { id: 'b1', action: 'establish', targets: ['chart'], meaning: '先建立基线' },
      { id: 'b2', action: 'accumulate', targets: ['chart'], meaning: '数值逐段累积' },
    ],
    narrationSegments: [
      { id: 'n1', text: '先看基线。', beatId: 'b1' },
      { id: 'n2', text: '再看累积。', beatId: 'b2' },
    ],
  });

  it('接受分段口播与受控节拍', () => {
    expect(sceneSchema.safeParse(beatScene()).success).toBe(true);
  });

  it('narration 与 narrationSegments 互斥', () => {
    const scene = { ...beatScene(), narration: '整段口播' };
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });

  it('拒绝重复的 beat id 与口播段 id', () => {
    const scene = beatScene();
    scene.beats[1]!.id = 'b1';
    expect(sceneSchema.safeParse(scene).success).toBe(false);
    const other = beatScene();
    other.narrationSegments[1]!.id = 'n1';
    expect(sceneSchema.safeParse(other).success).toBe(false);
  });

  it('拒绝未知动作、空 meaning 与空目标', () => {
    const unknown = beatScene();
    (unknown.beats[1] as { action: string }).action = 'wiggle';
    expect(sceneSchema.safeParse(unknown).success).toBe(false);
    const blank = beatScene();
    blank.beats[0]!.meaning = '   ';
    expect(sceneSchema.safeParse(blank).success).toBe(false);
    const empty = beatScene();
    empty.beats[0]!.targets = [];
    expect(sceneSchema.safeParse(empty).success).toBe(false);
  });

  it('拒绝悬空 beat 引用与孤立 beat', () => {
    const dangling = beatScene();
    dangling.narrationSegments[1]!.beatId = 'missing';
    expect(sceneSchema.safeParse(dangling).success).toBe(false);
    const orphan = beatScene();
    orphan.narrationSegments = [orphan.narrationSegments[0]!];
    expect(sceneSchema.safeParse(orphan).success).toBe(false);
  });

  it('拒绝不存在的目标与目标原语不支持的动作', () => {
    const ghost = beatScene();
    ghost.beats[1]!.targets = ['ghost'];
    expect(sceneSchema.safeParse(ghost).success).toBe(false);
    const unsupported = beatScene();
    unsupported.sceneTree.children.push({ id: 'arrow', type: 'connector', direction: 'ltr' });
    unsupported.beats[1]!.targets = ['arrow'];
    expect(sceneSchema.safeParse(unsupported).success).toBe(false);
  });

  it('拒绝不连续的 beat 引用', () => {
    const scene = beatScene();
    scene.beats.push({ id: 'b3', action: 'deplete', targets: ['chart'], meaning: '回落' });
    scene.narrationSegments.push({ id: 'n3', text: '第三句。', beatId: 'b1' });
    expect(sceneSchema.safeParse(scene).success).toBe(false);
  });

  it('拒绝派生字段里倒退、重叠或越界的帧区间', () => {
    const scene = beatScene();
    scene.resolvedBeats = [
      { id: 'b1', action: 'establish', targets: ['chart'], meaning: '建立', startFrame: 0, endFrame: 60 },
      { id: 'b2', action: 'accumulate', targets: ['chart'], meaning: '累积', startFrame: 40, endFrame: 200 },
    ];
    const result = sceneSchema.safeParse(scene);
    expect(result.success).toBe(false);
  });
});

describe('renderer 判别联合', () => {
  it('缺省 renderer 的旧分镜按 tree 解释（向后兼容）', () => {
    const parsed = sceneSchema.parse(structuredClone(EMPTY_STORYBOARD.scenes[0]));
    expect(parsed.renderer).toBeUndefined();
  });
  it('显式 renderer.kind: tree 接受场景树场景', () => {
    const scene = { ...structuredClone(EMPTY_STORYBOARD.scenes[0]), renderer: { kind: 'tree' as const } };
    expect(sceneSchema.safeParse(scene).success).toBe(true);
  });
  it('code 场景接受 module 并拒绝 sceneTree', () => {
    const scene = {
      ...structuredClone(EMPTY_STORYBOARD.scenes[0]),
      renderer: { kind: 'code' as const, module: 'intro' },
      motions: [],
    };
    delete (scene as { sceneTree?: unknown }).sceneTree;
    expect(sceneSchema.safeParse(scene).success).toBe(true);
    expect(sceneSchema.safeParse({ ...scene, sceneTree: EMPTY_STORYBOARD.scenes[0]!.sceneTree }).success).toBe(false);
  });
  it('code 场景拒绝 motions', () => {
    const scene = {
      ...structuredClone(EMPTY_STORYBOARD.scenes[0]),
      renderer: { kind: 'code' as const, module: 'intro' },
      motions: [],
    };
    delete (scene as { sceneTree?: unknown }).sceneTree;
    expect(sceneSchema.safeParse(scene).success).toBe(true);
    expect(sceneSchema.safeParse({ ...scene, motions: [{ target: 'x', recipe: 'fade', startFrame: 0 }] }).success).toBe(false);
  });
  it('拒绝未知渲染模式', () => {
    const scene = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    expect(sceneSchema.safeParse({ ...scene, renderer: { kind: 'canvas' } }).success).toBe(false);
  });
  it('code module 拒绝扩展名、绝对路径与路径穿越', () => {
    const base = structuredClone(EMPTY_STORYBOARD.scenes[0]);
    delete (base as { sceneTree?: unknown }).sceneTree;
    base.motions = [];
    for (const module of ['intro.tsx', 'C:/evil', '/abs', '../escape', './here', 'a/../b', '.hidden']) {
      const scene = { ...base, renderer: { kind: 'code' as const, module } };
      expect(sceneSchema.safeParse(scene).success, module).toBe(false);
    }
    const ok = { ...base, renderer: { kind: 'code' as const, module: 'charts/bars' } };
    expect(sceneSchema.safeParse(ok).success).toBe(true);
  });
});
