/**
 * 飞轮（`loop`）：小球沿圆轨道一格一格前进，每转一格「准备度」就抬高一截。
 *
 * 逐行对应旧组件库 `assets/figures.js`：
 *
 * - `LOOP` 常量与 `loopPoint`（第 1048–1082 行）、`loopGeometry`（第 1084–1095 行）；
 * - `updateLoop`（第 1103–1289 行）；
 * - `MARKUP_LOOP`（第 1292–1310 行）；
 * - 它依赖的三个几何工具：`fitLabelToCircle`（213–267）、`paintLabelLines`（279–293）、
 *   `balanceChars`（184–192）。
 *
 * ## 为什么半径必须由实测文字宽度决定（这段历史不能省）
 *
 * 飞轮节点原先**写死半径 76px**（直径 152px），而 `.loop-node-text` 的字号来自
 * `--a2v-ink-value`（预设下 = `--a2v-size-body` = 40px，旧注释里那个 44px 是过期字面量），
 * 四个汉字带字距约 160–183px——**比直径还宽**，文字必然穿出圆。
 * 而观感闸门 K7 只比安全区、且显式排除 SVG 宿主文本，所以没有任何检查会发现它：
 * 「先写死容器、再放文字」这个顺序本身就是缺陷。K8 把容器内溢出变成硬判定之后，
 * 反例实测报「「打开选项」穿出 .loop-node-disc（圆周）16.0px」。
 *
 * 因此这里保持同一个性质：**圆盘半径只能由实测宽度反推**，不许回到写死的 76。
 * 判据是「矩形内接于圆」：宽 w、高 h 的文字块居中放进半径 r 的圆，
 * 需要 `r ≥ sqrt((w/2)² + (h/2)²)`；逐行数试算，取所需半径最小的一种装法
 * （所需半径相同则取行数更少的），再与最小半径取大。
 *
 * ## 量宽度换了一种做法（这是与旧实现唯一的机制性差异）
 *
 * 旧实现把文字先挂进文档，再用 `textEl.getComputedTextLength()` 实测。新工程里
 * 那条路走不通：它要求节点已在文档里、会触发一次同步布局，而且逐帧调用就不是
 * 帧无关的了。这里改用运行时给的 canvas 量尺（`useTextMeasure`）：把每个节点的
 * 文字节点挂一个 ref，`useLayoutEffect` 在挂载后量一次，算出半径与断行写进 state。
 *
 * 两条由此而来的性质：
 *
 * - **首帧还没有量到结果**，此时按老实现的降级路径渲染（单行原文 + 最小半径），
 *   量到之后再切过去；降级不是抛错，画面必须仍然成立。
 * - **同一份文案在同一容器宽度下永远得到同一个半径**：结果只依赖文案、字体与
 *   令牌取值，不含帧号，也不含上一帧的布局——逐帧重算只会拖慢渲染，还会把
 *   「帧驱动」换成「布局驱动」。
 *
 * ## 与旧实现有意不同的两处（详见交付说明）
 *
 * 1. 旧实现的 `presetActive()` 分叉（未启用预设时冻结为 3 个停位、半径写死 76）
 *    **没有搬过来**：步长一律 `360 / 节点数`，半径一律实测。原因是这条任务书
 *    明确要求「步长必须是 360/节点数」「半径不许写死」，而 `examples/why-effort-fails`
 *    那一幕（4 个节点、分镜里没有 preset）正是那个「index 3 落回 360°、两个圆盘
 *    画在同一位置」的历史缺陷现场。
 * 2. 弧线长度不再用 `path.getTotalLength()`（同上：要求已排版、且是隐藏状态），
 *    改为解析式：`M x y A R R 0 0 1 x y` 画的就是半径 R、圆心角 `360/停位数`
 *    的圆弧，长度 = `R × 圆心角(弧度)`，与 `getTotalLength()` 相等。
 */
import {
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FC,
} from 'react';

import { SPRINGS, spring } from '@/runtime/motion';
import {
  EASE,
  beat,
  plainText,
  svgOpacity,
  svgTransform,
  useFigure,
  useFit,
  useFontsReady,
  useTextMeasure,
} from '@/runtime/figures';

/* ---------------- 常量：逐值照搬 assets/figures.js 的 LOOP（1048–1059） ---------------- */

