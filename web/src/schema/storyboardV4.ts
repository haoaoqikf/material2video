import { z } from 'zod';
import { primitiveDefinition } from '@/registry';
import { countArticleCharacters } from './articleText';
import {
  beatSchema, directingBriefSchema, moduleSpecifierSchema, motionRecipeSchema, narrationSegmentSchema,
  sceneNodeSchema, staggerSchema, visualIntentSchema, type SceneNode,
} from './storyboard';

const idSchema = z.string().regex(/^[A-Za-z0-9_-]+$/);
const nonEmpty = z.string().trim().min(1);

const rendererSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal('tree') }).strict(),
  z.object({ kind: z.literal('code'), module: moduleSpecifierSchema }).strict(),
]);

const objectSchema = z.object({
  id: idSchema,
  role: z.enum(['primary', 'supporting', 'annotation']),
  description: nonEmpty,
}).strict();

const bindingSchema = z.union([
  z.object({ beatId: idSchema }).strict(),
  z.object({ stageId: idSchema, phase: z.enum(['establish', 'change', 'result', 'settle']) }).strict(),
]);

const stateTrackSchema = z.object({
  id: idSchema, target: idSchema,
  property: z.enum(['visible', 'state', 'value', 'contentRef', 'sourceRef']),
  binding: bindingSchema, to: z.unknown(),
  interpolation: z.enum(['step-end', 'linear', 'ease-in', 'ease-out', 'ease-in-out']),
}).strict();

const cameraSegmentSchema = z.object({
  id: idSchema,
  kind: z.enum(['hold', 'push-in', 'pull-out', 'pan', 'reframe', 'settle']),
  binding: bindingSchema,
  focus: idSchema.optional(),
  direction: z.enum(['left', 'right', 'up', 'down']).optional(),
  intensity: z.number().min(0).max(1).optional(),
}).strict().superRefine((segment, ctx) => {
  if (segment.kind === 'pan' && !segment.direction) {
    ctx.addIssue({ code: 'custom', path: ['direction'], message: 'pan 必须声明方向' });
  }
});

const cameraSchema = z.object({
  shot: z.enum(['macro', 'close', 'medium', 'wide']),
  composition: z.enum(['center', 'left', 'right', 'split', 'full']),
  depth: z.enum(['flat', 'layered']), focus: idSchema,
  segments: z.array(cameraSegmentSchema).min(1),
}).strict();

const motionSchema = z.object({
  target: idSchema.optional(), targets: z.array(idSchema).min(1).optional(),
  recipe: motionRecipeSchema, binding: bindingSchema, stagger: staggerSchema.optional(),
}).strict().superRefine((motion, ctx) => {
  if (Boolean(motion.target) === Boolean(motion.targets)) {
    ctx.addIssue({ code: 'custom', path: ['target'], message: 'target 与 targets 必须二选一' });
  }
  if (motion.targets && !motion.stagger) {
    ctx.addIssue({ code: 'custom', path: ['stagger'], message: '编组 motion 必须声明错峰策略' });
  }
});

const localSoundRef = nonEmpty.refine((value) => !/[\\:]/.test(value) && !value.startsWith('/')
  && value.split('/').every((part) => part && part !== '.' && part !== '..'), '声音必须是本地相对路径');
const soundtrackSchema = z.object({
  music: z.object({ sourceRef: localSoundRef, gainDb: z.number().min(-60).max(0).optional(),
    loop: z.boolean().optional(), fadeInMs: z.number().int().min(0).max(60000).optional(),
    fadeOutMs: z.number().int().min(0).max(60000).optional() }).strict().optional(),
  effects: z.array(z.object({ sourceRef: localSoundRef, stageId: idSchema, beatId: idSchema,
    offsetMs: z.number().int().min(-60000).max(60000).optional(), gainDb: z.number().min(-60).max(0).optional() }).strict()).max(128).optional(),
}).strict();

