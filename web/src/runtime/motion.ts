/**
 * 动效配方层（由 `assets/timeline.js` 的动效部分移植为 TypeScript）。
 *
 * 这一层解决的问题：入场动效由「弹性曲线 + 收敛时机 + 常驻微动」三件事组成，
 * 这三件事决定整支片子的手感。如果每个组件自己写阻尼、频率、收敛帧数，
 * 手感就会随组件漂移，而且没有一处可以整体调整。
 * 所以：**数字只写在这里，组件只说「这是什么元素、移动多远」**。
 *
 * 移植原则是**配方数值逐值照搬**，一个都不改：这些数字是实测调出来的
 * （收敛时刻、过冲量、呼吸周期都对着曲线核对过），改一个字都会与旧路径的
 * 抽帧对照对不上。`assets/timeline.js` 与这里的一致性由
 * `motion.test.ts` 逐项对照，而不是靠人记得两边一样。
 *
 * 与旧实现的差别只有两处，都是 React 决定的：
 *   1. 旧版直接写 DOM（`el.style.transform = …`）。这里只**算**描述，
 *      由组件决定怎么写——同一帧同一结果的约束因此更容易看清；
 *   2. 旧版靠 `window.A2VSpring` 这个全局找求解器，找不到才抛错。
 *      这里改成静态 `import`：缺依赖是**编译期**失败，比运行到某一幕才炸更早。
 */

import { position, restSeconds } from '@/runtime/spring';

/** 只走这三条曲线，混用更多会让整支片子的手感不一致（见设计宪法 C4）。 */
export const EASE = { enter: 'outQuint', gate: 'outCubic', both: 'inOutCubic' } as const;

export type EasingName = 'linear' | 'outCubic' | 'inOutCubic' | 'outQuint' | 'outBack';

/** 缓动函数集合。只在帧位置已知时使用，因此结果可复现。 */
export const EASING: Record<EasingName, (t: number) => number> = {
  linear: (t) => t,
  outCubic: (t) => 1 - (1 - t) ** 3,
  inOutCubic: (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2),
  outQuint: (t) => 1 - (1 - t) ** 5,
  outBack: (t) => {
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2;
  },
};

/**
 * 两档配方按元素的落点分：
 *   surface —— 画面上的表面（卡片、文字块），位移略大、呼吸略快；
 *   figure  —— 图形本体（SVG 分组），位移略小，避免与几何线条打架。
 */
export interface MotionRecipe {
  distance: number;
  scale: number;
  periodFrames: number;
  amplitude: number;
  springResponse: number;
  springDampingFraction: number;
  settleAt: number;
  settleFrames: number;
}

export const RECIPES: Record<'surface' | 'figure', MotionRecipe> = {
  surface: {
    distance: 44,
    scale: 1,
    periodFrames: 130,
    amplitude: 3,
    springResponse: 0.44,
    springDampingFraction: 0.9,
    settleAt: 0.24,
    settleFrames: 36,
  },
  figure: {
    distance: 40,
    scale: 1,
    periodFrames: 140,
    amplitude: 2.5,
    springResponse: 0.44,
    springDampingFraction: 0.9,
    settleAt: 0.24,
    settleFrames: 36,
  },
};

/** 节奏名 → 速度倍率。分镜只写名字，节拍由运行时算。 */
export const TEMPO_SPEED: Record<string, number> = { calm: 0.82, normal: 1, impact: 1.24 };

/*
 * 弹性预设。组件里写一串数字时，读者看不出它和别处的数字有什么意图差别，
 * 改一处也想不到别处还有几处。给它们起名之后，「这个元素该有多弹」就成了可讨论的事。
 *
 * 两个参数都是物理量，不是手感凑出来的系数：
 *   response        自然周期（秒）。越小越快，直接决定「多久到位」。
 *   dampingFraction 阻尼比 ζ。过冲量只由它决定，与快慢无关：
 *                   ζ=1 临界不过冲；过冲峰值 ≈ e^(-πζ/√(1-ζ²))。
 * 收敛时间（进 2% 带内）≈ 3.91/(ζω₀) 秒，ω₀ = 2π/response。
 * 这些数不是估的，`motion.test.ts` 会按曲线实测核对。
 */
