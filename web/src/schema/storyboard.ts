import { z } from 'zod';
import { ICON_NAMES, PRIMITIVE_ACTIONS, PRIMITIVE_MOTIONS, PRIMITIVE_PROPS, PRIMITIVE_TYPES, SEMANTIC_ACTIONS, type IconName } from './primitiveTypes';
import { supportsContinuityTransform } from '@/registry';

export const STORYBOARD_VERSION = 3;
const nonEmptyText = z.string().trim().min(1);
const nodeId = z.string().regex(/^[A-Za-z0-9_-]+$/, '节点 id 只允许字母、数字、_ 与 -');
export const motionRecipeSchema = z.enum(['reveal', 'fade', 'rise', 'count', 'draw']);
export const motionPhaseSchema = z.enum(['establish', 'change', 'result']);
export const staggerSchema = z.object({
  kind: z.enum(['forward', 'reverse', 'center', 'path']),
  intervalFrames: z.number().int().min(2).max(12).default(4),
  path: z.array(nodeId).min(2).optional(),
}).strict().superRefine((value, ctx) => {
  if (value.kind === 'path' && !value.path) ctx.addIssue({ code: 'custom', path: ['path'], message: '路径传播必须声明 path' });
  if (value.kind !== 'path' && value.path) ctx.addIssue({ code: 'custom', path: ['path'], message: '只有路径传播可以声明 path' });
});
const primitiveTypeSchema = nonEmptyText.refine((value) => (PRIMITIVE_TYPES as readonly string[]).includes(value), { message: `未知视觉原语（已知：${PRIMITIVE_TYPES.join('、')}）` });

/** 每幕场景树的节点总数上限：控制渲染成本，也让容量超限尽早暴露。 */
export const MAX_NODES_PER_SCENE = 48;

/**
 * 代码场景模块标识：作品 `scenes/` 目录下的相对路径（不含扩展名）。
 * 只允许字母、数字、`_`、`-` 与 `/` 分段——扩展名、盘符、绝对路径与 `..`
 * 都在字符层面被拒绝，路径穿越没有入口。
 */
export const moduleSpecifierPattern = /^[A-Za-z0-9_-]+(?:\/[A-Za-z0-9_-]+)*$/;
export const moduleSpecifierSchema = z
  .string()
  .regex(moduleSpecifierPattern, '模块标识只允许字母、数字、_ 与 -（可用 / 分段）；不含扩展名或路径穿越');

/** 渲染模式判别联合：`tree` 走场景树解释器，`code` 挂载作品级模块。 */
export const treeRendererSchema = z.object({ kind: z.literal('tree') }).strict();
export const codeRendererSchema = z.object({ kind: z.literal('code'), module: moduleSpecifierSchema }).strict();
export const rendererSchema = z.discriminatedUnion('kind', [treeRendererSchema, codeRendererSchema]);

export interface SceneNode {
  id: string; type: string; children?: SceneNode[]; contentRef?: string;
  role?: 'hero' | 'headline' | 'title' | 'body' | 'label' | 'caption';
  align?: 'start' | 'center' | 'end' | 'stretch'; gap?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  direction?: 'horizontal' | 'vertical' | 'ltr' | 'rtl' | 'ttb' | 'btt' | 'cw' | 'ccw'; ratio?: '1:1' | '1:2' | '2:1' | '2:3' | '3:2'; columns?: 2 | 3;
  shape?: 'circle' | 'rect' | 'line' | 'spotlight' | 'ring'; state?: 'rest' | 'focus' | 'muted' | 'done';
  icon?: IconName; chart?: 'bar' | 'line' | 'pie'; sourceRef?: string;
  schematic?: boolean;
}

const directionSchema = z.enum(['horizontal', 'vertical', 'ltr', 'rtl', 'ttb', 'btt', 'cw', 'ccw']);

