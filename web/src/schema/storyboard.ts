/**
 * 分镜脚本的 zod 镜像。
 *
 * **权威校验器仍是 Python 侧的 `scripts/a2v/storyboard.py`**——它带字段路径定位、
 * 排版类警告与 `--strict`，AI 的快速修正循环依赖它。这里的 schema 做三件事：
 * 给渲染层提供运行时安全与类型推导、给组件读分镜时提供默认值、
 * 并作为「服务端镜像 + 漂移测试」模式的另一端（对照 `examples/` 下的真实分镜）。
 *
 * 因此这里**不重复实现**警告类规则（行长上限、场景过短、`emphasis` 未命中）——
 * 重复一份只会让两边漂移。
 */
import { z } from 'zod';

import { FIGURE_KINDS } from './figureKinds';

export const STORYBOARD_VERSION = 1;

const nonEmptyText = z.string().min(1);

/** 短标注：键与值都必须是非空字符串。 */
export const labelsSchema = z.record(z.string(), nonEmptyText);

export const motionNameSchema = z.enum(['calm', 'normal', 'impact']);
export type MotionName = z.infer<typeof motionNameSchema>;

/**
 * `figure.kind` 的取值由注册表枚举（生成物 `figureKinds.ts`，任务 9.2）：
 * 写了一个注册表里没有的 kind，解析直接报错并列出已知组件——
 * 渲染层的 `SceneFigure` 本来也会在挂载时抛同样的错，提前到解析阶段
 * 只是让报错更早、更可定位。kind 可以缺省：缺省时按场景类型取默认组件。
 */
const knownKind = nonEmptyText.refine(
  (value) => (FIGURE_KINDS as readonly string[]).includes(value),
  {
    message: `figure.kind 必须是注册表里的组件（已知：${FIGURE_KINDS.join('、')}）`,
  },
);

export const figureSchema = z
  .object({
    kind: knownKind.optional(),
    labels: labelsSchema.optional(),
    motion: motionNameSchema.optional(),
    /**
     * 预留的几何覆盖。当前没有任何组件读取它，写了不会改变画面——
     * 与 Python 校验器的口径一致（那边会给出提醒）。
     */
    params: z.record(z.string(), z.unknown()).optional(),
    /**
     * 示意标记（任务 7.5）：分镜声明这组数值没有来源时置 true。
     * 图表组件会因此在画面上画出「示意」标；Python 校验器接受该标记，
     * 并在标记缺失/无处落点时给出提示。
     */
    schematic: z.boolean().optional(),
  })
  .strict();

export const emphasisSchema = z.array(nonEmptyText).nonempty();

/** 列表项既可以是字符串，也可以是 `{label, desc}`。 */
export const listItemSchema = z.union([
  nonEmptyText,
  z.object({ label: nonEmptyText, desc: z.string().optional() }).strict(),
]);
export type ListItem = z.infer<typeof listItemSchema>;

/**
 * 图节点：字符串，或 `{id, label}`。
 *
 * 节点在画面上显示的是 `label`（`figures.js` 的循环图就是 `name.label || name.id`），
 * `id` 只用来被 `edges` 引用。曾经这里只允许 `{id}`，于是**既有示例直接解析失败**：
 * `examples/keynote-baseline` 的循环图节点是 `{id, label}`，契约页整页画不出来，
 * 而 Python 校验器一直认为它合法（那边只要求 `id` 非空，不禁止别的键）。
 * 两个校验器的口径必须一致，否则「分镜通过了校验」在新旧两条路径上有两种含义。
 */
export const diagramNodeSchema = z.union([
  nonEmptyText,
  z.object({ id: nonEmptyText, label: z.string().optional() }).strict(),
]);

export const diagramEdgeSchema = z.union([
  z.tuple([nonEmptyText, nonEmptyText]),
  z.object({ from: nonEmptyText, to: nonEmptyText }).strict(),
]);

/** 各场景类型共有的可选项。 */
const sceneDataCommon = {
  annotations: labelsSchema.optional(),
  figure: figureSchema.optional(),
};

const titleData = z.object({
  text: nonEmptyText,
  subtitle: z.string().optional(),
  emphasis: emphasisSchema.optional(),
  ...sceneDataCommon,
});

const quoteData = z.object({
  text: nonEmptyText,
  attribution: z.string().optional(),
  emphasis: emphasisSchema.optional(),
  ...sceneDataCommon,
});

const comparisonData = z.object({
  left: nonEmptyText,
  right: nonEmptyText,
  title: z.string().optional(),
  ...sceneDataCommon,
});

const timelineData = z.object({
  items: z.array(listItemSchema).nonempty(),
  title: z.string().optional(),
  ...sceneDataCommon,
});

const diagramData = z.object({
  nodes: z.array(diagramNodeSchema).nonempty(),
  edges: z.array(diagramEdgeSchema).optional(),
  title: z.string().optional(),
  ...sceneDataCommon,
});

