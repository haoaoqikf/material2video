/**
 * 代码场景公开 API（作品可导入的唯一项目内部模块）。
 *
 * 作品通过别名 `@a2v/scene` 导入这里定义的类型与工具；依赖白名单检查
 * 把这个别名当作「项目公开的内部 API」放行，仓库其余内部文件不对作品开放。
 *
 * 设计约束（见 openspec 变更 add-code-driven-scenes 的 design.md）：
 * - 时间轴不属于作品：组件拿到的只有当前帧、幕内帧与进度，
 *   没有 durationInFrames、没有相邻幕、没有 fps 之外的时钟——
 *   分镜是顺序与时长的单一真源，代码模块不可能形成第二套时间轴。
 * - 随机必须是稳定种子随机：`random()` 由场景与节点标识播种，
 *   同一帧重复求值、随机寻帧、跨机器渲染都得到同一序列。
 * - 探针协议是最小可观察面：`useProbeProps` 输出稳定 DOM 标记，
 *   让现有内容探针与 C/K/M 闸门继续量测自由场景。
 */
import type { CSSProperties } from 'react';

/** 共享画布参数：与分镜声明的输出尺寸一致，场景不得假设其他尺寸。 */
export interface A2VCanvas {
  width: number;
  height: number;
}

/** 主题信息：与共享设计令牌同一来源（`visual.theme` / `visual.preset`）。 */
export interface A2VThemeInfo {
  theme: 'dark' | 'light';
  preset?: 'keynote';
}

/** 注入给代码场景的幕级数据：内容仍以分镜为真源。 */
export interface A2VSceneInfo<Data = unknown> {
  id: string;
  type: string;
  /** 本幕的 `data` 字段原样传入。 */
  data: Data;
  /** 本幕持续多少帧（只读参考：进度已由共享层算好）。 */
  durationInFrames: number;
  kicker?: string;
}

/**
 * 代码场景组件 props。
 *
 * 字段集合是封闭的：作品组件不能声明自己的时间轴字段
 * （`durationInFrames`、相邻幕、总帧数都不在这里），
 * 类型层面保证「第二套时间真源」无法产生。
 */
export interface A2VCodeSceneProps<Data = unknown> {
  scene: A2VSceneInfo<Data>;
  /** 全局帧号：整片时间轴上的绝对帧。 */
  frame: number;
  /** 幕内帧号：本幕从 0 重新计数。 */
  localFrame: number;
  /** 幕内进度：`localFrame / (durationInFrames - 1)`，夹在 [0, 1]。 */
  progress: number;
  fps: number;
  canvas: A2VCanvas;
  theme: A2VThemeInfo;
  /**
   * 稳定种子随机：`random(node)` 为节点标识派生独立序列；
   * 省略节点时使用场景级默认序列。同一输入永远返回同一序列。
   */
  random: (node?: string) => number;
}

/** 代码场景组件类型：作品模块的默认导出必须是它。 */
export type A2VCodeScene<Data = unknown> = React.FC<A2VCodeSceneProps<Data>>;

/* ------------------------------------------------------------------ */
/* 稳定种子随机                                                         */
/* ------------------------------------------------------------------ */

/** FNV-1a 32 位散列：把字符串折叠成种子。纯函数，无时钟依赖。 */
export function hashSeed(text: string): number {
  let hash = 0x811c9dc5;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

/**
 * mulberry32：小而快的确定性 PRNG。
 * 相同种子产生相同序列，与求值顺序无关（每次调用从种子重新出发）。
 */
export function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** 由场景标识与节点标识派生稳定随机函数；节点间序列相互独立。 */
export function createSceneRandom(sceneId: string, nodeId?: string): (node?: string) => number {
  return (node?: string) => mulberry32(hashSeed(`${sceneId}::${node ?? nodeId ?? 'scene'}`))();
}

/* ------------------------------------------------------------------ */
/* 探针协议                                                             */
/* ------------------------------------------------------------------ */

/**
 * 语义角色。与场景树原语的 role 枚举同源：
 * 内容探针按角色读取文字、K 系列闸门按角色检查排版。
 */
export type A2VProbeRole = 'hero' | 'headline' | 'title' | 'body' | 'label' | 'caption';

/**
 * 生成代码场景的最小探针标记：
 * - 根节点由共享包装器自动打 `data-a2v-scene`，组件不必重复；
 * - 需要体检的节点用 `node` 声明稳定 id，用 `role` 声明语义角色；
 * - 文字要被内容探针读到时必须带 `node` + `role`。
 *
 * 用法：`<div {...probe({ node: 'headline', role: 'headline' })}>…</div>`
 */
export function probe(options: { node: string; role?: A2VProbeRole; inside?: string; schematic?: boolean }): {
  'data-a2v-node': string;
  'data-a2v-role'?: string;
  'data-a2v-inside'?: string;
  'data-a2v-schematic'?: string;
} {
  return {
    'data-a2v-node': options.node,
    ...(options.role ? { 'data-a2v-role': options.role } : {}),
    ...(options.inside ? { 'data-a2v-inside': options.inside } : {}),
    ...(options.schematic ? { 'data-a2v-schematic': '' } : {}),
  };
}

/**
 * 帧驱动样式的便捷工具：把 0..1 进度映射为受控 CSS 属性。
 * 只输出确定性属性（透明度、位移、缩放），不接受任意 transform 字符串拼接之外的东西。
 */
export function frameStyle(
  progress: number,
  params: { opacity?: boolean; rise?: number; scale?: number } = {},
): CSSProperties {
  const clamped = Math.min(1, Math.max(0, progress));
  const style: CSSProperties = {};
  if (params.opacity) style.opacity = clamped;
  if (params.rise !== undefined) style.transform = `translateY(${(1 - clamped) * params.rise}px)`;
  if (params.scale !== undefined) {
    const value = params.scale * clamped;
    style.transform = `${style.transform ?? ''} scale(${value})`.trim();
  }
  return style;
}