export const sceneNodeSchema: z.ZodType<SceneNode> = z.lazy(() => z.object({
  id: nodeId, type: primitiveTypeSchema, children: z.array(sceneNodeSchema).max(12).optional(), contentRef: nonEmptyText.optional(),
  role: z.enum(['hero', 'headline', 'title', 'body', 'label', 'caption']).optional(),
  align: z.enum(['start', 'center', 'end', 'stretch']).optional(), gap: z.enum(['none', 'xs', 'sm', 'md', 'lg', 'xl']).optional(),
  direction: directionSchema.optional(), ratio: z.enum(['1:1', '1:2', '2:1', '2:3', '3:2']).optional(),
  columns: z.union([z.literal(2), z.literal(3)]).optional(), shape: z.enum(['circle', 'rect', 'line', 'spotlight', 'ring']).optional(),
  state: z.enum(['rest', 'focus', 'muted', 'done']).optional(), icon: z.enum(ICON_NAMES).optional(),
  chart: z.enum(['bar', 'line', 'pie']).optional(), sourceRef: nonEmptyText.optional(), schematic: z.boolean().optional(),
}).strict());

/**
 * 逐幕视觉论证声明：导演意图字段，composition 不读取它们。
 * 保留在 schema 里供 v3 契约报告呈现导演意图；
 * 校验语义由 Python 端 `a2v.visual_narrative` 负责。
 */
export const visualModeSchema = z.enum(['metaphor', 'process', 'comparison', 'cycle', 'chart', 'image', 'typography']);

export const visualIntentSchema = z.object({
  relation: z.enum(['focus', 'contrast', 'sequence', 'cause', 'cycle', 'collection']),
  focus: z.enum(['text', 'number', 'shape', 'chart', 'path']), composition: z.enum(['center', 'offset', 'split', 'radial', 'full']),
  density: z.enum(['sparse', 'balanced', 'dense']), tone: z.enum(['calm', 'tense', 'neutral', 'uplifting', 'decisive']),
  mode: visualModeSchema, claim: nonEmptyText, showWithoutText: nonEmptyText,
  primaryObject: nonEmptyText, motionMeaning: nonEmptyText,
}).strict();
export const motionSchema = z.object({
  target: nodeId.optional(), targets: z.array(nodeId).min(1).optional(), recipe: motionRecipeSchema,
  phase: motionPhaseSchema.optional(), beatId: nodeId.optional(), stagger: staggerSchema.optional(),
  durationFrames: z.number().int().positive().optional(),
}).strict().superRefine((motion, ctx) => {
  if (Boolean(motion.target) === Boolean(motion.targets)) ctx.addIssue({ code: 'custom', path: ['target'], message: 'target 与 targets 必须二选一' });
  if (Boolean(motion.phase) === Boolean(motion.beatId)) ctx.addIssue({ code: 'custom', path: ['phase'], message: 'motion 必须且只能绑定 phase 或 beatId' });
  if (motion.stagger && !motion.targets) ctx.addIssue({ code: 'custom', path: ['stagger'], message: 'stagger 只适用于 targets 节点组' });
  if (motion.targets && !motion.stagger) ctx.addIssue({ code: 'custom', path: ['stagger'], message: '编组 motion 必须声明错峰策略 stagger' });
});

