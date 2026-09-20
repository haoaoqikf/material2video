import { z } from 'zod';
import { PRIMITIVE_MOTIONS, PRIMITIVE_PROPS, PRIMITIVE_TYPES } from './primitiveTypes';

export const STORYBOARD_VERSION = 2;
const nonEmptyText = z.string().trim().min(1);
const nodeId = z.string().regex(/^[A-Za-z0-9_-]+$/, '节点 id 只允许字母、数字、_ 与 -');
export const motionRecipeSchema = z.enum(['reveal', 'fade', 'rise', 'count', 'draw']);
export type MotionRecipe = z.infer<typeof motionRecipeSchema>;
const primitiveTypeSchema = nonEmptyText.refine((value) => (PRIMITIVE_TYPES as readonly string[]).includes(value), { message: `未知视觉原语（已知：${PRIMITIVE_TYPES.join('、')}）` });

/** 每幕场景树的节点总数上限：控制渲染成本，也让容量超限尽早暴露。 */
export const MAX_NODES_PER_SCENE = 48;

export interface SceneNode {
  id: string; type: string; children?: SceneNode[]; contentRef?: string;
  role?: 'hero' | 'headline' | 'title' | 'body' | 'label' | 'caption';
  align?: 'start' | 'center' | 'end' | 'stretch'; gap?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  direction?: 'horizontal' | 'vertical' | 'ltr' | 'rtl' | 'ttb' | 'btt'; ratio?: '1:1' | '1:2' | '2:1' | '2:3' | '3:2'; columns?: 2 | 3;
  shape?: 'circle' | 'rect' | 'line' | 'spotlight' | 'ring'; state?: 'rest' | 'focus' | 'muted' | 'done';
  icon?: 'arrow' | 'check' | 'cross' | 'spark'; chart?: 'bar' | 'line' | 'pie'; sourceRef?: string;
  schematic?: boolean;
}

const directionSchema = z.enum(['horizontal', 'vertical', 'ltr', 'rtl', 'ttb', 'btt']);

export const sceneNodeSchema: z.ZodType<SceneNode> = z.lazy(() => z.object({
  id: nodeId, type: primitiveTypeSchema, children: z.array(sceneNodeSchema).max(12).optional(), contentRef: nonEmptyText.optional(),
  role: z.enum(['hero', 'headline', 'title', 'body', 'label', 'caption']).optional(),
  align: z.enum(['start', 'center', 'end', 'stretch']).optional(), gap: z.enum(['none', 'xs', 'sm', 'md', 'lg', 'xl']).optional(),
  direction: directionSchema.optional(), ratio: z.enum(['1:1', '1:2', '2:1', '2:3', '3:2']).optional(),
  columns: z.union([z.literal(2), z.literal(3)]).optional(), shape: z.enum(['circle', 'rect', 'line', 'spotlight', 'ring']).optional(),
  state: z.enum(['rest', 'focus', 'muted', 'done']).optional(), icon: z.enum(['arrow', 'check', 'cross', 'spark']).optional(),
  chart: z.enum(['bar', 'line', 'pie']).optional(), sourceRef: nonEmptyText.optional(), schematic: z.boolean().optional(),
}).strict());

export const visualIntentSchema = z.object({
  relation: z.enum(['focus', 'contrast', 'sequence', 'cause', 'cycle', 'collection']),
  focus: z.enum(['text', 'number', 'shape', 'chart', 'path']), composition: z.enum(['center', 'offset', 'split', 'radial', 'full']),
  density: z.enum(['sparse', 'balanced', 'dense']), tone: z.enum(['calm', 'tense', 'neutral', 'uplifting', 'decisive']),
}).strict();
export const motionSchema = z.object({ target: nodeId, recipe: motionRecipeSchema, startFrame: z.number().int().min(0).default(0), durationFrames: z.number().int().positive().optional() }).strict();

/** 结构性字段不属于原语属性声明，按类型校验属性时豁免。 */
const STRUCTURAL_NODE_KEYS = ['id', 'type', 'children'] as const;