/** 环心、半径与节点圆的最小半径；`NODE_R` 曾是实际半径，现在只是下限。 */
export const LOOP = {
  CX: 444,
  CY: 290,
  R: 200,
  NODE_R: 76,
  /** 未启用预设时的冻结停位数：新实现不再使用（见文件头第 1 条）。 */
  FROZEN_STOPS: 3,
  /** 小球要转满几圈。条满 = 转满 LAPS 圈，所以格数 = 停位数 × LAPS。 */
  LAPS: 2,
} as const;

/**
 * 节点圆的最小半径：令牌 `--fig-node-r-min`（`tokens.css` 第 324 行，76px）。
 *
 * 老实现用 `tokenPx(text, '--fig-node-r-min', LOOP.NODE_R)` 读它。新工程不许用
 * `getComputedStyle` 读令牌像素值，而半径又必须落成 SVG 属性、无法用 CSS 表达，
 * 所以这里写**兜底值**：令牌名与取值都注明在此。
 */
export const MIN_NODE_RADIUS = LOOP.NODE_R;

/**
 * 表面内边距：令牌 `--fig-surface-pad`（= `--a2v-space-3`，16px）。
 * 同上：参与几何计算、无法用 CSS 表达，取老实现的兜底值 `tokenPx(..., 16)`。
 */
export const SURFACE_PAD = 16;

/**
 * 节点文字字号：令牌 `--a2v-ink-value`（预设下 = `--a2v-size-body` = 40px，
 * 未启用预设时样式表兜底 48px）。老实现读的是元素的计算字号。
 *
 * 这里只需要它来算行高，**字宽由量尺实测**，量出来的宽度自然反映真实字号；
 * 只有行高（`行数 × 行高`）参与「矩形内接于圆」的判据，所以它必须有确切取值。
 * 取 40px 而不是老注释里的 44px：预设下 `--a2v-ink-value` → `--a2v-size-body`
 * 就是 40px，老代码当下读到的也是 40（旧注释 44px 是字阶换成 40px 之前的残留）。
 */
export const NODE_FONT_PX = 40;

/** 行高倍数：老预设层 `[data-a2v-preset="keynote"] .loop-node-text { line-height: 1.15 }`。 */
export const NODE_LINE_HEIGHT = 1.15;

/**
 * 参与几何计算的行高（px）：`1.15 × 40px = 46px`。
 *
 * 浏览器把 `line-height: 1.15` 解析成 px 之后交给老代码的是 `"46px"`，
 * 所以这里写 46 而不是 `40 * 1.15`（后者是 45.99999999999999）。
 */
export const NODE_LINE_PX = 46;

/** 一个节点的文字装法：断行结果、算出来的圆盘半径、是否量到了宽度。 */
export interface LoopLabelLayout {
  lines: string[];
  radius: number;
  lineHeight: number;
  /**
   * 是否量到了宽度。false 表示走了降级路径：**单行原文 + 最小半径**，
   * 由调用方按原样绘制（老实现的 `measured: false` 是同一个意思）。
   */
  measured: boolean;
}

/** `fitLabelToCircle` 的几何输入。 */
export interface LoopFitOptions {
  /** 令牌 `--fig-node-r-min`（兜底 76） */
  minRadius: number;
  /** 令牌 `--fig-surface-pad`（兜底 16） */
  pad: number;
  /** 行高（px），见 `NODE_LINE_PX` */
  lineHeight: number;
}

/** 把 chars 均衡切成 count 行：行数固定，各行的字数差不超过 1。 */
export function balanceChars(chars: readonly string[], count: number): string[] {
  const lines: string[] = [];
  const size = Math.ceil(chars.length / count);
  for (let i = 0; i < chars.length; i += size) {
    lines.push(chars.slice(i, i + size).join(''));
  }
  return lines;
}

/**
 * 把一段标签装进圆形节点：**几何由内容测量结果决定**，而不是先写死半径再塞字。
 *
 * 与老实现（`fitLabelToCircle`，213–267 行）逐行等价，只有两处改法：
 *
 * - 量宽度改成收一个 `widthOf(line)`：老实现是「把候选行写进 textContent，
 *   再读 getComputedTextLength」——那是在改它并不拥有的 DOM。React 侧文字内容
 *   由组件渲染，量尺只回答「这一串在什么字体下有多宽」，两件事分开。
 *   量不到（返回 0 / null / NaN）时的行为与老实现完全一致：走降级。
 * - 老实现里那个只写不读的 `widest` 变量没有搬（死代码，写出来会让后来人以为
 *   它参与判据）。
 *
 * 注意：文件头的「逐行数试算」是老注释的原话，**实际不可达**——循环末尾那句
 * `if (lines.length === 1) break;` 在 count=1 时必然成立，见下面的行内说明。
 * 这里照抄它，因为抽帧对照比的是老实现的真实输出，而不是它的注释。
 */