export const directingVersionSchema = z.literal(1);
export const directingBriefSchema = z.object({ thesis: nonEmptyText, audienceShift: nonEmptyText, emotionalArc: z.array(nonEmptyText).min(2), visualMotif: nonEmptyText, stylePack: z.enum(['editorial', 'cinematic', 'technical', 'poetic']), avoid: z.array(nonEmptyText).default([]) }).strict();
export const cameraSegmentSchema = z.object({
  kind: z.enum(['hold', 'push-in', 'pull-out', 'pan', 'reframe', 'settle']),
  beatId: nodeId.optional(), phase: z.enum(['establish', 'change', 'result', 'settle']).optional(), focus: nodeId.optional(),
  direction: z.enum(['left', 'right', 'up', 'down']).optional(), intensity: z.number().min(0).max(1).default(0.5),
}).strict().superRefine((segment, ctx) => {
  if (Boolean(segment.beatId) === Boolean(segment.phase)) ctx.addIssue({ code: 'custom', path: ['beatId'], message: '镜头段必须在 beatId 与 phase 中二选一' });
  if (segment.kind === 'pan' && !segment.direction) ctx.addIssue({ code: 'custom', path: ['direction'], message: 'pan 必须声明方向' });
});
export const cameraSchema = z.object({ shot: z.enum(['macro', 'close', 'medium', 'wide']), composition: z.enum(['center', 'left', 'right', 'split', 'full']), depth: z.enum(['flat', 'layered']), focus: nodeId, segments: z.array(cameraSegmentSchema).min(1) }).strict();
export const transitionSchema = z.object({
  kind: z.enum(['inherit', 'transform', 'decompose', 'recompose', 'dissolve', 'break']),
  source: nodeId.optional(), target: nodeId.optional(),
  sources: z.array(nodeId).min(2).max(6).optional(), targets: z.array(nodeId).min(2).max(6).optional(),
  meaning: nonEmptyText,
}).strict();

/* ------------------------------------------------------------------ */
/* 语义节拍（beats）与分段口播                                          */
/* ------------------------------------------------------------------ */

/** 受控语义动作：与 `web/src/registry/registry.json` 同一份词汇表。 */
export const semanticActionSchema = z.enum(SEMANTIC_ACTIONS);

/**
 * 分段口播：每段有唯一 id、非空文本和有效 beat 引用。
 * 它与字符串 `narration` 互斥——完整口播由各段按顺序拼接，
 * 不保存第二份完整文本，因此重复短语也能稳定引用。
 */
export const speechSchema = z.object({
  rate: z.string().regex(/^[+-]\d+%$/).refine((v) => Math.abs(Number(v.slice(0, -1))) <= 50).optional(),
  pauseBeforeMs: z.number().int().min(0).max(2000).optional(),
  pauseAfterMs: z.number().int().min(0).max(2000).optional(),
}).strict();
export const narrationSegmentSchema = z.object({ id: nodeId, text: nonEmptyText, beatId: nodeId, speech: speechSchema.optional() }).strict();
const localSoundRef = nonEmptyText.refine((v) => !/[\\:]/.test(v) && !v.startsWith('/') && v.split('/').every((p) => p && p !== '.' && p !== '..'), '声音必须是本地相对路径');
export const soundtrackSchema = z.object({
  music: z.object({ sourceRef: localSoundRef, gainDb: z.number().min(-60).max(0).optional(), loop: z.boolean().optional(), fadeInMs: z.number().int().min(0).max(60000).optional(), fadeOutMs: z.number().int().min(0).max(60000).optional() }).strict().optional(),
  effects: z.array(z.object({ sourceRef: localSoundRef, sceneId: nodeId, beatId: nodeId, offsetMs: z.number().int().min(-60000).max(60000).optional(), gainDb: z.number().min(-60).max(0).optional() }).strict()).max(128).optional(),
}).strict();

/** 语义节拍：受控动作 + 至少一个目标节点 + 非空 meaning（这一步让观众多看懂什么）。 */
export const beatSchema = z.object({
  id: nodeId, action: semanticActionSchema, targets: z.array(nodeId).min(1), meaning: nonEmptyText, before: nonEmptyText.optional(), after: nonEmptyText.optional(), relation: nonEmptyText.optional(),
}).strict();

/**
 * 已解析到帧区间的节拍：媒体准备按真实 TTS 词边界写入，
 * `startFrame` 含、`endFrame` 不含，与字幕 cue 和场景区间同一约定。
 * 它是派生字段：源分镜不能声明，只有 `storyboard.effective.json` 会带。
 */
export const resolvedBeatSchema = beatSchema.extend({
  startFrame: z.number().int().min(0), endFrame: z.number().int().positive(),
}).strict();