const numberData = z.object({
  value: z.union([z.number(), nonEmptyText]),
  label: z.string().optional(),
  caption: z.string().optional(),
  ...sceneDataCommon,
});

/** 图表数据点：标签 + 数值。组件不保存任何默认数据，缺了就在渲染时报错。 */
export const chartValueSchema = z
  .object({ label: nonEmptyText, value: z.number() })
  .strict();
export type ChartValue = z.infer<typeof chartValueSchema>;

const chartData = z.object({
  values: z.array(chartValueSchema).nonempty(),
  title: z.string().optional(),
  /** 图表类型：柱状（默认）/ 折线 / 饼图。 */
  chart: z.enum(['bar', 'line', 'pie']).optional(),
  ...sceneDataCommon,
});

const listData = z.object({
  items: z.array(listItemSchema).nonempty(),
  title: z.string().optional(),
  ...sceneDataCommon,
});

const conclusionData = z.object({
  text: nonEmptyText,
  action: z.string().optional(),
  emphasis: emphasisSchema.optional(),
  ...sceneDataCommon,
});

/**
 * 已知场景类型 → 其 `data` 的 schema。
 *
 * 类型不在表内时校验器只给**警告**（便于扩展），因此这里用 `passthrough` 的
 * 兜底 schema 接住未知类型，而不是直接报错——渲染层的职责是「画不出来要报错」，
 * 不是「类型不在清单里就拒绝」。
 */
export const KNOWN_SCENE_DATA = {
  title: titleData,
  quote: quoteData,
  comparison: comparisonData,
  timeline: timelineData,
  diagram: diagramData,
  number: numberData,
  chart: chartData,
  list: listData,
  conclusion: conclusionData,
} as const;

export type KnownSceneType = keyof typeof KNOWN_SCENE_DATA;

export const KNOWN_SCENE_TYPES = Object.keys(KNOWN_SCENE_DATA) as KnownSceneType[];

export function isKnownSceneType(type: string): type is KnownSceneType {
  return Object.prototype.hasOwnProperty.call(KNOWN_SCENE_DATA, type);
}

export const sceneSchema = z
  .object({
    id: z.string().regex(/^[A-Za-z0-9_-]+$/, 'id 只允许字母、数字、_ 与 -'),
    type: nonEmptyText,
    durationInFrames: z.number().int().positive(),
    narration: z.string().optional(),
    data: z.record(z.string(), z.unknown()),
    visual: z
      .object({
        layout: z.enum(['center', 'lower']).optional(),
        kicker: z.string().optional(),
      })
      .strict()
      .optional(),
  })
  .strict();

export type Scene = z.infer<typeof sceneSchema>;

export const sceneVisualSchema = sceneSchema.shape.visual;

export const storyboardSchema = z
  .object({
    version: z.literal(STORYBOARD_VERSION),
    fps: z.number().int().min(1).max(120),
    width: z.number().int().positive().default(1080),
    height: z.number().int().positive().default(1920),
    title: z.string().optional(),
    scenes: z.array(sceneSchema).nonempty(),
    visual: z
      .object({
        theme: z.enum(['dark', 'light']).default('dark'),
        preset: z.literal('keynote').optional(),
      })
      .strict()
      .optional(),
  })
  .strict();

export type Storyboard = z.infer<typeof storyboardSchema>;
export type StoryboardInput = z.input<typeof storyboardSchema>;

/** 解析并校验分镜。失败时把 zod 的 issue 路径拍平成可定位的字段路径。 */
export function parseStoryboard(input: unknown): Storyboard {
  const result = storyboardSchema.safeParse(input);
  if (result.success) {
    return result.data;
  }
  const detail = result.error.issues
    .map((issue) => `${issue.path.join('.') || '<root>'}: ${issue.message}`)
    .join('; ');
  throw new Error(`分镜脚本结构校验失败 —— ${detail}`);
}

/** 场景的 `data` 按类型解析；未知类型原样返回（渲染层会因找不到组件而报错）。 */
export function parseSceneData(scene: Scene): Record<string, unknown> {
  if (!isKnownSceneType(scene.type)) {
    return scene.data;
  }
  const schema = KNOWN_SCENE_DATA[scene.type];
  const result = schema.safeParse(scene.data);
  if (!result.success) {
    const detail = result.error.issues
      .map((issue) => `${issue.path.join('.') || '<root>'}: ${issue.message}`)
      .join('; ');
    throw new Error(`场景 ${scene.id} 的 data 校验失败 —— ${detail}`);
  }
  return result.data as Record<string, unknown>;
}

/**
 * 渲染时的默认分镜：Remotion Studio 打开时要有一个合法的最小输入。
 * 它不参与任何真实作品——真实分镜由 `--props` 传入。
 */
export const EMPTY_STORYBOARD: Storyboard = {
  version: STORYBOARD_VERSION,
  fps: 30,
  width: 1080,
  height: 1920,
  title: '（未传入分镜）',
  scenes: [
    {
      id: 'placeholder',
      type: 'title',
      durationInFrames: 30,
      data: { text: '未传入分镜' },
    },
  ],
};