export function fitLabelToCircle(
  label: unknown,
  widthOf: (line: string) => number | null | undefined,
  options: LoopFitOptions,
): LoopLabelLayout {
  const text = String(label === null || label === undefined ? '' : label);
  const chars = Array.from(text);
  /** 降级：单行原文 + 最小半径，不抛错。 */
  const fallback: LoopLabelLayout = {
    lines: [text],
    radius: options.minRadius,
    lineHeight: options.lineHeight,
    measured: false,
  };
  if (!chars.length) {
    // 空文案：老实现返回空行集，调用方据此清空文字节点
    return { ...fallback, lines: [] };
  }

  let best: { lines: string[]; radius: number } | null = null;
  for (let count = 1; count <= chars.length; count += 1) {
    const lines = balanceChars(chars, count);
    let maxWidth = 0;
    for (const line of lines) {
      // 量不到（0 / null / NaN）→ maxWidth 保持 0 或变成 NaN，下面一并走降级
      maxWidth = Math.max(maxWidth, widthOf(line) ?? 0);
    }
    if (!maxWidth) {
      return fallback;
    }
    const blockH = lines.length * options.lineHeight;
    // 「矩形内接于圆」：居中放进半径 r 的圆，需要 r ≥ sqrt((w/2)² + (h/2)²)
    const needed = Math.sqrt((maxWidth / 2) ** 2 + (blockH / 2) ** 2) + options.pad;
    if (
      best === null ||
      needed < best.radius - 0.5 ||
      (Math.abs(needed - best.radius) <= 0.5 && lines.length < best.lines.length)
    ) {
      best = { lines, radius: needed };
    }
    /*
     * 照抄老实现（256–258 行）的这一句——**它让上面那段多行试算永远不可达**：
     * count=1 时 balanceChars 只切出一行，所以循环总在第一次迭代就退出，
     * 「取所需半径最小的装法」实际只比较过单行这一种。因此断行结果恒为单行
     * （这是老实现的真实行为，不是新 Bug）。不许顺手删掉它：删掉之后四个汉字
     * 会变成两行、圆盘半径从按单行算的 110.93px 缩到 88.11px，抽帧对照会差一片。
     */
    if (lines.length === 1) {
      break;
    }
  }
  if (best === null) {
    // 不可达：chars 非空 ⇒ count=1 那轮必然设过 best
    return fallback;
  }
  return {
    lines: best.lines,
    radius: Math.max(options.minRadius, best.radius),
    lineHeight: options.lineHeight,
    measured: true,
  };
}

/** 一行 `tspan` 的落点：`paintLabelLines`（279–293 行）的等价物。 */
export interface LoopTextLine {
  text: string;
  x: number;
  y: number;
}

/**
 * 按测量结果把标签写成单行或多行，并让整块在 (cx, cy) 上垂直居中。
 *
 * 单行时 `y = cy`（老实现同样不碰 lineHeight），多行时按行盒中心对称铺开。
 */
export function loopLabelLines(
  layout: LoopLabelLayout,
  cx: number,
  cy: number,
): LoopTextLine[] {
  const lines = layout.lines;
  return lines.map((line, index) => ({
    text: line,
    x: cx,
    y:
      lines.length > 1
        ? cy + (index - (lines.length - 1) / 2) * layout.lineHeight
        : cy,
  }));
}

/* ---------------- 环上几何：loopGeometry / loopPoint（1048–1095 行） ---------------- */

/**
 * 一圈几个停位：**节点数**（老实现的预设分支 `Math.max(nodeCount, 2)`）。
 *
 * 停位数必须与节点数一致：`loopPoint` 同时给「小球走的环」和「节点摆在哪」用，
 * 两者用不同步长时，第 4 个节点会落回 360° 与第 1 个重合——屏幕上只看得到
 * 三个圆盘，「打开选项」被完全遮住（老实现为此留了 1048–1075 行的整段说明）。
 */
export function loopStops(nodeCount: number): number {
  return Math.max(nodeCount, 2);
}