export type NarrationSegment = z.infer<typeof narrationSegmentSchema>;
export type Beat = z.infer<typeof beatSchema>;
export type ResolvedBeat = z.infer<typeof resolvedBeatSchema>;

/** 结构性字段不属于原语属性声明，按类型校验属性时豁免。 */
const STRUCTURAL_NODE_KEYS = ['id', 'type', 'children'] as const;

export const sceneSchema = z.object({
  id: z.string().regex(/^[A-Za-z0-9_-]+$/, 'id 只允许字母、数字、_ 与 -'), type: nonEmptyText,
  durationInFrames: z.number().int().positive(), data: z.record(z.string(), z.unknown()),
  narrationSegments: z.array(narrationSegmentSchema).optional(), beats: z.array(beatSchema).optional(),
  resolvedBeats: z.array(resolvedBeatSchema).optional(),
  visualIntent: visualIntentSchema, camera: cameraSchema, transition: transitionSchema.optional(), renderer: rendererSchema, sceneTree: sceneNodeSchema.optional(), motions: z.array(motionSchema).default([]),
  visual: z.object({ kicker: z.string().optional() }).strict().optional(),
}).strict().superRefine((scene, ctx) => {
  const isCode = scene.renderer?.kind === 'code';
  if (isCode) {
    // 互斥字段：代码场景的画面由模块实现，不能同时携带场景树
    if (scene.sceneTree) ctx.addIssue({ code: 'custom', path: ['sceneTree'], message: 'code 场景不能声明 sceneTree：渲染模式每幕二选一' });
    if (scene.motions.length > 0) ctx.addIssue({ code: 'custom', path: ['motions'], message: 'code 场景不支持 motions：动效由场景代码按帧号实现' });
  } else if (!scene.sceneTree) {
    ctx.addIssue({ code: 'custom', path: ['sceneTree'], message: 'tree 场景必须包含一棵场景树（sceneTree）' });
  }
  if (scene.id !== '__first_scene__' && scene.transition === undefined) { /* root continuity is checked with storyboard order */ }
  const tree = scene.sceneTree;
  if (!tree) {
    // 代码场景：节点是运行期探针 id，静态核验不了，只做跨字段规则
    validateBeats(scene, ctx, null);
    return;
  }
  const ids = new Map<string, (string | number)[]>(); const types = new Map<string, string>();
  let nodeCount = 0;
  const walk = (node: SceneNode, path: (string | number)[], depth: number): void => {
    nodeCount += 1;
    if (nodeCount > MAX_NODES_PER_SCENE) {
      ctx.addIssue({ code: 'custom', path, message: `场景树最多 ${MAX_NODES_PER_SCENE} 个节点` });
    }
    if (depth > 8) ctx.addIssue({ code: 'custom', path, message: '场景树深度不能超过 8' });
    const allowed = new Set<string>([...STRUCTURAL_NODE_KEYS, ...(PRIMITIVE_PROPS[node.type] ?? [])]);
    for (const key of Object.keys(node)) {
      if (!allowed.has(key)) ctx.addIssue({ code: 'custom', path: [...path, key], message: `原语 ${node.type} 不支持属性 ${key}` });
    }
    const previous = ids.get(node.id);
    if (previous) ctx.addIssue({ code: 'custom', path: [...path, 'id'], message: `节点 id ${node.id} 与 ${previous.join('.')} 重复` });
    else { ids.set(node.id, [...path, 'id']); types.set(node.id, node.type); }
    if (node.contentRef && !node.contentRef.startsWith('data.')) ctx.addIssue({ code: 'custom', path: [...path, 'contentRef'], message: '内容引用必须以 data. 开头' });
    // 量级类原语没有内容引用就只会画一个空盘：这是静默错误，直接报出来。
    if ((node.type === 'gauge' || node.type === 'pictogram') && !node.contentRef) {
      ctx.addIssue({ code: 'custom', path: [...path, 'contentRef'], message: `${node.type} 必须用 contentRef 指向 data 中的数值（0–100）` });
    }
    if (node.sourceRef && !node.sourceRef.startsWith('data.')) ctx.addIssue({ code: 'custom', path: [...path, 'sourceRef'], message: '媒体引用必须以 data. 开头' });
    node.children?.forEach((child, index) => walk(child, [...path, 'children', index], depth + 1));
  };
  walk(tree, ['sceneTree'], 1);
  scene.motions.forEach((motion, index) => {
    const targets = motion.targets ?? (motion.target ? [motion.target] : []);
    targets.forEach((target, position) => { if (!ids.has(target)) ctx.addIssue({ code: 'custom', path: ['motions', index, motion.targets ? 'targets' : 'target', ...(motion.targets ? [position] : [])], message: `动效目标 ${target} 不存在` }); });
    if (motion.beatId && !scene.beats?.some((beat) => beat.id === motion.beatId)) ctx.addIssue({ code: 'custom', path: ['motions', index, 'beatId'], message: `动效引用了不存在的 beat ${motion.beatId}` });

    targets.forEach((target) => { const supported = PRIMITIVE_MOTIONS[types.get(target) ?? ''] ?? []; if (!supported.includes(motion.recipe)) ctx.addIssue({ code: 'custom', path: ['motions', index, 'recipe'], message: `原语 ${types.get(target) ?? '（未知）'} 不支持动效 ${motion.recipe}` }); });
    if (motion.durationFrames !== undefined && motion.durationFrames > scene.durationInFrames) ctx.addIssue({ code: 'custom', path: ['motions', index, 'durationFrames'], message: '动效时长不能超过场景时长' });
    const staggerOffset = motion.targets && motion.stagger ? (motion.targets.length - 1) * motion.stagger.intervalFrames : 0;
    if ((motion.durationFrames ?? 1) + staggerOffset > scene.durationInFrames) ctx.addIssue({ code: 'custom', path: ['motions', index], message: '编组错峰动效超出场景时间轴' });
  });
  scene.camera?.segments?.forEach((segment, index) => {
    if (segment.beatId && !scene.beats?.some((beat) => beat.id === segment.beatId)) ctx.addIssue({ code: 'custom', path: ['camera', 'segments', index, 'beatId'], message: `镜头段引用了不存在的 beat ${segment.beatId}` });
    const focus = segment.focus ?? scene.camera?.focus; if (focus && !ids.has(focus)) ctx.addIssue({ code: 'custom', path: ['camera', 'segments', index, 'focus'], message: `镜头焦点 ${focus} 不存在` });
  });
  validateBeats(scene, ctx, types);
});