const worldSchema = z.object({
  id: idSchema, claim: nonEmpty, metaphor: nonEmpty,
  objects: z.array(objectSchema).min(1), renderer: rendererSchema,
  data: z.record(z.string(), z.unknown()),
  sceneTree: sceneNodeSchema.optional(),
  stateTracks: z.array(stateTrackSchema),
  motions: z.array(motionSchema),
  camera: cameraSchema,
}).strict().superRefine((world, ctx) => {
  if (!world.objects.some((item) => item.role === 'primary')) {
    ctx.addIssue({ code: 'custom', path: ['objects'], message: 'world 至少需要一个 primary 对象' });
  }
  if (world.renderer.kind === 'tree' && !world.sceneTree) {
    ctx.addIssue({ code: 'custom', path: ['sceneTree'], message: 'tree renderer 必须提供全片 sceneTree' });
  }
  if (world.renderer.kind === 'code' && world.sceneTree) {
    ctx.addIssue({ code: 'custom', path: ['sceneTree'], message: 'code renderer 不得同时声明 sceneTree' });
  }
});

const stageSchema = z.object({
  id: idSchema, durationInFrames: z.number().int().positive(),
  data: z.record(z.string(), z.unknown()), visualIntent: visualIntentSchema,
  narrationSegments: z.array(narrationSegmentSchema).optional(),
  beats: z.array(beatSchema).optional(),
}).strict().superRefine((stage, ctx) => {
  if (stage.narrationSegments && !stage.beats) {
    ctx.addIssue({ code: 'custom', path: ['beats'], message: '有口播阶段必须声明 beats' });
  }
});

