/**
 * 画面组件的 React 侧运行时：一个场景的状态、组件能用的接口，以及几条共用手法。
 *
 * 与旧运行时的关系：**数学与配方全部来自 `motion.ts`**（那是逐值对照过的移植），
 * 这里只做三件事——把「每帧算一次再写 DOM」翻译成「每帧算出样式交给 React」、
 * 把旧实现里散落的 DOM 工具收进一处、把「组件能碰什么」收窄成一份接口。
 *
 * 三条不许破的约束：
 *
 * 1. **画面只由帧号推导**。这里没有任何计时器、随机数或 CSS 动画：
 *    所有函数的输入都是 `localFrame` 与常量。`useFit` 会量一次文字宽度，
 *    量的结果只与字体和容器宽度有关，与第几帧无关。
 * 2. **锚点名字与旧页面一致**（`data-a2v-fit`、`data-el`、`data-a2v-figure`、
 *    `data-fig-kind`…）。改名不会报错，只会让闸门**静默跳过**。
 * 3. **未启用预设时不取档**。取档会改变排版结果，无条件生效就会改到既有作品；
 *    因此 `useFit` 内部走 `fitForPreset`，没有预设时直接返回空。
 */
import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from 'react';

import type { Scene } from '@/schema/storyboard';

import {
  clamp,
  drawPathStyle,
  enterRecipe,
  entranceOpacity,
  entranceTransform,
  lerp,
  motionBeat,
  progress,
  range,
  since,
  type EasingName,
  type EntranceOptions,
  type MotionState,
  type PathDrawStyle,
} from './motion';
import { fit, MIN_BODY_PX, type FitResult } from './typography';

/*
 * 转发动效层的纯函数。
 *
 * 组件要的是「帧号进、画面值出」，它们既能从 `fig.api`（同一份实现）拿，
 * 也能直接 import。转发而不是让组件改从 `@/runtime/motion` 取，是因为
 * 组件的所有依赖都应当来自同一处：写组件的人只需要记住一个入口，
 * 而两处入口各写一遍参数顺序，正是那种「看着一样、算出来差一点」的来源。
 */
export { clamp, drawPathStyle, lerp, motionBeat, progress, range, since, stagger } from './motion';
export type { MotionState, PathDrawStyle } from './motion';

export const SVG_NS = 'http://www.w3.org/2000/svg';

/** 时间只走四条曲线，与旧组件库同一个口径（多一档就会显得杂）。 */
export const EASE = {
  out: 'outQuint',
  soft: 'outCubic',
  symmetric: 'inOutCubic',
  linear: 'linear',
} as const satisfies Record<string, EasingName>;

/**
 * 数值滚动的最少步数。低于这个步数，滚动读不出「在滚动」，
 * 只读得出「跳了一下」——而跳的那一下显示的是一个**不是最终值**的数字。
 * 实测数字幕（value: 1，180 帧）：第 15–23 帧会以 350px 显示「0」，第 24 帧跳成「1」，
 * 而那一幕讲的正是一「只保留 1 个」。不足 10 步就直接显示最终值。
 */
export const ROLL_MIN = 10;

/** 幕角标的编号补零：`01 / 08`。 */
export function pad(value: number): string {
  return (value < 10 ? '0' : '') + value;
}

/** 组件声明的规格：kind、标注、几何参数、节奏与示意标记。 */
export interface FigureSpec {
  kind: string;
  labels: Record<string, string>;
  params: Record<string, unknown>;
  motion: string;
  /**
   * 示意标记（`figure.schematic`）：这组数值没有来源，画面上要出现「示意」标。
   * 目前由图表组件消费（任务 7.5）；其它组件声明了它但不会自动画标，
   * 校验器会在文案里也没有「示意」二字时给出提示。
   */
  schematic: boolean;
}

export interface FigureApi {
  clamp(value: number, min: number, max: number): number;
  lerp(from: number, to: number, t: number): number;
  progress(
    frame: number,
    startFrame: number,
    durationFrames: number,
    easing?: EasingName,
  ): number;
  since(frame: number, startFrame?: number): number;
  range(t: number, from: number, to: number, options?: { clamp?: boolean }): number;
  drawPath(p: number, length: number): PathDrawStyle;
}