/**
 * 语义节拍与分段口播的跨字段校验：与 Python 端 `a2v.storyboard` 同一口径。
 *
 * 单项形状（id 形状、动作枚举、目标非空、meaning 非空）由 zod 的字段声明
 * 负责；这里只查引用完整性与顺序：重复 id、悬空 beat、孤立 beat、
 * 不连续引用、目标原语是否支持该动作，以及派生 `resolvedBeats` 的
 * 顺序/重叠/越界。
 *
 * `types` 为 null 表示这一幕是代码场景（没有场景树），节点由作品模块在
 * 运行期用探针 id 声明，静态核验不了。
 */
function validateBeats(scene: Scene, ctx: z.RefinementCtx, types: Map<string, string> | null): void {
  const segments = scene.narrationSegments;
  const beats = scene.beats;
  const indexById = new Map<string, number>();
  beats?.forEach((beat, index) => {
    const previous = indexById.get(beat.id);
    if (previous !== undefined) {
      ctx.addIssue({ code: 'custom', path: ['beats', index, 'id'], message: `beat id ${beat.id} 与 beats[${previous}] 重复` });
    } else {
      indexById.set(beat.id, index);
    }
    if (!types) return;
    beat.targets.forEach((target, position) => {
      const primitive = types.get(target);
      if (primitive === undefined) {
        ctx.addIssue({ code: 'custom', path: ['beats', index, 'targets', position], message: `beat 目标 ${target} 不存在` });
        return;
      }
      const allowed = PRIMITIVE_ACTIONS[primitive] ?? [];
      if (!allowed.includes(beat.action)) {
        ctx.addIssue({ code: 'custom', path: ['beats', index, 'targets', position], message: `原语 ${primitive} 不支持语义动作 ${beat.action}（允许：${allowed.join('、') || '无'}）` });
      }
    });
  });
  if (!segments) {
    if (beats) ctx.addIssue({ code: 'custom', path: ['narrationSegments'], message: 'beats 必须由分段口播驱动：narrationSegments 必须是非空数组' });
    validateResolvedBeats(scene, ctx);
    return;
  }
  if (segments.length > scene.durationInFrames) {
    ctx.addIssue({ code: 'custom', path: ['narrationSegments'], message: `场景只有 ${scene.durationInFrames} 帧，装不下 ${segments.length} 段口播：每段至少需要 1 帧` });
  }
  const segmentIds = new Map<string, number>();
  const referenced: string[] = [];
  segments.forEach((segment, index) => {
    const previous = segmentIds.get(segment.id);
    if (previous !== undefined) {
      ctx.addIssue({ code: 'custom', path: ['narrationSegments', index, 'id'], message: `口播段 id ${segment.id} 与 narrationSegments[${previous}] 重复` });
    } else {
      segmentIds.set(segment.id, index);
    }
    if (!indexById.has(segment.beatId)) {
      ctx.addIssue({ code: 'custom', path: ['narrationSegments', index, 'beatId'], message: `口播段引用了不存在的 beat ${segment.beatId}（悬空引用）` });
    } else {
      referenced.push(segment.beatId);
    }
  });
  beats?.forEach((beat, index) => {
    if (!referenced.includes(beat.id)) {
      ctx.addIssue({ code: 'custom', path: ['beats', index], message: `beat ${beat.id} 没有被任何口播段引用：没有可解析的时间，画面不知道该在哪一帧动` });
    }
  });
  const runs = referenced.filter((id, position) => position === 0 || referenced[position - 1] !== id);
  for (const id of new Set(runs.filter((item, index) => runs.indexOf(item) !== index))) {
    ctx.addIssue({ code: 'custom', path: ['narrationSegments'], message: `beat ${id} 的口播段不连续：同一 beat 的引用必须相邻，否则时间轴会倒退或重叠` });
  }
  validateResolvedBeats(scene, ctx);
}