export const storyboardV4Schema = z.object({
  version: z.literal(4), schemaVersion: z.literal(4), directingVersion: z.literal(2),
  fps: z.number().int().min(1).max(120), width: z.number().int().positive(), height: z.number().int().positive(),
  title: nonEmpty.optional(),
  visualDirection: z.object({ motif: nonEmpty,
    compositionBias: z.enum(['centered', 'asymmetric', 'mixed']),
    density: z.enum(['sparse', 'balanced', 'dense']),
    rhythm: z.enum(['restrained', 'steady', 'dynamic']), avoid: z.array(nonEmpty),
  }).strict(),
  directingBrief: directingBriefSchema,
  visual: z.object({ theme: z.enum(['dark', 'light']), preset: z.literal('keynote') }).strict(),
  soundtrack: soundtrackSchema.optional(), world: worldSchema, stages: z.array(stageSchema).min(1),
}).strict().superRefine((storyboard, ctx) => {
  const totalFrames = storyboard.stages.reduce((sum, stage) => sum + stage.durationInFrames, 0);
  if (totalFrames < 35 * storyboard.fps || totalFrames > 45 * storyboard.fps) {
    ctx.addIssue({ code: 'custom', path: ['stages'], message: `声明全片时长为 ${(totalFrames / storyboard.fps).toFixed(2)} 秒，必须在 35～45 秒（含边界）` });
  }
  const narration = storyboard.stages.flatMap((stage) => stage.narrationSegments ?? []).map((segment) => segment.text).join('');
  const narrationCount = countArticleCharacters(narration);
  if (narrationCount === 0) {
    ctx.addIssue({ code: 'custom', path: ['stages'], message: '标准作品必须有完整口播，静音不能豁免篇幅要求' });
  } else if (narrationCount < 130 || narrationCount > 170) {
    ctx.addIssue({ code: 'custom', path: ['stages'], message: `最终口播为 ${narrationCount} 字，必须在 130～170 字` });
  }
  const objectIds = new Set<string>();
  storyboard.world.objects.forEach((object, index) => {
    if (objectIds.has(object.id)) ctx.addIssue({ code: 'custom', path: ['world', 'objects', index, 'id'], message: `重复 world object id: ${object.id}` });
    objectIds.add(object.id);
  });
  if (!objectIds.has(storyboard.world.camera.focus)) {
    ctx.addIssue({ code: 'custom', path: ['world', 'camera', 'focus'], message: 'focus 必须引用已声明全局对象' });
  }
  const treeNodeIds = new Set<string>();
  const treeNodes = new Map<string, SceneNode>();
  let treeNodeCount = 0;
  const collectNodeIds = (node: SceneNode, depth = 1) => {
    treeNodeCount += 1;
    if (depth > 8) ctx.addIssue({ code: 'custom', path: ['world', 'sceneTree'], message: '场景树深度不能超过 8' });
    if (treeNodeIds.has(node.id)) {
      ctx.addIssue({ code: 'custom', path: ['world', 'sceneTree'], message: `重复全局节点 id: ${node.id}` });
    }
    treeNodeIds.add(node.id);
    treeNodes.set(node.id, node);
    const primitive = primitiveDefinition(node.type);
    const childCount = node.children?.length ?? 0;
    if (primitive && (childCount < primitive.children[0] || childCount > primitive.children[1])) {
      ctx.addIssue({ code: 'custom', path: ['world', 'sceneTree', node.id, 'children'], message: `原语 ${node.type} 子节点数量不符合注册表` });
    }
    if (primitive) {
      for (const key of Object.keys(node)) {
        if (!['id', 'type', 'children'].includes(key) && !primitive.props.includes(key)) {
          ctx.addIssue({ code: 'custom', path: ['world', 'sceneTree', node.id, key], message: `原语 ${node.type} 不支持属性 ${key}` });
        }
      }
    }
    node.children?.forEach((child) => collectNodeIds(child, depth + 1));
  };
  if (storyboard.world.sceneTree) {
    collectNodeIds(storyboard.world.sceneTree);
    storyboard.world.objects.forEach((object, index) => {
      if (!treeNodeIds.has(object.id)) ctx.addIssue({ code: 'custom', path: ['world', 'objects', index, 'id'], message: 'tree renderer 的持续对象须映射到同 id 全局节点' });
    });
    if (treeNodeCount > 48) ctx.addIssue({ code: 'custom', path: ['world', 'sceneTree'], message: `全片节点数 ${treeNodeCount} 超出上限 48` });
  }
  const stageIds = new Set<string>();
  const beatIds = new Set<string>();
  const narrationIds = new Set<string>();
  storyboard.stages.forEach((stage, index) => {
    const localBeatIds = new Set(stage.beats?.map((beat) => beat.id) ?? []);
    if (stageIds.has(stage.id)) ctx.addIssue({ code: 'custom', path: ['stages', index, 'id'], message: `重复 stage id: ${stage.id}` });
    stageIds.add(stage.id);
    stage.beats?.forEach((beat, beatIndex) => {
      if (beatIds.has(beat.id)) ctx.addIssue({ code: 'custom', path: ['stages', index, 'beats', beatIndex, 'id'], message: `重复 beat id: ${beat.id}` });
      beatIds.add(beat.id);
    });
    stage.narrationSegments?.forEach((segment, segmentIndex) => {
      if (narrationIds.has(segment.id)) ctx.addIssue({ code: 'custom', path: ['stages', index, 'narrationSegments', segmentIndex, 'id'], message: `重复 narration segment id: ${segment.id}` });
      narrationIds.add(segment.id);
      if (!localBeatIds.has(segment.beatId)) {
        ctx.addIssue({ code: 'custom', path: ['stages', index, 'narrationSegments', segmentIndex, 'beatId'], message: '必须引用本 stage 中存在的 beat' });
      }
    });
  });
  storyboard.stages.forEach((stage, index) => {
    stage.beats?.forEach((beat, beatIndex) => {
      beat.targets.forEach((target, targetIndex) => {
        if (!storyboard.world.objects.some((item) => item.id === target)) {
          ctx.addIssue({ code: 'custom', path: ['stages', index, 'beats', beatIndex, 'targets', targetIndex], message: `未知 world object: ${target}` });
        }
      });
    });
  });
  storyboard.world.camera.segments.forEach((segment, index) => {
    if (segment.focus && !objectIds.has(segment.focus)) {
      ctx.addIssue({ code: 'custom', path: ['world', 'camera', 'segments', index, 'focus'], message: 'focus 必须引用已声明全局对象' });
    }
    if ('beatId' in segment.binding && !beatIds.has(segment.binding.beatId)) {
      ctx.addIssue({ code: 'custom', path: ['world', 'camera', 'segments', index, 'binding'], message: 'camera binding 引用了未知 beat' });
    }
    if ('stageId' in segment.binding && !stageIds.has(segment.binding.stageId)) {
      ctx.addIssue({ code: 'custom', path: ['world', 'camera', 'segments', index, 'binding'], message: 'camera binding 引用了未知 stage' });
    }
  });
  const beatTargets = new Map<string, Set<string>>();
  storyboard.stages.forEach((stage) => stage.beats?.forEach((beat) => {
    beatTargets.set(beat.id, new Set(beat.targets));
  }));
  const dataAt = (root: unknown, reference: string): unknown => reference.split('.').reduce<unknown>((current, key) =>
    current && typeof current === 'object' && key in current ? (current as Record<string, unknown>)[key] : undefined, root);
  const numericShape = (value: unknown): unknown => {
    if (typeof value === 'number' && Number.isFinite(value)) return 'number';
    if (Array.isArray(value)) {
      const parts = value.map(numericShape);
      return parts.every((part) => part !== undefined) ? parts : undefined;
    }
    if (value && typeof value === 'object') {
      const parts = Object.fromEntries(Object.entries(value).map(([key, item]) => [key, numericShape(item)]));
      return Object.values(parts).every((part) => part !== undefined) ? parts : undefined;
    }
    return undefined;
  };
  const bindings = new Set<string>();
  storyboard.world.stateTracks.forEach((track, index) => {
    const path = ['world', 'stateTracks', index] as (string | number)[];
    const targetNode = treeNodes.get(track.target);
    const targetType = targetNode?.type;
    const primitive = targetType ? primitiveDefinition(targetType) : undefined;
    if (storyboard.world.renderer.kind === 'tree' && track.property !== 'visible'
      && (!primitive || !primitive.props.includes(track.property))) {
      ctx.addIssue({ code: 'custom', path: [...path, 'property'], message: `${targetType ?? '目标'} 不支持属性 ${track.property}` });
    }
    const codeObjects = storyboard.world.data.objects;
    const codeTarget = codeObjects && typeof codeObjects === 'object'
      ? (codeObjects as Record<string, unknown>)[track.target] : undefined;
    const baselineNode = storyboard.world.renderer.kind === 'tree' ? targetNode : codeTarget;
    let baseline: unknown;
    if (track.property === 'visible') baseline = baselineNode && typeof baselineNode === 'object'
      && 'visible' in baselineNode ? (baselineNode as Record<string, unknown>).visible : true;
    else if (baselineNode && typeof baselineNode === 'object') {
      baseline = (baselineNode as Record<string, unknown>)[track.property];
      if (track.property === 'value' && storyboard.world.renderer.kind === 'tree') {
        const ref = (baselineNode as SceneNode).contentRef;
        baseline = ref ? dataAt(storyboard.world.data, ref) : undefined;
      }
    }
    if (baseline === undefined) {
      ctx.addIssue({ code: 'custom', path: [...path, 'target'], message: `对象 ${track.target} 的 ${track.property} 缺少基础值` });
    } else if (track.property === 'visible') {
      if (typeof baseline !== 'boolean' || typeof track.to !== 'boolean') ctx.addIssue({ code: 'custom', path: [...path, 'to'], message: 'visible 轨道必须使用布尔值' });
      if (track.interpolation !== 'step-end') ctx.addIssue({ code: 'custom', path: [...path, 'interpolation'], message: 'visible 是离散属性，只允许 step-end' });
    } else if (track.property === 'state') {
      const states = ['rest', 'focus', 'muted', 'done'];
      if (!states.includes(String(baseline)) || !states.includes(String(track.to))) ctx.addIssue({ code: 'custom', path: [...path, 'to'], message: 'state 轨道值必须来自受控集合' });
      if (track.interpolation !== 'step-end') ctx.addIssue({ code: 'custom', path: [...path, 'interpolation'], message: 'state 是离散属性，只允许 step-end' });
    } else if (track.property === 'contentRef' || track.property === 'sourceRef') {
      if (typeof baseline !== 'string' || typeof track.to !== 'string' || !track.to.trim()) ctx.addIssue({ code: 'custom', path: [...path, 'to'], message: `${track.property} 轨道必须使用非空引用` });
      if (track.interpolation !== 'step-end') ctx.addIssue({ code: 'custom', path: [...path, 'interpolation'], message: `${track.property} 是离散属性，只允许 step-end` });
    } else {
      if (storyboard.world.renderer.kind === 'tree' && targetType && !['number', 'chart', 'gauge', 'pictogram'].includes(targetType)) {
        ctx.addIssue({ code: 'custom', path: [...path, 'target'], message: `${targetType} 不支持 value 属性` });
      }
      const fromShape = numericShape(baseline);
      const toShape = numericShape(track.to);
      if (fromShape === undefined || toShape === undefined) ctx.addIssue({ code: 'custom', path: [...path, 'to'], message: 'value 轨道必须使用数值或同形数值结构' });
      else if (JSON.stringify(fromShape) !== JSON.stringify(toShape) && track.interpolation !== 'step-end') {
        ctx.addIssue({ code: 'custom', path: [...path, 'interpolation'], message: '数值结构改变时只允许 step-end' });
      }
    }
    const bindingKey = 'beatId' in track.binding ? `beat:${track.binding.beatId}` : `stage:${track.binding.stageId}:${track.binding.phase}`;
    const conflictKey = `${track.target}\0${track.property}\0${bindingKey}`;
    if (bindings.has(conflictKey)) ctx.addIssue({ code: 'custom', path: [...path, 'binding'], message: '同一对象属性存在重叠轨道绑定' });
    bindings.add(conflictKey);
    if ('beatId' in track.binding && !beatIds.has(track.binding.beatId)) ctx.addIssue({ code: 'custom', path: [...path, 'binding'], message: '引用未知全局 beat' });
    if ('beatId' in track.binding && beatIds.has(track.binding.beatId)
      && !beatTargets.get(track.binding.beatId)?.has(track.target)) {
      ctx.addIssue({ code: 'custom', path: [...path, 'target'], message: '轨道目标不在绑定 beat 的 targets 中' });
    }
    if ('stageId' in track.binding && !stageIds.has(track.binding.stageId)) ctx.addIssue({ code: 'custom', path: [...path, 'binding'], message: '引用未知 stage' });
  });
  storyboard.world.motions.forEach((motion, index) => {
    const targets = motion.target ? [motion.target] : (motion.targets ?? []);
    targets.forEach((target, targetIndex) => {
      const exists = storyboard.world.renderer.kind === 'tree' ? treeNodeIds.has(target) : objectIds.has(target);
      if (!exists) ctx.addIssue({ code: 'custom', path: ['world', 'motions', index, 'target', targetIndex], message: 'motion 引用了未知全局对象或节点' });
    });
    if ('beatId' in motion.binding && !beatIds.has(motion.binding.beatId)) {
      ctx.addIssue({ code: 'custom', path: ['world', 'motions', index, 'binding'], message: 'motion binding 引用了未知 beat' });
    }
    const motionBeatId = 'beatId' in motion.binding ? motion.binding.beatId : undefined;
    if (motionBeatId && beatIds.has(motionBeatId)) {
      targets.forEach((target, targetIndex) => {
        if (!beatTargets.get(motionBeatId)?.has(target)) {
          ctx.addIssue({ code: 'custom', path: ['world', 'motions', index, 'target', targetIndex], message: 'motion 目标不在绑定 beat 的 targets 中' });
        }
      });
    }
    if ('stageId' in motion.binding && !stageIds.has(motion.binding.stageId)) {
      ctx.addIssue({ code: 'custom', path: ['world', 'motions', index, 'binding'], message: 'motion binding 引用了未知 stage' });
    }
  });
});

export type StoryboardV4 = z.infer<typeof storyboardV4Schema>;