export interface FigureRuntime {
  scene: Scene;
  sceneIndex: number;
  sceneCount: number;
  data: Record<string, unknown>;
  spec: FigureSpec;
  fps: number;
  preset: string | undefined;
  /**
   * 这一幕此刻是否在画面上。
   *
   * 未到的那几幕仍然挂载着（旧页面也是：一幕一个 `<section>`，靠 `display: none`
   * 切换），而 `display: none` 的元素**量出来全是 0**。取档依赖实测宽度，
   * 因此必须在「这一幕真的可见」之后才量——否则量到 0，取档返回 null，
   * 这一幕就按样式表的默认字号渲染，而溢出闸门也拿不到任何结论。
   */
  active: boolean;
  /** 动效原语的输入：幕内帧号、幕长与该幕节奏 */
  state: MotionState;
  api: FigureApi;
}

const FigureContext = createContext<FigureRuntime | null>(null);

export const FigureProvider = FigureContext.Provider;

export function useFigure(): FigureRuntime {
  const runtime = useContext(FigureContext);
  if (!runtime) {
    throw new Error('组件必须在 FigureProvider 内渲染：它需要幕内帧号与分镜数据');
  }
  return runtime;
}

/** 组装组件能用的接口。fps 由分镜给出，组件不许自己拿帧号除以写死的帧率。 */
export function createFigureApi(fps: number): FigureApi {
  const rate = fps > 0 ? fps : 30;
  return {
    clamp,
    lerp,
    progress,
    since: (frame, startFrame = 0) => since(frame, startFrame, rate),
    range,
    drawPath: drawPathStyle,
  };
}

/** 场景内的比例点换算成帧号，并按该幕节奏缩放。 */
export function beat(runtime: FigureRuntime, fraction: number): number {
  return motionBeat(runtime.state, fraction);
}

/**
 * 场景里的第 `fraction` 个比例点距现在过去了多少秒。
 * 组件里的写法固定为 `since(fig, 0.1)`，含义是「从这一幕 10% 处起算」。
 */
export function sinceBeat(runtime: FigureRuntime, fraction: number): number {
  return runtime.api.since(runtime.state.localFrame, beat(runtime, fraction));
}

/**
 * HTML 元素的入场样式（缩放 + 位移 + 常驻微动 + 不透明度）。
 *
 * `seconds` 是**距入场起点的秒数**（来自 `sinceBeat`），不是 0..1 的进度：
 * 弹簧本身就是曲线，喂给它一条已经缓动过的进度，它的自然周期就失去了意义。
 */
export function enterStyle(
  runtime: FigureRuntime,
  seconds: number,
  options: EntranceOptions = {},
): CSSProperties {
  const motion = enterRecipe(runtime.state, 'surface', seconds, options);
  return {
    transform: entranceTransform(motion),
    opacity: String(entranceOpacity(motion, options.opacity)),
  };
}

/** SVG 分组的入场：同上，但写的是 SVG 的 `transform` 属性。 */
export function enterSvgAttrs(
  runtime: FigureRuntime,
  seconds: number,
  options: EntranceOptions = {},
): { transform: string; opacity: string } {
  const motion = enterRecipe(runtime.state, 'figure', seconds, options);
  const x = motion.axis === 'x' ? motion.shift : 0;
  const y = (motion.axis === 'y' ? motion.shift : 0) + motion.drift;
  return {
    transform: svgTransform(x, y, 0, range(motion.from, motion.scale, 1, { clamp: false })),
    opacity: String(clamp(motion.from, 0, 1)),
  };
}

/**
 * SVG 的 `transform` 属性串。
 *
 * 与旧实现逐字符一致（`translate(x.xx y.yy) rotate(r.rrrr) scale(s.ssss)`）：
 * 抽帧对照会把它算进像素差，格式不同就是白差一堆。
 */