/** 派生时间轴的自检：倒退、重叠、越界都要在读取阶段失败。 */
function validateResolvedBeats(scene: Scene, ctx: z.RefinementCtx): void {
  const resolved = scene.resolvedBeats;
  if (!resolved) return;
  let previousEnd = 0;
  resolved.forEach((beat, index) => {
    if (beat.endFrame <= beat.startFrame) {
      ctx.addIssue({ code: 'custom', path: ['resolvedBeats', index], message: `帧区间为空（${beat.startFrame}–${beat.endFrame}）` });
    }
    if (beat.startFrame < previousEnd) {
      ctx.addIssue({ code: 'custom', path: ['resolvedBeats', index], message: `帧区间相对上一条倒退或重叠（起点 ${beat.startFrame} < ${previousEnd}）` });
    }
    if (beat.endFrame > scene.durationInFrames) {
      ctx.addIssue({ code: 'custom', path: ['resolvedBeats', index], message: `帧区间超出场景（${beat.endFrame} > ${scene.durationInFrames}）` });
    }
    previousEnd = Math.max(previousEnd, beat.endFrame);
  });
}
export type Scene = z.infer<typeof sceneSchema>;

export const storyboardSchema = z.object({
  version: z.literal(STORYBOARD_VERSION), schemaVersion: z.literal(3), fps: z.number().int().min(1).max(120),
  width: z.number().int().positive().default(1080), height: z.number().int().positive().default(1920), title: z.string().optional(),
  visualDirection: z.object({ motif: nonEmptyText, compositionBias: z.enum(['centered', 'asymmetric', 'mixed']), density: z.enum(['sparse', 'balanced', 'dense']), rhythm: z.enum(['restrained', 'steady', 'dynamic']), avoid: z.array(nonEmptyText).default([]) }).strict(),
  directingVersion: directingVersionSchema, directingBrief: directingBriefSchema,
  soundtrack: soundtrackSchema.optional(),
  // 仅媒体派生 props 携带；Python 源分镜校验拒绝此字段。
  subtitleCues: z.array(z.object({ start: z.number().nonnegative(), end: z.number().positive(), text: nonEmptyText }).strict()).optional(),
  scenes: z.array(sceneSchema).nonempty(), visual: z.object({ theme: z.enum(['dark', 'light']).default('dark'), preset: z.literal('keynote') }).strict(),
}).strict().superRefine((storyboard, ctx) => {
  if (storyboard.directingVersion === 1 && !storyboard.directingBrief) {
    ctx.addIssue({ code: 'custom', path: ['directingBrief'], message: 'directingVersion=1 必须同时提供 directingBrief' });
  }
  validateContinuity(storyboard, ctx);
  storyboard.soundtrack?.effects?.forEach((effect, index) => {
    const scene = storyboard.scenes.find((s) => s.id === effect.sceneId);
    if (!scene?.beats?.some((b) => b.id === effect.beatId)) ctx.addIssue({ code: 'custom', path: ['soundtrack', 'effects', index], message: '音效场景或节拍不存在' });
  });
});