export const SPRINGS: Record<string, { response: number; dampingFraction: number }> = {
  enter: { response: 0.5, dampingFraction: 1 }, // 温和入场，临界阻尼，一点不过冲；约 0.46s 收敛
  firm: { response: 0.44, dampingFraction: 0.9 }, // 图形主体到位（默认）：过冲约 0.2%，约 0.31s 收敛
  lively: { response: 0.4, dampingFraction: 0.62 }, // 有分量的落点：过冲约 8.4%，约 0.40s 收敛
  snap: { response: 0.28, dampingFraction: 0.8 }, // 小元素快速归位：过冲约 1.5%，约 0.22s 收敛
};

/** 幕内常驻微动的周期。振幅按元素分档，周期统一，否则同屏各晃各的。 */
export const DRIFT_PERIOD = 150;

export function clamp(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value;
}

export function lerp(from: number, to: number, t: number): number {
  return from + (to - from) * t;
}

/** 计算动画片段进度。`localFrame` 是场景内帧号，返回 0..1。 */
export function progress(
  localFrame: number,
  startFrame: number,
  durationFrames: number,
  easingName?: EasingName,
): number {
  if (durationFrames <= 0) {
    return localFrame >= startFrame ? 1 : 0;
  }
  const t = clamp((localFrame - startFrame) / durationFrames, 0, 1);
  const fn = easingName ? EASING[easingName] : EASING.linear;
  return (fn ?? EASING.linear)(t);
}

/** 逐项呈现时第 index 项的起始帧。 */
export function stagger(index: number, stepFrames: number, baseFrame = 0): number {
  return baseFrame + index * stepFrames;
}

/**
 * 距某个起始帧已经过去的秒数——弹簧与所有物理量动效的输入。
 *
 * 为什么要有这个而不是继续用 `progress()`：弹簧的时间尺度是秒，
 * 而 `progress()` 返回的是**已经缓动过**的 0..1 进度。把缓动后的进度
 * 喂给弹簧等于把两条曲线串起来，response（自然周期）就失去了意义
 * （曾经如此：3 帧走完 58px，而注释写着「0.6 秒收敛」）。
 */
export function since(frame: number, startFrame = 0, fps = 30): number {
  const rate = fps > 0 ? fps : 30;
  return Math.max(0, frame - startFrame) / rate;
}

/**
 * 物理弹簧：把「距入场起点已经过去的秒数」映射为 0→1 的进度。
 *
 * **必须喂线性的时间。** 这里曾经是 `1 - e^(-damping·x)·cos(frequency·π·x)`，
 * x 取的是调用方已经缓动过的进度——两条曲线串起来，弹簧自己的时间尺度就没了意义。
 * 后果实测过：第 1 幕标题的 58px 位移在**第 1 帧就走完 36px、第 3 帧完成 97%**，
 * 之后只剩 0.76px 的过冲；而注释还写着「30fps 下约 0.6 秒收敛」。
 */
export function spring(
  seconds: number,
  options: { response?: number; dampingFraction?: number } = {},
): number {
  const response = options.response === undefined ? 0.44 : options.response;
  const dampingFraction = options.dampingFraction === undefined ? 0.9 : options.dampingFraction;
  if (!(seconds > 0)) {
    return 0;
  }
  // 弹簧只会无限逼近 1，这条让「到位」有确切时刻：包络进 0.1% 带内就返回 1。
  // 不用「位移小于阈值」判断——那会在 lively 回弹的半途把它截掉。
  if (seconds >= restSeconds(response, dampingFraction)) {
    return 1;
  }
  return position(seconds, response, dampingFraction);
}

/**
 * 把 0..1 的进度线性映射到任意数值区间，作为位移、缩放、透明度、光晕强度的
 * 统一驱动。默认把结果钳制在区间内，避免 spring 的过冲把数值推出合理范围。
 */
export function range(
  t: number,
  from: number,
  to: number,
  options: { clamp?: boolean } = {},
): number {
  const x = options.clamp === false ? t : clamp(t, 0, 1);
  return from + (to - from) * x;
}

/**
 * 常驻微动：让画面在「入场动画已经结束」的后半段仍有一点活性。
 * 配音会把场景拉长，如果后段完全静止，成片会显得卡住。
 *
 * 只依赖帧号与常量，因此逐帧可复现；振幅建议 ≤ 6px，周期建议 90–150 帧。
 */
export function breath(
  localFrame: number,
  options: { periodFrames?: number; amplitude?: number; phase?: number } = {},
): number {
  const period = options.periodFrames === undefined ? 120 : options.periodFrames;
  const amplitude = options.amplitude === undefined ? 4 : options.amplitude;
  if (!period) {
    return 0;
  }
  return Math.sin(((localFrame + (options.phase ?? 0)) / period) * Math.PI * 2) * amplitude;
}