/** 停位数与格数：格数 = 停位数 × LAPS（两整圈之后条满）。 */
export function loopGeometry(nodeCount: number): { stops: number; segments: number } {
  const stops = loopStops(nodeCount);
  return { stops, segments: stops * LOOP.LAPS };
}

/** 一格的角度：`360 / 停位数`。 */
export function loopStepDegrees(stops: number): number {
  return 360 / Math.max(stops, 1);
}

/**
 * 环上的一个点。`travel` 以「一格」为单位，`stops` 是一圈有几个停位。
 *
 * `-90°` 起步 = 第一个节点在正上方，与旧实现一致。
 */
export function loopPoint(travel: number, stops: number): { x: number; y: number } {
  const angle = ((-90 + travel * loopStepDegrees(stops)) * Math.PI) / 180;
  return {
    x: LOOP.CX + LOOP.R * Math.cos(angle),
    y: LOOP.CY + LOOP.R * Math.sin(angle),
  };
}

/**
 * 一段弧的总长度：半径 R、圆心角 `360/停位数` 的圆弧，长度 = `R × 圆心角(弧度)`。
 *
 * 老实现读的是 `path.getTotalLength()`。同一段弧，解析值与浏览器实测值相等，
 * 但解析值不要求元素已排版，也不依赖上一帧的布局——见文件头第 2 条。
 */
export function loopArcLength(stops: number): number {
  return (LOOP.R * loopStepDegrees(stops) * Math.PI) / 180;
}

/** 节点 `index` → `index+1` 的那段弧的 `d`，与旧实现逐字符相同。 */
export function loopArcPath(
  from: { x: number; y: number },
  to: { x: number; y: number },
): string {
  return (
    'M' +
    from.x.toFixed(2) +
    ' ' +
    from.y.toFixed(2) +
    ' A ' +
    LOOP.R +
    ' ' +
    LOOP.R +
    ' 0 0 1 ' +
    to.x.toFixed(2) +
    ' ' +
    to.y.toFixed(2)
  );
}

/** 一个节点标签：字符串直接用；对象取 `label`，退到 `id`（老实现 1131 行）。 */
export function loopNodeLabel(node: unknown): string {
  if (typeof node === 'string') {
    return node;
  }
  if (node && typeof node === 'object') {
    const record = node as Record<string, unknown>;
    const label = record['label'];
    if (label) {
      return String(label);
    }
    const id = record['id'];
    if (id) {
      return String(id);
    }
  }
  return '';
}

/** 分镜里的 `nodes`（字符串或 `{id,label}`）→ 一串标签。 */
export function loopNodeLabels(nodes: unknown): string[] {
  return Array.isArray(nodes) ? nodes.map(loopNodeLabel) : [];
}

/** 只在结果不同时更新 state：逐帧重建数组会让整棵子树每帧都重渲染。 */
function sameLayouts(
  previous: LoopLabelLayout[] | null,
  next: LoopLabelLayout[],
): boolean {
  if (!previous || previous.length !== next.length) {
    return false;
  }
  return previous.every((layout, index) => {
    const other = next[index]!;
    return (
      layout.measured === other.measured &&
      layout.radius === other.radius &&
      layout.lineHeight === other.lineHeight &&
      layout.lines.join('\n') === other.lines.join('\n')
    );
  });
}