function nodeTypes(scene: Scene): Map<string, string> {
  const result = new Map<string, string>();
  const walk = (node?: SceneNode): void => { if (!node) return; result.set(node.id, node.type); node.children?.forEach(walk); };
  walk(scene.sceneTree);
  return result;
}

/** 跨幕映射只接受显式节点和注册表声明的有限变形，不做相似度猜测。 */
function validateContinuity(storyboard: { scenes: Scene[] }, ctx: z.RefinementCtx): void {
  storyboard.scenes.forEach((scene, index) => {
    const transition = scene.transition;
    if (index > 0 && !transition) ctx.addIssue({ code: 'custom', path: ['scenes', index, 'transition'], message: 'v3 第二幕起必须显式声明跨幕 transition' });
    if (!transition) return;
    const path = ['scenes', index, 'transition'] as (string | number)[];
    if (index === 0) { ctx.addIssue({ code: 'custom', path, message: '第一幕不能声明跨幕 transition' }); return; }
    const previousTypes = nodeTypes(storyboard.scenes[index - 1]!);
    const currentTypes = nodeTypes(scene);
    const requireNode = (field: 'source' | 'target', value: string | undefined, types: Map<string, string>, owner: string): string | undefined => {
      if (!value) { ctx.addIssue({ code: 'custom', path: [...path, field], message: `${transition.kind} 转场必须声明 ${field}` }); return undefined; }
      const type = types.get(value);
      if (!type) ctx.addIssue({ code: 'custom', path: [...path, field], message: `${field} 节点 ${value} 不存在于${owner}` });
      return type;
    };
    const requireNodes = (field: 'sources' | 'targets', values: string[] | undefined, types: Map<string, string>, owner: string): string[] => {
      if (!values) { ctx.addIssue({ code: 'custom', path: [...path, field], message: `${transition.kind} 转场必须声明至少两个 ${field}` }); return []; }
      if (new Set(values).size !== values.length) ctx.addIssue({ code: 'custom', path: [...path, field], message: `${field} 不能包含重复节点` });
      values.forEach((value, position) => { if (!types.has(value)) ctx.addIssue({ code: 'custom', path: [...path, field, position], message: `${field} 节点 ${value} 不存在于${owner}` }); });
      return values;
    };
    const rejectFields = (...fields: Array<'source' | 'target' | 'sources' | 'targets'>): void => {
      fields.forEach((field) => { if (transition[field] !== undefined) ctx.addIssue({ code: 'custom', path: [...path, field], message: `${transition.kind} 转场不接受 ${field}` }); });
    };
    if (transition.kind === 'inherit' || transition.kind === 'transform') {
      rejectFields('sources', 'targets');
      const sourceType = requireNode('source', transition.source, previousTypes, '上一幕');
      const targetType = requireNode('target', transition.target, currentTypes, '当前幕');
      if (sourceType && targetType && transition.kind === 'inherit' && sourceType !== targetType) {
        ctx.addIssue({ code: 'custom', path: [...path, 'target'], message: `inherit 只能继承同类原语（${sourceType} → ${targetType}）` });
      }
      if (sourceType && targetType && transition.kind === 'transform' && !supportsContinuityTransform(sourceType, targetType)) {
        ctx.addIssue({ code: 'custom', path: [...path, 'target'], message: `未登记的跨幕变形 ${sourceType} → ${targetType}` });
      }
    } else if (transition.kind === 'decompose') {
      rejectFields('target', 'sources');
      requireNode('source', transition.source, previousTypes, '上一幕');
      requireNodes('targets', transition.targets, currentTypes, '当前幕');
    } else if (transition.kind === 'recompose') {
      rejectFields('source', 'targets');
      requireNodes('sources', transition.sources, previousTypes, '上一幕');
      requireNode('target', transition.target, currentTypes, '当前幕');
    } else if (transition.kind === 'break') {
      rejectFields('target', 'sources', 'targets');
      requireNode('source', transition.source, previousTypes, '上一幕');
    } else if (transition.kind === 'dissolve') {
      rejectFields('source', 'target', 'sources', 'targets');
    }
  });
}
export type Storyboard = z.infer<typeof storyboardSchema>;
export function parseStoryboard(input: unknown): Storyboard {
  const result = storyboardSchema.safeParse(input); if (result.success) return result.data;
  if (input && typeof input === 'object' && ((input as Record<string, unknown>).version === 1 || (input as Record<string, unknown>).version === 2)) throw new Error('不支持 v3 之前分镜；请按分镜 v3 契约重新编排');
  const detail = result.error.issues.map((issue) => `${issue.path.join('.') || '<root>'}: ${issue.message}`).join('; '); throw new Error(`分镜脚本结构校验失败 —— ${detail}`);
}
export const EMPTY_STORYBOARD: Storyboard = {
  version: 3, schemaVersion: 3, directingVersion: 1, directingBrief: { thesis: 'placeholder', audienceShift: 'placeholder', emotionalArc: ['calm', 'clear'], visualMotif: 'line', stylePack: 'editorial', avoid: [] }, visual: { theme: 'dark', preset: 'keynote' }, fps: 30, width: 1080, height: 1920, title: '（未传入分镜）',
  visualDirection: { motif: 'placeholder', compositionBias: 'centered', density: 'sparse', rhythm: 'restrained', avoid: [] },
  scenes: [{ id: 'placeholder', type: 'title', durationInFrames: 30, data: { text: '未传入分镜' }, visualIntent: { relation: 'focus', focus: 'text', composition: 'center', density: 'sparse', tone: 'neutral', mode: 'typography', claim: 'placeholder', showWithoutText: 'A single text anchor.', primaryObject: 'headline', motionMeaning: 'The headline enters.' }, camera: { shot: 'medium', composition: 'center', depth: 'flat', focus: 'text', segments: [{ kind: 'hold', phase: 'establish', intensity: 0 }] }, renderer: { kind: 'tree' }, sceneTree: { id: 'root', type: 'stack', children: [{ id: 'text', type: 'text', contentRef: 'data.text', role: 'headline' }] }, motions: [] }],
};