export function recipe(name?: string): MotionRecipe {
  if (name === 'figure') {
    return RECIPES.figure;
  }
  return RECIPES.surface;
}

/** 按预设名取弹性值；未知名字用 firm，不抛错。入参是秒数。 */
export function springBy(seconds: number, name?: string): number {
  return spring(seconds, (name && SPRINGS[name]) || SPRINGS.firm);
}

/** 幕内常驻微动：周期统一，只按元素给振幅与相位。 */
export function idle(
  localFrame: number,
  options: { periodFrames?: number; amplitude?: number; phase?: number } = {},
): number {
  return breath(localFrame, {
    periodFrames: options.periodFrames === undefined ? DRIFT_PERIOD : options.periodFrames,
    amplitude: options.amplitude === undefined ? 3 : options.amplitude,
    phase: options.phase ?? 0,
  });
}

/** 节奏名对应的速度倍率；未知名字按正常速度处理，不抛错。 */
export function tempo(name?: string): number {
  return (name && TEMPO_SPEED[name]) || TEMPO_SPEED.normal;
}

/**
 * 动效状态。
 *
 * 组件只交「幕内第几帧、这一幕多少帧、这一幕什么节奏」三件事；
 * 旧运行时把这些藏在模块级状态里，让「同一帧同一结果」依赖于调用顺序。
 */
export interface MotionState {
  localFrame: number;
  sceneDurationFrames: number;
  /** 那一幕声明里给的节奏名（`data.figure.motion`）；缺省按 normal 处理 */
  motion?: string;
}

/** 当前场景的节奏倍率。从 state 里读，而不是模块级变量。 */
export function tempoOf(state: MotionState): number {
  return tempo(state.motion);
}

/**
 * 场景内的比例点换算成绝对帧号，并按该幕的节奏缩放。
 *
 * 用比例而不是绝对帧：配音把场景拉长后，入场节奏保持不变。
 * 节奏越快，同一个比例点越早到达，后半段自然留出更长的停留。
 */
export function motionBeat(state: MotionState, fraction: number): number {
  if (!state || !state.sceneDurationFrames) {
    return 0;
  }
  return (fraction * state.sceneDurationFrames) / tempoOf(state);
}

/**
 * 入场收敛度：入场结束后把缩放钉在 1，并让常驻微动淡入。
 *
 * 没有这一步，弹性曲线的过冲会把元素长期留在一个略大的尺寸上，
 * 常驻微动也会在入场阶段就开始晃。
 */
export function settleWith(
  state: MotionState,
  base: MotionRecipe,
  options: { at?: number; frames?: number } = {},
): number {
  const at = options.at === undefined ? base.settleAt : options.at;
  const frames = options.frames === undefined ? base.settleFrames : options.frames;
  return progress(state.localFrame, motionBeat(state, at), frames, EASE.both);
}

export function settle(
  state: MotionState,
  options: { recipe?: string; at?: number; frames?: number } = {},
): number {
  return settleWith(state, recipe(options.recipe), options);
}

/** 入场配方算出来的描述。写法（HTML 的 style 还是 SVG 的属性）由组件决定。 */
export interface EntranceMotion {
  /** 弹性进度，峰值可能略大于 1 */
  from: number;
  axis: 'x' | 'y';
  /** 位移量（px），已按元素方向与距离算好 */
  shift: number;
  /** 常驻微动，已按收敛度淡入 */
  drift: number;
  scale: number;
}

export interface EntranceOptions {
  distance?: number;
  axis?: 'x' | 'y';
  scale?: number;
  opacity?: number;
  periodFrames?: number;
  amplitude?: number;
  phase?: number;
  recipe?: string;
  /** 收敛起始点（场景占比）与收敛帧数；缺省取配方的值，旧实现同样允许覆盖 */
  at?: number;
  frames?: number;
}

/**
 * 入场配方的实现：弹性曲线 + 收敛 + 常驻微动，算完交给组件去写属性。
 *
 * HTML 与 SVG 只有「最后怎么写」不同，因此参数解析只在这里写一次——
 * 两处各写一遍必然会慢慢走偏（曾经 SVG 一侧就漏掉了自己的呼吸周期）。
 */