export const LoopFigure: FC = () => {
  const fig = useFigure();
  const { localFrame, sceneDurationFrames } = fig.state;
  const data = fig.data;

  const nodes = loopNodeLabels(data['nodes']);
  const nodeCount = nodes.length;
  // 文案的稳定签名：state 的重算只认它（数组本身每帧都是新对象）
  const labelsKey = nodes.join('\u0000');
  const geometry = loopGeometry(nodeCount);

  const titleText = plainText(data['title']);
  const title = useFit({ level: 'title', text: titleText });
  const gaugeLabel = plainText(fig.spec.labels['gauge']);

  /*
   * 实测几何：这是本组件**唯一**的跨帧状态。
   *
   * 它的输入只有文案、字体与令牌取值——没有帧号、没有上一帧的布局，
   * 所以同一份文案永远得到同一个半径；写它的时机是挂载后的 `useLayoutEffect`。
   */
  const measure = useTextMeasure();
  const fontsReady = useFontsReady();
  const textRefs = useRef<Array<SVGTextElement | null>>([]);
  const [attached, setAttached] = useState(0);
  const [layouts, setLayouts] = useState<LoopLabelLayout[] | null>(null);

  /*
   * 每个节点的文字节点一个 ref。回调本身要稳定（每次渲染都换一个新函数的话，
   * React 会不停卸载再挂载 ref，`setAttached` 就会每帧自增一次）。
   */
  const attachText = useMemo(
    () =>
      Array.from(
        { length: nodeCount },
        (_unused: unknown, index: number) => (element: SVGTextElement | null) => {
          textRefs.current[index] = element;
          setAttached((count) => count + 1);
        },
      ),
    [nodeCount],
  );

  useLayoutEffect(() => {
    const next = nodes.map((label, index) =>
      fitLabelToCircle(
        label,
        // 字体取该元素的计算样式（量尺内部做的）；元素还没挂上就量不到 → 降级
        (line) => measure(textRefs.current[index] ?? null, line),
        { minRadius: MIN_NODE_RADIUS, pad: SURFACE_PAD, lineHeight: NODE_LINE_PX },
      ),
    );
    setLayouts((previous) => (sameLayouts(previous, next) ? previous : next));
    /*
     * 只在「量的东西」可能变了的时候重量：文案、字体就绪、预设（决定令牌字号）、
     * 节点数、ref 挂载。`nodes` 不进依赖——它每帧都是新数组，进去就等于逐帧重量。
     */
  }, [measure, fontsReady, fig.preset, labelsKey, nodeCount, attached]);

  /* ---- 逐帧几何：逐行照搬 updateLoop（1103–1289 行） ---- */

  // 轨道先淡入
  const trackOpacity = fig.api.progress(
    localFrame,
    beat(fig, 0.06),
    beat(fig, 0.08),
    EASE.out,
  );

  /* 小球：每格若干帧，走满 geometry.segments 格正好把「准备度」填满。
   * 格数 = 停位数 × LAPS，所以 4 个节点是 8 格（两整圈、回到起点）。 */
  const travelStart = beat(fig, 0.2);
  const segFrames = Math.max(
    (sceneDurationFrames - travelStart) / geometry.segments,
    1,
  );
  const travel = fig.api.clamp(
    (localFrame - travelStart) / segFrames,
    0,
    geometry.segments,
  );
  const point = loopPoint(travel, geometry.stops);
  const arrived = Math.floor(travel);
  const frac = travel - arrived;

  /* 焦点是**连续**的：小球一路走，焦点一路交。
   * 交接拆成两段，任何一帧仍然只有一个 focus 元素：
   *   frac ∈ [0, 0.5)  旧节点是 focus，mix 从 1 降到 0（淡出）
   *   frac ∈ [0.5, 1)  新节点是 focus，mix 从 0 升到 1（淡入）
   * 换手正好发生在 mix = 0 的那一帧，两侧外观都等于 rest，所以没有缝。 */
  const nodeStart = beat(fig, 0.12);
  const handingOver = frac < 0.5;
  const focusIndex = nodeCount
    ? handingOver
      ? arrived % nodeCount
      : (arrived + 1) % nodeCount
    : -1;
  const focusMix = fig.api.clamp(handingOver ? 1 - frac * 2 : frac * 2 - 1, 0, 1);

  const tokenIn = fig.api.progress(localFrame, travelStart - 6, 18, EASE.out);
  const arcLength = loopArcLength(geometry.stops);
  const gaugeWidth = `${(
    fig.api.clamp(travel / geometry.segments, 0, 1) * 100
  ).toFixed(2)}%`;

  return (
    <>
      <h2
        className="section-title"
        data-el="title"
        data-a2v-fit="title"
        ref={title.ref}
        style={title.style}
      >
        {titleText}
      </h2>
      {/* 飞轮：一个小球沿着「上场→暴露→反馈」转圈，每转一格准备度就抬高一截 */}
      <svg className="fig fig-loop" viewBox="0 0 888 560" aria-hidden="true">
        <defs>
          <radialGradient id="loop-halo">
            <stop
              offset="0"
              stopColor="color-mix(in srgb, var(--a2v-accent-soft-solid) 35%, transparent)"
            />
            <stop
              offset="1"
              stopColor="color-mix(in srgb, var(--a2v-accent-soft-solid) 0%, transparent)"
            />
          </radialGradient>
        </defs>
        <circle
          className="loop-track"
          data-el="track"
          cx="444"
          cy="290"
          r="200"
          style={{ opacity: String(trackOpacity) }}
        />
        <g data-el="arcs">
          {nodes.map((_label, index) => {
            const from = loopPoint(index, geometry.stops);
            const to = loopPoint(index + 1, geometry.stops);
            const draw = fig.api.drawPath(
              fig.api.clamp(travel - index, 0, 1),
              arcLength,
            );
            return (
              <path
                key={index}
                className="loop-arc"
                data-arc={String(index)}
                d={loopArcPath(from, to)}
                strokeDasharray={draw.strokeDasharray}
                strokeDashoffset={draw.strokeDashoffset}
                style={{ opacity: draw.opacity }}
              />
            );
          })}
        </g>
        <circle
          className="loop-token-halo"
          data-el="tokenHalo"
          cx={point.x.toFixed(2)}
          cy={point.y.toFixed(2)}
          r="86"
          opacity={svgOpacity(tokenIn * 0.55)}
        />
        <circle
          className="loop-token"
          data-el="token"
          cx={point.x.toFixed(2)}
          cy={point.y.toFixed(2)}
          r="20"
          opacity={svgOpacity(tokenIn)}
        />
        <g data-el="nodes">
          {nodes.map((label, index) => {
            const nodePoint = loopPoint(index, geometry.stops);
            const layout = layouts ? layouts[index] : undefined;
            // 首帧还没量到 → 走降级：单行原文 + 最小半径
            const radius = layout ? layout.radius : MIN_NODE_RADIUS;
            const lines = layout
              ? loopLabelLines(layout, nodePoint.x, nodePoint.y)
              : null;
            const isFocus = index === focusIndex;
            const nodeState = isFocus ? 'focus' : 'rest';
            const pulse = isFocus ? focusMix : 0;
            /* 节点只有一个 transform 写入点：入场位移、缩放入场与「到达时鼓一下」
             * 必须合成同一条 transform，否则后写的那条会把先写的覆盖掉。 */
            const enterP = spring(
              fig.api.since(localFrame, nodeStart + index * 8),
              SPRINGS['enter'],
            );
            const scale =
              fig.api.range(enterP, 0.94, 1, { clamp: false }) *
              (1 + pulse * 0.09);
            return (
              <g
                key={index}
                data-node={String(index)}
                transform={svgTransform(
                  nodePoint.x * (1 - scale),
                  nodePoint.y * (1 - scale) +
                    (1 - fig.api.clamp(enterP, 0, 1)) * 26,
                  0,
                  scale,
                )}
                opacity={svgOpacity(fig.api.clamp(enterP, 0, 1))}
              >
                <circle
                  className="loop-node-shadow"
                  cx={nodePoint.x}
                  cy={nodePoint.y + 12}
                  r={radius}
                />
                <circle
                  className="loop-node-disc a2v-surface"
                  data-a2v-state={nodeState}
                  cx={nodePoint.x}
                  cy={nodePoint.y}
                  r={radius}
                  /* 焦点外观靠这条连续通道淡入淡出；只在 focus 时写，
                   * 所以回到 rest 的元素不会留下会突然生效的陈旧值。 */
                  style={
                    isFocus
                      ? ({
                          '--a2v-focus-mix': focusMix.toFixed(4),
                        } as CSSProperties)
                      : undefined
                  }
                />
                <text
                  ref={attachText[index]}
                  className="loop-node-text a2v-label"
                  data-a2v-state={nodeState}
                  /* 声明这段文字装在哪个容器里：观感闸门 K8 据此判定「有没有穿出圆」。
                   * 只能由组件声明——阶梯的注写在柱子上方，同为近邻却不装在容器里，
                   * 几何上无法自动区分。 */
                  data-a2v-inside=".loop-node-disc"
                  x={nodePoint.x}
                  y={nodePoint.y}
                >
                  {lines
                    ? lines.map((line, lineIndex) => (
                        <tspan key={lineIndex} x={line.x} y={line.y}>
                          {line.text}
                        </tspan>
                      ))
                    : label}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
      <div className="gauge">
        <span className="gauge-label" data-el="gaugeLabel">
          {gaugeLabel}
        </span>
        <span className="gauge-track">
          <span
            className="gauge-fill"
            data-el="gaugeFill"
            style={{ width: gaugeWidth }}
          />
        </span>
      </div>
    </>
  );
};
