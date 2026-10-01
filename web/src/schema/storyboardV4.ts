import { z } from 'zod';
import {
  beatSchema, directingBriefSchema, moduleSpecifierSchema, motionRecipeSchema, narrationSegmentSchema,
  sceneNodeSchema, staggerSchema, visualIntentSchema,
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
  const objectIds = new Set<string>();
  storyboard.world.objects.forEach((object, index) => {
    if (objectIds.has(object.id)) ctx.addIssue({ code: 'custom', path: ['world', 'objects', index, 'id'], message: `重复 world object id: ${object.id}` });
    objectIds.add(object.id);
  });
  if (!objectIds.has(storyboard.world.camera.focus)) {
    ctx.addIssue({ code: 'custom', path: ['world', 'camera', 'focus'], message: 'focus 必须引用已声明全局对象' });
  }
  const treeNodeIds = new Set<string>();
  const collectNodeIds = (node: z.infer<typeof sceneNodeSchema>) => {
    if (treeNodeIds.has(node.id)) {
      ctx.addIssue({ code: 'custom', path: ['world', 'sceneTree'], message: `重复全局节点 id: ${node.id}` });
    }
    treeNodeIds.add(node.id);
    node.children?.forEach(collectNodeIds);
  };
  if (storyboard.world.sceneTree) {
    collectNodeIds(storyboard.world.sceneTree);
    storyboard.world.objects.forEach((object, index) => {
      if (!treeNodeIds.has(object.id)) ctx.addIssue({ code: 'custom', path: ['world', 'objects', index, 'id'], message: 'tree renderer 的持续对象须映射到同 id 全局节点' });
    });
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
  storyboard.world.motions.forEach((motion, index) => {
    const targets = motion.target ? [motion.target] : (motion.targets ?? []);
    targets.forEach((target, targetIndex) => {
      const exists = storyboard.world.renderer.kind === 'tree' ? treeNodeIds.has(target) : objectIds.has(target);
      if (!exists) ctx.addIssue({ code: 'custom', path: ['world', 'motions', index, 'target', targetIndex], message: 'motion 引用了未知全局对象或节点' });
    });
    if ('beatId' in motion.binding && !beatIds.has(motion.binding.beatId)) {
      ctx.addIssue({ code: 'custom', path: ['world', 'motions', index, 'binding'], message: 'motion binding 引用了未知 beat' });
    }
    if ('stageId' in motion.binding && !stageIds.has(motion.binding.stageId)) {
      ctx.addIssue({ code: 'custom', path: ['world', 'motions', index, 'binding'], message: 'motion binding 引用了未知 stage' });
    }
  });
});

export type StoryboardV4 = z.infer<typeof storyboardV4Schema>;