export function enterRecipe(
  state: MotionState,
  name: 'surface' | 'figure',
  seconds: number,
  options: EntranceOptions = {},
): EntranceMotion {
  const base = recipe(options.recipe || name);
  const from = spring(seconds, {
    response: base.springResponse,
    dampingFraction: base.springDampingFraction,
  });
  const pin = settleWith(state, base, options);
  return {
    from,
    axis: options.axis || 'y',
    shift: (1 - from) * (options.distance === undefined ? base.distance : options.distance),
    drift:
      breath(state.localFrame, {
        periodFrames:
          options.periodFrames === undefined ? base.periodFrames : options.periodFrames,
        amplitude: options.amplitude === undefined ? base.amplitude : options.amplitude,
        phase: options.phase ?? 0,
      }) * pin,
    scale: options.scale === undefined ? base.scale : options.scale,
  };
}

/** 把入场描述写成 CSS 变换串（与旧运行时逐字符相同，便于抽帧对照）。 */
export function entranceTransform(motion: EntranceMotion): string {
  const x = motion.axis === 'x' ? motion.shift : 0;
  const y = (motion.axis === 'y' ? motion.shift : 0) + motion.drift;
  const scale = range(motion.from, motion.scale, 1, { clamp: false });
  return `translate3d(${x.toFixed(2)}px,${y.toFixed(2)}px,0) scale(${scale.toFixed(4)})`;
}

/** 入场当帧的不透明度。 */
export function entranceOpacity(motion: EntranceMotion, opacity = 1): number {
  return clamp(motion.from, 0, 1) * opacity;
}

/**
 * 逐字揭示：中文长句按帧号逐字点亮，比整句淡入更有「被读出来」的感觉。
 *
 * 旧实现每帧改写各字节点的 `style.opacity`；这里返回**每一字的不透明度**，
 * 由组件渲染。逐字节点结构只在文案变化时重建这件事交给 React 的 key，
 * 而「同一帧永远得到同一画面」由此变成纯函数的性质。
 *
 * 两种用法（二选一）：
 *   revealCharOpacities(text, p);                                   // 按整体进度均分
 *   revealCharOpacities(text, 0, { frame: f, staggerFrames: 3 });   // 按帧号逐字
 */
export function revealCharOpacities(
  text: string,
  p: number,
  options: {
    staggerFrames?: number;
    frame?: number;
    startFrame?: number;
    tailFade?: number;
  } = {},
): number[] {
  const chars = Array.from(text ?? '');
  if (!chars.length) {
    return [];
  }

  if (typeof options.staggerFrames === 'number' && typeof options.frame === 'number') {
    const step = Math.max(options.staggerFrames, 1);
    const base = options.startFrame ?? 0;
    return chars.map((_char, index) =>
      clamp((options.frame! - base - index * step) / step, 0, 1),
    );
  }

  const tailFade = options.tailFade === undefined ? 0.35 : options.tailFade;
  const span = chars.length > 1 ? (1 + tailFade) / chars.length : 1;
  const last = Math.max(1 - span, 0);
  return chars.map((_char, index) => {
    const start = chars.length > 1 ? (index / (chars.length - 1)) * last : 0;
    return clamp((p - start) / span, 0, 1);
  });
}

/** 一次描边绘制在某一进度下的属性。 */
export interface PathDrawStyle {
  strokeDasharray: string;
  strokeDashoffset: string;
  opacity: string;
}

/**
 * 路径描边：进度 0 时完全没画出来，1 时整条画完。
 *
 * `length` 由调用方给出（实测 `getTotalLength()`，缺省用声明的
 * `data-a2v-length`）：旧实现把长度写回 DOM 属性再读回来，
 * 那是隐藏状态；在 React 里长度应当是量出来的一个值。
 */
export function drawPathStyle(p: number, length: number): PathDrawStyle {
  const x = clamp(p, 0, 1);
  const total = Number.isFinite(length) && length > 0 ? length : 1;
  return {
    strokeDasharray: String(total),
    strokeDashoffset: String(total * (1 - x)),
    opacity: String(x),
  };
}

/** 配方表：只读快照，供文档、调试与对照测试使用。 */
export function motionRecipes(): Record<string, MotionRecipe> {
  return {
    surface: { ...RECIPES.surface },
    figure: { ...RECIPES.figure },
  };
}

/** 弹性预设表：同上。 */
export function motionSprings(): Record<string, { response: number; dampingFraction: number }> {
  const out: Record<string, { response: number; dampingFraction: number }> = {};
  for (const [name, value] of Object.entries(SPRINGS)) {
    out[name] = { ...value };
  }
  return out;
}