export function svgTransform(
  tx: number,
  ty: number,
  rotate?: number,
  scale?: number,
): string {
  let value = `translate(${tx.toFixed(2)} ${ty.toFixed(2)})`;
  if (rotate) {
    value += ` rotate(${rotate.toFixed(4)})`;
  }
  if (scale !== undefined && scale !== null) {
    value += ` scale(${scale.toFixed(4)})`;
  }
  return value;
}

/** SVG 的 `opacity` 属性：钳到 0..1 再写成字符串。 */
export function svgOpacity(value: number): string {
  return String(clamp(value, 0, 1));
}

/** HTML 转义：与旧实现同一份表，强调短语是拼进标记里的，必须先转义。 */
export function escapeHtml(text: unknown): string {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * 把分镜里的重点短语包成强调样式（`<span class="key">`），只替换**第一处**出现。
 *
 * 这里返回的是 HTML 串而不是 React 节点，理由只有一个：**和旧实现逐字符相同**。
 * 旧实现是在已经拼好的串上依次做 `replace`，后一个短语可能因为前一个短语插入的
 * 标记而匹配不上（`['自', '自由']` 里「自由」就匹配不到）——换成节点拼装，
 * 这个行为会悄悄改变，强调词的位置也就跟着变了。文案来自分镜，且已转义。
 */
export function emphasize(text: unknown, phrases?: unknown, underline?: boolean): string {
  let html = escapeHtml(text);
  const list = Array.isArray(phrases) ? phrases : [];
  for (const phrase of list) {
    const safe = escapeHtml(phrase);
    if (safe && html.indexOf(safe) !== -1) {
      html = html.replace(
        safe,
        `<span class="key">${safe}${underline ? '<span class="key-underline"></span>' : ''}</span>`,
      );
    }
  }
  return html;
}

/** 强调串的渲染属性。文案与标记都在 `emphasize` 里定好，这里只负责挂上去。 */
export function emphasisProps(html: string): { dangerouslySetInnerHTML: { __html: string } } {
  return { dangerouslySetInnerHTML: { __html: html } };
}

/** 非预设下光晕的默认模糊半径（px）与浓度——旧实现 `emphasizeKey` 的缺省值。 */
export const GLOW_BLUR_PX = 26;
export const GLOW_ALPHA = 0.22;

export interface EmphasisOptions {
  /** 是否在强调片段里放一个下划线节点 */
  underline?: boolean;
  /**
   * 强调进度 0..1，驱动下划线与光晕。
   *
   * 不传时**不写任何行内样式**：旧实现在没有强调节点时根本不会调 `emphasizeKey`，
   * 下划线与光晕就停在样式表的初值上。传了才会长出来。
   */
  progress?: number;
  /** 设计语言预设是否生效：决定光晕写在哪一层 */
  preset?: boolean;
  /** 非预设下光晕模糊半径的上限 */
  glowPx?: number;
  /** 非预设下光晕浓度的上限 */
  glowAlpha?: number;
  /** `api.range`：把 0..1 映到模糊半径与浓度上 */
  range?: (value: number, from: number, to: number) => number;
  /**
   * 额外写到**第一个强调片段**上的行内自定义属性，如 `--a2v-emphasis-mix`。
   *
   * 必须写在片段自己身上，不能写在祖先元素上：样式表里的 `.key` 规则自己声明了
   * `--a2v-emphasis-mix: 0`，元素自身的声明会盖掉继承来的值。旧实现也是
   * `key.style.setProperty(...)`（`figures.js` 第 501–504 行），落在同一个位置。
   */
  vars?: Record<string, string>;
}

/**
 * 强调串 + 行内样式：旧实现 `emphasize`（拼标记）与 `emphasizeKey`（写行内值）的合体。
 *
 * 为什么把行内值拼进标记，而不是让组件事后去节点上写：
 *
 * 1. 下划线的长度是一个**连续量**（`transform: scaleX(p)`），样式表里没有它，
 *    必须写在节点上；而 React 里拿不到 `emphasize` 生成的那个节点，
 *    除非组件去 `querySelector`——那正是这次迁移要消灭的手法。
 * 2. 预设下光晕只写自定义属性 `--a2v-emphasis-glow`（模糊与浓度由设计语言层给），
 *    非预设下才写行内 `text-shadow`。行内 `text-shadow` 优先级最高，写错一层
 *    就会把设计语言层整个盖掉。
 *
 * 逐字保留了旧实现的两个细节：**每个短语各替换第一处出现**（因此多个短语会
 * 产生多个强调片段），以及**行内样式只落在第一个强调片段上**（旧实现用的是
 * `querySelector('.key')`）。
 */
export function emphasisHtml(
  text: unknown,
  phrases?: unknown,
  options: EmphasisOptions = {},
): string {
  const { underline, progress, preset } = options;
  const range =
    options.range ?? ((value: number, from: number, to: number) => lerp(from, to, value));
  let style = '';
  if (progress !== undefined) {
    if (preset) {
      style = `--a2v-emphasis-glow: ${progress.toFixed(4)};`;
    } else {
      const blur = range(progress, 0, options.glowPx ?? GLOW_BLUR_PX);
      const alpha = range(progress, 0, options.glowAlpha ?? GLOW_ALPHA);
      style =
        `text-shadow: 0 0 ${blur.toFixed(1)}px ` +
        `rgba(var(--a2v-accent-rgb), ${alpha.toFixed(3)});`;
    }
  }
  for (const [name, value] of Object.entries(options.vars ?? {})) {
    style += `${name}: ${value};`;
  }
  const underlineNode = underline ? '<span class="key-underline"></span>' : '';

  let html = escapeHtml(text);
  const list = Array.isArray(phrases) ? phrases : [];
  let styled = false;
  for (const phrase of list) {
    const safe = escapeHtml(phrase);
    if (!safe || html.indexOf(safe) === -1) {
      continue;
    }
    if (style && !styled) {
      styled = true;
      const underlineStyle =
        underline && progress !== undefined
          ? `<span class="key-underline" style="transform: scaleX(${progress.toFixed(4)});"></span>`
          : underlineNode;
      html = html.replace(
        safe,
        `<span class="key" style="${style}">${safe}${underlineStyle}</span>`,
      );
    } else {
      html = html.replace(safe, `<span class="key">${safe}${underlineNode}</span>`);
    }
  }
  return html;
}

/** 空值安全的纯文本：分镜没写就留空，而不是显示 `undefined`。 */
export function plainText(value: unknown): string {
  return value === null || value === undefined ? '' : String(value);
}

export interface FitOptions {
  /** 该元素的取档上限（`data-a2v-fit` 的值） */
  level?: string;
  /** 字号下限，默认正文下限 */
  minPx?: number;
  /** 参与取档的文本；变化时重算 */
  text: string;
  /**
   * 是否让字阶接管行高。
   *
   * 默认**不接管**（与旧 `applyFit` 一致）：行高是组件的设计值，字号一变它自己
   * 就会按比例缩放；把字阶的行高写进内联样式等于把「双真源」从字号搬到行高上。
   */
  leading?: boolean;
  /** 是否让字阶接管字距；默认不接管，理由同上（各元素的字距并不相同）。 */
  tracking?: boolean;
}

export interface FitBinding {
  /**
   * 挂到元素上的 ref。
   *
   * 类型是「接收任意 Element 的回调」而不是 `RefObject<HTMLDivElement>`：
   * 同一个 hook 要能挂在 HTML 与 SVG 元素上（构图里两种都有），
   * 而调用方不该为了取档去写一遍标签名。
   */
  ref: (element: Element | null) => void;
  /** 取档结果；未启用预设或还没量到时为 null，此时元素按样式表的字号渲染 */
  result: FitResult | null;
  /** 取档算出来的行内样式（字号、行高、字距） */
  style: CSSProperties;
  /** 断行后的行；未取档时为 null，由组件按原文渲染 */
  lines: string[] | null;
}

/**
 * 按实测宽度取档（预设生效时才做）。
 *
 * 三件事必须一起成立，否则「不取档」会变成「取错档」：
 *
 * - **可用宽度取容器**（`.a2v-safe`）的客户区宽度，而不是元素自己的宽度：
 *   收缩适应的元素宽度就等于它那行文字，永远除得尽，那是循环论证；
 * - **测量用 canvas**，字体取元素的计算样式：SVG 里的 `getComputedTextLength`
 *   在 HTML 元素上不存在，而构图里的文字两种都有；
 * - **只在输入变化时重算**：量一次的结果与帧号无关，逐帧重算只会拖慢渲染，
 *   还会让同一帧的结果依赖上一帧的布局（那就不再是帧驱动的了）。
 */
export function useFit(options: FitOptions): FitBinding {
  const runtime = useFigure();
  const elementRef = useRef<Element | null>(null);
  const [attached, setAttached] = useState(0);
  const [measured, setMeasured] = useState<{ width: number; font: FontKey } | null>(null);
  const [result, setResult] = useState<FitResult | null>(null);
  const fontsReady = useFontsReady();
  const level = options.level;
  const minPx = options.minPx;

  const attach = useCallback((element: Element | null) => {
    elementRef.current = element;
    // 元素挂上（或换成另一个）时重量一次：回调 ref 是唯一能确定「已经挂上了」的时机
    setAttached((count) => count + 1);
  }, []);

  const measure = useCallback(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }
    // 可用宽度由容器决定：元素自身可能是收缩适应的，量它等于问文字自己有多宽
    const host = element.closest('.a2v-safe') ?? element.parentElement;
    const width = host ? host.clientWidth : 0;
    const style = window.getComputedStyle(element);
    setMeasured((previous) => {
      const next = { width, font: fontKeyOf(style) };
      return previous && previous.width === next.width && previous.font.key === next.font.key
        ? previous
        : next;
    });
  }, []);

  /*
   * 只在「量的东西」可能变了的时候重量：挂在文案、档位、下限、字体就绪、容器尺寸上，
   * 而不是每帧都量。逐帧读 `getComputedStyle` 会让同一帧的结果依赖上一帧的布局，
   * 那就不再是帧驱动的了——而且 30fps 下每个文字元素一次样式重算是白扔的开销。
   *
   * `runtime.active` 是这套依赖里唯一与时间有关的一项：这一幕可见之前量出来是 0
   * （`display: none`），只有等它上场才有意义。它只翻转一次，因此仍然是「量一次」。
   */
  useLayoutEffect(() => {
    measure();
  }, [measure, attached, options.text, level, minPx, fontsReady, runtime.preset, runtime.active]);

  const computed = useMemo(() => {
    // 未启用预设不取档：取档会改变排版结果，无条件生效就会改到既有作品
    if (!runtime.preset || !measured || measured.width <= 0) {
      return null;
    }
    const context = measureCanvas();
    if (!context) {
      return null;
    }
    context.font = measured.font.shorthand;
    const size = measured.font.sizePx || 40;
    return fit({
      text: options.text,
      availableWidth: measured.width,
      // canvas 的宽度是像素，引擎要的是 em：除回字号，字体大小的影响由引擎自己乘
      measure: (text: string) => context.measureText(text).width / size,
      maxLevel: level,
      minPx: minPx === undefined ? MIN_BODY_PX : minPx,
    });
  }, [runtime.preset, measured, options.text, level, minPx]);

  useLayoutEffect(() => {
    setResult((previous) => (sameFit(previous, computed) ? previous : computed));
  }, [computed]);

  const style = useMemo<CSSProperties>(() => {
    if (!result) {
      return {};
    }
    /*
     * 默认只写字号（与旧 `applyFit` 一致）：行高与字距是组件的设计值，
     * 由样式表给；只有调用方显式要求时才让字阶接管。
     */
    const out: CSSProperties = { fontSize: `${result.fontSize}px` };
    if (options.leading === true) {
      out.lineHeight = String(result.lineHeight);
    }
    if (options.tracking === true) {
      out.letterSpacing = `${result.letterSpacing}em`;
    }
    /*
     * 均衡断行必须配 `white-space: pre-line`：`lines` 里的换行符在默认的
     * `white-space: normal` 下会被折叠成一个空格，两行会挤成一行。
     * 旧实现是在 `reflow` 成功之后才写这一条（`typography.js` 第 563 行），
     * 判据同样是「断行结果里真的有换行」。
     */
    if (result.lines.join('\n').includes('\n')) {
      out.whiteSpace = 'pre-line';
    }
    return out;
  }, [result, options.leading, options.tracking]);

  /*
   * 把取档结论写回元素上的 `data-a2v-fit-*`。
   *
   * 这几个属性是**闸门的输入**：体检脚本用 `[data-a2v-fit-fits="false"]`
   * 收集「缩到正文下限仍放不下」的文本块（`inspect.py` 第 549 行）。
   * 不写它们，溢出闸门不会失败——它会**一个节点都找不到**，然后安静地通过。
   * 这类「检查空转」比检查失败危险得多，因此这里逐条对齐旧实现（第 567–572 行）。
   *
   * 用命令式 `setAttribute` 而不是 JSX 属性：这几个值来自测量结果，
   * 元素本身是组件渲染的，把测量结果塞进 JSX 会让每次量测都触发一次重渲染。
   */
  useLayoutEffect(() => {
    const element = elementRef.current;
    if (!element) {
      return;
    }
    if (!result) {
      // 未启用预设（或还没量到）时不写任何结论：旧路径同样只在取档后写
      for (const name of FIT_DATA_ATTRIBUTES) {
        element.removeAttribute(name);
      }
      return;
    }
    element.setAttribute('data-a2v-fit-level', result.level);
    element.setAttribute('data-a2v-fit-measured', result.measured ? 'true' : 'false');
    element.setAttribute(
      'data-a2v-fit-balanced',
      result.lines.join('\n').includes('\n') ? 'true' : 'false',
    );
    element.setAttribute('data-a2v-fit-fits', result.fits ? 'true' : 'false');
  }, [result, attached]);

  return { ref: attach, result, style, lines: result ? result.lines : null };
}