export const sceneSchema = z.object({
  id: z.string().regex(/^[A-Za-z0-9_-]+$/, 'id 只允许字母、数字、_ 与 -'), type: nonEmptyText,
  durationInFrames: z.number().int().positive(), narration: z.string().optional(), data: z.record(z.string(), z.unknown()),
  visualIntent: visualIntentSchema, sceneTree: sceneNodeSchema, motions: z.array(motionSchema).default([]),
  visual: z.object({ kicker: z.string().optional() }).strict().optional(),
}).strict().superRefine((scene, ctx) => {
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
    if (node.sourceRef && !node.sourceRef.startsWith('data.')) ctx.addIssue({ code: 'custom', path: [...path, 'sourceRef'], message: '媒体引用必须以 data. 开头' });
    node.children?.forEach((child, index) => walk(child, [...path, 'children', index], depth + 1));
  };
  walk(scene.sceneTree, ['sceneTree'], 1);
  scene.motions.forEach((motion, index) => {
    if (!ids.has(motion.target)) ctx.addIssue({ code: 'custom', path: ['motions', index, 'target'], message: `动效目标 ${motion.target} 不存在` });
    if (motion.startFrame + (motion.durationFrames ?? 1) > scene.durationInFrames) ctx.addIssue({ code: 'custom', path: ['motions', index], message: '动效时间范围超出场景' });
    const supported = PRIMITIVE_MOTIONS[types.get(motion.target) ?? ''] ?? [];
    if (!supported.includes(motion.recipe)) ctx.addIssue({ code: 'custom', path: ['motions', index, 'recipe'], message: `原语 ${types.get(motion.target) ?? '（未知）'} 不支持动效 ${motion.recipe}` });
  });
});
export type Scene = z.infer<typeof sceneSchema>;

export const storyboardSchema = z.object({
  version: z.literal(STORYBOARD_VERSION), schemaVersion: z.literal(2), fps: z.number().int().min(1).max(120),
  width: z.number().int().positive().default(1080), height: z.number().int().positive().default(1920), title: z.string().optional(),
  visualDirection: z.object({ motif: nonEmptyText, compositionBias: z.enum(['centered', 'asymmetric', 'mixed']), density: z.enum(['sparse', 'balanced', 'dense']), rhythm: z.enum(['restrained', 'steady', 'dynamic']), avoid: z.array(nonEmptyText).default([]) }).strict(),
  scenes: z.array(sceneSchema).nonempty(), visual: z.object({ theme: z.enum(['dark', 'light']).default('dark'), preset: z.literal('keynote').optional() }).strict().optional(),
}).strict();
export type Storyboard = z.infer<typeof storyboardSchema>;
export type StoryboardInput = z.input<typeof storyboardSchema>;
export function parseStoryboard(input: unknown): Storyboard {
  const result = storyboardSchema.safeParse(input); if (result.success) return result.data;
  if (input && typeof input === 'object' && (input as Record<string, unknown>).version === 1) throw new Error('旧版分镜不能直接渲染；请先运行 migrate_storyboard.py 显式迁移到场景树 v2');
  const detail = result.error.issues.map((issue) => `${issue.path.join('.') || '<root>'}: ${issue.message}`).join('; '); throw new Error(`分镜脚本结构校验失败 —— ${detail}`);
}
export const EMPTY_STORYBOARD: Storyboard = {
  version: 2, schemaVersion: 2, fps: 30, width: 1080, height: 1920, title: '（未传入分镜）',
  visualDirection: { motif: 'placeholder', compositionBias: 'centered', density: 'sparse', rhythm: 'restrained', avoid: [] },
  scenes: [{ id: 'placeholder', type: 'title', durationInFrames: 30, data: { text: '未传入分镜' }, visualIntent: { relation: 'focus', focus: 'text', composition: 'center', density: 'sparse', tone: 'neutral' }, sceneTree: { id: 'root', type: 'stack', children: [{ id: 'text', type: 'text', contentRef: 'data.text', role: 'headline' }] }, motions: [] }],
};