/** 取档结论写在元素上的属性名（闸门读它们，改名会让检查静默空转）。 */
export const FIT_DATA_ATTRIBUTES = [
  'data-a2v-fit-level',
  'data-a2v-fit-measured',
  'data-a2v-fit-balanced',
  'data-a2v-fit-fits',
] as const;

/** 元素的计算字体：键用于判断要不要重量，shorthand 用于 canvas。 */
interface FontKey {
  key: string;
  shorthand: string;
  sizePx: number;
}

function fontKeyOf(style: CSSStyleDeclaration): FontKey {
  const sizePx = parseFloat(style.fontSize) || 0;
  const shorthand = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
  return { key: shorthand, shorthand, sizePx };
}

/**
 * 字体是否已经加载完成。
 *
 * 「字体还没就绪就量宽度」得到一个**看起来很正常的错值**：字号档位会差一档，
 * 而画面、校验、渲染全部照常通过。旧页面在首次 seek 之前 await 过
 * `document.fonts.ready`，这里在同一件事上加一个状态：字体就绪后重量一次。
 */
export function useFontsReady(): boolean {
  const [ready, setReady] = useState(
    () => typeof document === 'undefined' || !document.fonts || document.fonts.status === 'loaded',
  );
  useLayoutEffect(() => {
    if (ready || typeof document === 'undefined' || !document.fonts) {
      return;
    }
    let alive = true;
    document.fonts.ready
      .then(() => {
        if (alive) {
          setReady(true);
        }
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [ready]);
  return ready;
}

/** 只在结果不同时更新 state：逐帧重建对象会让 React 每帧都重渲染整棵子树。 */
function sameFit(a: FitResult | null, b: FitResult | null): boolean {
  if (a === b) {
    return true;
  }
  if (!a || !b) {
    return false;
  }
  return (
    a.level === b.level &&
    a.fontSize === b.fontSize &&
    a.fits === b.fits &&
    a.lines.join('\n') === b.lines.join('\n')
  );
}

/** 复用一个 canvas 上下文测宽：每次新建的代价远高于测一次文字。 */
let measureContext: CanvasRenderingContext2D | null | undefined;
function measureCanvas(): CanvasRenderingContext2D | null {
  if (measureContext === undefined) {
    measureContext =
      typeof document === 'undefined' ? null : document.createElement('canvas').getContext('2d');
  }
  return measureContext;
}

/**
 * 把文本切成「普通片段 / 强调片段」，强调片段是 `phrases` 中**第一处**命中的部分。
 *
 * 与旧实现同一条规则：只认第一个在文本里找得到的短语，找不到就整段普通。
 * 换一条规则（例如所有短语都点亮）会改变强调词的数量，那是画面变化。
 */
export function splitEmphasis(
  text: string,
  phrases?: readonly string[],
): Array<{ text: string; key: boolean }> {
  for (const phrase of phrases ?? []) {
    if (typeof phrase !== 'string' || !phrase) {
      continue;
    }
    const at = text.indexOf(phrase);
    if (at === -1) {
      continue;
    }
    return [
      { text: text.slice(0, at), key: false },
      { text: phrase, key: true },
      { text: text.slice(at + phrase.length), key: false },
    ].filter((unit) => unit.text !== '');
  }
  return [{ text, key: false }];
}

/**
 * 逐字揭示的节点树：每个字一个节点，逐帧只改不透明度。
 *
 * 强调片段整体比正文晚 6 帧出现（读起来有轻重），换行符占位但不可见。
 * 与旧实现一致：**帧号是唯一输入**，因此同一帧永远得到同一棵节点树。
 */
export interface RevealChar {
  char: string;
  opacity: number;
  isBreak: boolean;
}

export interface RevealUnit {
  key: boolean;
  chars: RevealChar[];
}

export function revealUnits(
  text: string,
  phrases: readonly string[] | undefined,
  options: { frame: number; startFrame?: number; staggerFrames?: number },
): RevealUnit[] {
  const start = options.startFrame ?? 0;
  const stagger = Math.max(options.staggerFrames ?? 2, 1);
  const frame = options.frame;
  let index = 0;
  return splitEmphasis(text, phrases).map((unit) => ({
    key: unit.key,
    chars: Array.from(unit.text).map((char) => {
      if (char === '\n') {
        return { char, opacity: 1, isBreak: true };
      }
      const charStart = start + index * stagger + (unit.key ? REVEAL_KEY_DELAY_FRAMES : 0);
      index += 1;
      return { char, opacity: clamp((frame - charStart) / stagger, 0, 1), isBreak: false };
    }),
  }));
}

/** 强调片段比正文晚出现的帧数。 */
export const REVEAL_KEY_DELAY_FRAMES = 6;

/**
 * 量文本宽度的量尺（像素），字体取参考元素的计算样式。
 *
 * 为什么用 canvas 而不是 `getComputedTextLength()` / `getBBox()`：
 * 后两者要求元素已经在文档里、且会触发一次同步布局，逐帧调用就是逐帧重排；
 * 而 canvas 的 `measureText` 只依赖字体，结果与第几帧无关，可以缓存。
 * 旧实现里有几处「先写死容器尺寸再塞文字」的缺陷，判据就是实测宽度，
 * 因此量尺必须能用在**还没画出节点**的时候。
 *
 * 字体没就绪时量到的是回退字体的宽度，因此调用方应把 `fontsReady` 纳入依赖，
 * 就绪后重量一次（`useFit` 就是这么做的）。
 */
export function useTextMeasure(): (element: Element | null, text: string) => number {
  const fontsReady = useFontsReady();
  return useCallback(
    (element: Element | null, text: string) => {
      const context = measureCanvas();
      if (!element || !context) {
        return 0;
      }
      const font = fontKeyOf(window.getComputedStyle(element));
      context.font = font.shorthand;
      void fontsReady;
      return context.measureText(text).width;
    },
    [fontsReady],
  );
}
