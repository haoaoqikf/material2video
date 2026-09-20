/**
 * 阶梯幕：次数累积带来的位置变化，末段把「公司在挑你」翻成「你在挑公司」。
 *
 * 逐行对应旧组件库 `assets/figures.js` 的 `updateStairs`（第 1335–1464 行）、
 * 它用的常量 `STAIRS`（第 1316–1322 行）、`stairCenter`（第 1324–1327 行）
 * 与标记 `MARKUP_STAIRS`（第 1467–1487 行）。数字、表达式与遍历顺序一个都不改：
 * 这一支后面要做逐像素 PSNR ≥ 60 dB 的抽帧对照，任何一处「顺手简化」都会变成像素差。
 *
 * 从「每帧改 DOM」翻成「每帧算样式」时，有几处**看起来可以简化、简化就会改画面**：
 *
 * - `bars` 的结构与顺序必须与旧实现一致（`data.items` 的顺序、每根柱子内部
 *   `rect → note → label` 的顺序）。旧实现走的是 buildOnce + 三个
 *   `children[0..2]` 的索引写入，顺序变了画面就变；
 * - 焦点是 `index === activeStep`。旧注释里写得很清楚：焦点**跟着口播走**，
 *   而不是「最后一根长到 95% 才点亮」；`activeStep` 的判定用 `>=` 且是
 *   「越靠后的命中覆盖前面的」，因此最后一根命中时焦点落在最后一根；
 * - 柱子高度与说明位置吃的是**弹簧进度**（`motion.spring(..., 'firm')`，
 *   在运行时里就是 `springBy`），不是缓动过的进度；
 * - `STAIRS.HEIGHTS[index] || 120` 这个回退照搬：`items` 超过 4 项时
 *   第 5 根（以及与它相关的落点、注写）用 120 高，而不是不画或抛错；
 * - 小球的落点循环里，`prev` / `next` 取的是**固定表**里的高度，
 *   不是被钳制过的当前高度——跳到第 i 格之前小球确实停在 i-1 的柱顶；
 * - 小球的两个圆画在 `<g data-el="bars">` **之后**（SVG 里同一个位置），
 *   因为「谁压谁」由这个顺序决定：小球必须在柱子之上；
 * - 说明文字取的是**当前焦点那一条**（不是永远第一条），取档的输入也跟着焦点走；
 * - 字号一律来自样式类（`.stair-label` 等），组件里不写死 `font-size`。
 *   `data-a2v-fit` 只挂在旧标记本来就有的两处（`title` / `caption`），
 *   取档由 `useFit` 负责，未启用预设时不取档。
 */
import type { CSSProperties, FC } from 'react';

import {
  EASE,
  beat,
  plainText,
  svgOpacity,
  useFigure,
  useFit,
  type FigureRuntime,
} from '@/runtime/figures';
import { springBy } from '@/runtime/motion';

/* ------------------------------------------------------------------ *
 * 几何常量与纯函数
 *
 * 旧实现把这些算式写在 `updateStairs` 与 `stairCenter` 里，混着 DOM 操作。
 * 这里抽成具名纯函数：几何与数值部分可以脱离 React 逐值手算核对
 * （见 `Stairs.test.ts`），组件本体只负责把它们摆到节点上。
 * ------------------------------------------------------------------ */

/** 阶梯的几何常量，与旧实现 `STAIRS`（第 1316–1322 行）逐值一致。 */
export const STAIRS = {
  /** 基线（台阶落脚的那条横线）在 SVG 用户坐标里的 y */
  BASE: 545,
  /** 每根台阶的宽度 */
  BAR_W: 152,
  /** 相邻台阶的间隔 */
  GAP: 64,
  /** 前四根台阶的高度；`items` 超过 4 项时回退 120（旧实现的 `|| 120`） */
  HEIGHTS: [100, 210, 330, 460],
  /** 每一根台阶开始上升的时间点（场景比例） */
  START: [0.07, 0.24, 0.48, 0.73],
  /** 时间点缺省值：旧实现写了两遍 `STAIRS.START[index] === undefined ? 0.73 : ...` */
  START_FALLBACK: 0.73,
  /** `HEIGHTS[index]` 缺省值：旧实现的 `STAIRS.HEIGHTS[index] || 120` */
  HEIGHT_FALLBACK: 120,
  /** 画布宽度（`viewBox` 是 888×640），居中用它 */
  CANVAS_W: 888,
  /** 小球的跳跃时长（帧）与抬升高度 */
  HOP_FRAMES: 24,
  HOP_LIFT: 96,
  /** 小球入场：起点用 `beat(0.05)` 打底，再横跨 20 帧淡入 */
  MARKER_IN_FRAMES: 20,
  /** 末段翻转的起点与时长（场景比例），以及判据阈值 */
  FLIP_FROM: 0.84,
  FLIP_SPAN: 0.1,
  FLIP_TICK: 0.5,
} as const;

/**
 * 阶梯整体的占用宽度：`n * BAR_W + (n - 1) * GAP`。
 *
 * 旧实现把它内联在 `stairCenter` 里逐次重算。抽出来是为了让「居中」这条
 * 几何约定可以被单独核对——它决定整组台阶的横向落点，错了整幕都歪。
 */
export function stairTotalWidth(count: number = STAIRS.HEIGHTS.length): number {
  const steps = Number.isFinite(count) && count > 0 ? Math.floor(count) : 0;
  return steps * STAIRS.BAR_W + Math.max(steps - 1, 0) * STAIRS.GAP;
}

/** 第 `index` 根台阶的中心 x：居中的整组里按「宽 + 间隔」递推（旧 `stairCenter`）。 */
export function stairCenter(index: number): number {
  return (
    (STAIRS.CANVAS_W - stairTotalWidth()) / 2 +
    index * (STAIRS.BAR_W + STAIRS.GAP) +
    STAIRS.BAR_W / 2
  );
}

/**
 * 第 `index` 根台阶的**目标**高度。
 *
 * `|| HEIGHT_FALLBACK` 是照搬旧实现：表外（第 5 根起）回退 120，
 * `items` 数超出建议区间时是「多画一根矮的」，不是抛错也不是不画。
 */
export function stairHeight(index: number): number {
  return STAIRS.HEIGHTS[index] || STAIRS.HEIGHT_FALLBACK;
}

/** 第 `index` 根台阶在某一时刻的实际高度：目标高度 × 弹簧进度（钳到 0..1）。 */
export function stairBarHeight(index: number, springProgress: number): number {
  return stairHeight(index) * clamp01(springProgress);
}
/** 柱子自己的矩形（`y` 在上边，所以是 `BASE - height`）。 */
export function stairBarRect(index: number, height: number): { x: number; y: number } {
  return { x: stairCenter(index) - STAIRS.BAR_W / 2, y: STAIRS.BASE - height };
}

/** 柱子上方注写的 y：柱顶再抬 44px。柱子长高时它跟着走。 */
export function stairNotePoint(index: number, height: number): { x: number; y: number } {
  return { x: stairCenter(index), y: STAIRS.BASE - height - 44 };
}

/** 柱脚标签的 y：基线下方 52px。 */
export function stairLabelPoint(index: number): { x: number; y: number } {
  return { x: stairCenter(index), y: STAIRS.BASE + 52 };
}

/** 注写的不透明度：弹簧过 0.55 之后按斜率 2.2 拉开。 */
export function stairNoteOpacity(springProgress: number): number {
  return clamp01((springProgress - 0.55) * 2.2);
}

/** 标签的不透明度：弹簧过 0.3 之后按斜率 2 拉开（比注写早一点）。 */
export function stairLabelOpacity(springProgress: number): number {
  return clamp01((springProgress - 0.3) * 2);
}

/** 说明文字的不透明度：整段淡入到 0.94 封顶（旧实现乘 0.94）。 */
export function stairCaptionOpacity(p: number): number {
  return clamp01(p) * 0.94;
}

/** 小球入场的不透明度：`beat(0.05)` 起横跨 20 帧。 */
export function stairMarkerOpacity(p: number): number {
  return clamp01(p);
}

/** 光晕的不透明度：小球入场进度 × 0.9。 */
export function stairHaloOpacity(p: number): number {
  return stairMarkerOpacity(p) * 0.9;
}

/** 某个下标的时间点（场景比例）。表外回退 0.73，与旧实现的两处三元表达式一致。 */
export function stairStartFraction(index: number): number {
  return STAIRS.START[index] === undefined ? STAIRS.START_FALLBACK : STAIRS.START[index];
}

/** 时间点换算成绝对帧号：与 `beat(fig, x)` 同一条换算（比例 + 该幕节奏）。 */
export function stairStartFrame(runtime: FigureRuntime, index: number): number {
  return beat(runtime, stairStartFraction(index));
}

/**
 * 当前焦点台阶：**当前这一级就是焦点**，逐级推进。
 *
 * 逐项用 `f >= 起始帧` 判定，并且**后面的命中覆盖前面的**——因此小球跳到
 * 第三级时焦点是第三级，第四节没到之前焦点不会跑到最后一根上去。
 * `items` 为空时返回 0（旧实现初始化 `activeStep = 0`）。
 */
export function activeStairStep(
  localFrame: number,
  starts: readonly number[],
  count: number = starts.length,
): number {
  let active = 0;
  for (let index = 0; index < count; index += 1) {
    const start = starts[index];
    if (start === undefined || localFrame >= start) {
      active = index;
    }
  }
  return active;
}

/**
 * 小球逐格跳的进度：`hopStart = beat(START[i]) - beat(0.05)`，
 * 横跨 `beat(0.05)` 帧走完。`frame < hopStart` 时是 0（还没起跳）。
 */
export function stairHopAt(
  localFrame: number,
  hopStart: number,
  hopFrames: number,
): number {
  return easeOutQuint(clamp01(hopFrames > 0 ? (localFrame - hopStart) / hopFrames : localFrame >= hopStart ? 1 : 0));
}

/**
 * 小球在第 i 格起跳途中的位置。
 *
 * x 在相邻柱心之间线性插值；y 插值之后再抬一个正弦拱（`sin(hop·π) · 96`），
 * 这条拱就是「跳」这个动作的全部视觉来源，弧度、96px 与旧实现逐值相同。
 */
export function stairHopArc(
  from: { x: number; y: number },
  to: { x: number; y: number },
  hop: number,
): { x: number; y: number } {
  return {
    x: from.x + (to.x - from.x) * hop,
    y: from.y + (to.y - from.y) * hop - Math.sin(hop * Math.PI) * STAIRS.HOP_LIFT,
  };
}

/**
 * 小球在第 `frame` 帧的落点。
 *
 * 初始落点是第一根柱顶；随后每一格**只在自己起跳之后**才改写位置，
 * 所以「还没起跳的格子」不会把小球提前拉过去。循环从 1 开始、按 `count` 收尾，
 * 与旧实现 `for (var i = 1; i < groups.length; i += 1)` 同一段区间。
 */
export function stairMarkerPosition(
  frame: number,
  hopStarts: readonly number[],
  hopFrames: number,
  count: number = hopStarts.length,
): { x: number; y: number } {
  let pos = {
    x: stairCenter(0),
    y: STAIRS.BASE - stairHeight(0),
  };
  for (let index = 1; index < count; index += 1) {
    const hopStart = hopStarts[index];
    if (hopStart === undefined || frame < hopStart) {
      continue;
    }
    const hop = stairHopAt(frame, hopStart, hopFrames);
    pos = stairHopArc(
      { x: stairCenter(index - 1), y: STAIRS.BASE - stairHeight(index - 1) },
      { x: stairCenter(index), y: STAIRS.BASE - stairHeight(index) },
      hop,
    );
  }
  return pos;
}

/** 小球坐标的写法：旧实现 `toFixed(1)`，属性值因此是字符串。 */
export function stairMarkerAttrs(pos: { x: number; y: number }): { cx: string; cy: string } {
  return { cx: pos.x.toFixed(1), cy: pos.y.toFixed(1) };
}

/** 末段翻转的进度：从 `beat(0.84)` 起横跨 `beat(0.1)`。 */
export function stairFlipProgress(localFrame: number, flipFrom: number, flipSpan: number): number {
  return easeInOutCubic(clamp01(flipSpan > 0 ? (localFrame - flipFrom) / flipSpan : localFrame >= flipFrom ? 1 : 0));
}

/** 翻转已经发生（进度过半）：决定视角文案与箭头朝向。 */
export function stairFlipState(flipProgress: number): 'after' | 'before' {
  return flipProgress > STAIRS.FLIP_TICK ? 'after' : 'before';
}

/** 视角文案：翻转前是 before，翻转后是 after。 */
export function stairFlipText(flipProgress: number, before: string, after: string): string {
  return stairFlipState(flipProgress) === 'after' ? after : before;
}

/** 箭头朝向类名：`flip-arrow is-right` / `flip-arrow is-left`（旧实现整串覆盖）。 */
export function stairArrowClassName(flipProgress: number): string {
  return 'flip-arrow ' + (stairFlipState(flipProgress) === 'after' ? 'is-right' : 'is-left');
}

/** 翻转条的透明度：`beat(0.8)` 起横跨 20 帧（比翻转本身早一点露出来）。 */
export function stairFlipOpacity(p: number): number {
  return clamp01(p);
}

/** 分镜里的一个阶梯条目：字符串或 `{label, note, desc}`。 */
export interface StairItem {
  label: string;
  /** 柱子上方的注写 */
  note: string;
  /** 跟随口播的说明文字 */
  desc: string;
}

/**
 * 把 `data.items` 归一成三个字符串字段。
 *
 * 旧实现在三处各自解析同一条目（柱子用 `entry.note`/`entry.label`，
 * 说明用 `entry.desc`/字符串本体），三处口径必须一致，否则「标签写了、
 * 说明却读成另一套」。这里归一成一份，组件里就不再重复解析。
 * `items` 缺失或不是数组时返回空数组——空 items 不抛错。
 */
export function normalizeStairItems(items: unknown): StairItem[] {
  if (!Array.isArray(items)) {
    return [];
  }
  return items.map((item) => {
    if (typeof item === 'string') {
      return { label: item, note: '', desc: item };
    }
    if (item && typeof item === 'object') {
      const entry = item as Record<string, unknown>;
      return {
        label: plainText(entry['label']),
        note: plainText(entry['note']),
        desc: plainText(entry['desc']),
      };
    }
    return { label: plainText(item), note: '', desc: plainText(item) };
  });
}

/** 说明文字的第 `index` 条：越界时为空串（旧实现 `items[activeStep] || {}`）。 */
export function stairCaptionText(items: readonly StairItem[], index: number): string {
  const entry = items[index];
  return entry ? entry.desc : '';
}

/* ------------------------------------------------------------------ *
 * 内部小工具：与运行时同一口径的钳制与三条曲线
 * ------------------------------------------------------------------ */

/** `EASE.out`（outQuint）的解析式：与 `motion.EASING` 同一条曲线。 */
function easeOutQuint(t: number): number {
  return 1 - (1 - t) ** 5;
}

/** `EASE.symmetric`（inOutCubic）的解析式。 */
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
}

/** 与运行时语义一致的钳制，避免为一个小工具再暴露一层接口（同旧 `clampStatic`）。 */
function clamp01(value: number): number {
  return value < 0 ? 0 : value > 1 ? 1 : value;
}

/* ------------------------------------------------------------------ *
 * 组件
 * ------------------------------------------------------------------ */

export const StairsFigure: FC = () => {
  const fig = useFigure();
  const localFrame = fig.state.localFrame;

  const items = normalizeStairItems(fig.data['items']);
  /*
   * 这一幕只有一个 focus：先算出当前焦点，说明文字与柱子的焦点态共用它。
   * （旧实现里 `activeStep` 在柱子循环之前算，说明文字在循环之后用。）
   */
  const timeline = stairTimeline(
    localFrame,
    (index) => stairStartFrame(fig, index),
    (fraction) => beat(fig, fraction),
    items.length,
  );

  /*
   * 取档只发生在旧标记本来就有的锚点上（`data-a2v-fit`），字号档位因此与旧路径
   * 同一套：`title` 一档、说明文字 `body` 一档。未启用预设时 `useFit` 返回空样式，
   * 元素按样式表的字号渲染——组件里任何地方都不写死 `font-size`。
   */
  const titleText = plainText(fig.data['title']);
  const title = useFit({ level: 'title', text: titleText });
  // 说明文字「口播念到哪一句，屏幕上就是哪一句」，取档的输入也跟着焦点走
  const captionText = stairCaptionText(items, timeline.activeStep);
  const caption = useFit({ level: 'body', text: captionText });

  return (
    <>
      <h2
        className="section-title"
        data-el="title"
        data-a2v-fit="title"
        ref={title.ref}
        style={{ ...title.style }}
      >
        {titleText}
      </h2>
      {/* 阶梯：每一根柱子是一次上场之后的「位置」，小球沿着柱顶往上跳 */}
      <div
        className="stair-caption"
        data-el="caption"
        data-a2v-fit="body"
        ref={caption.ref}
        style={{ opacity: String(stairCaptionOpacity(captionProgress(fig))) }}
      >
        {captionText}
      </div>
      <StairsSvg fig={fig} items={items} timeline={timeline} />
      <StairFlip fig={fig} />
    </>
  );
};

/** 说明文字的入场进度：`beat(0.03)` 起横跨 22 帧（比后面的元素都早）。 */
function captionProgress(fig: FigureRuntime): number {
  return fig.api.progress(fig.state.localFrame, beat(fig, 0.03), 22, EASE.out);
}

/** 阶梯的画布：轴线、基线、逐根柱子与小球。 */
const StairsSvg: FC<{
  fig: FigureRuntime;
  items: readonly StairItem[];
  timeline: StairTimeline;
}> = ({ fig, items, timeline }) => {
  const localFrame = fig.state.localFrame;
  const api = fig.api;

  /*
   * 两条线是「画」出来的：长度用显式常量（旧实现同样写死 842 / 467，
   * 而不是去量 `getTotalLength()`），进度各走自己的起点与时长。
   * 顺序也照抄：先基线后轴线（描边叠在一起时，谁压谁由这个顺序决定）。
   */
  const baseline = api.drawPath(
    api.progress(localFrame, beat(fig, 0.04), beat(fig, 0.12), EASE.out),
    842,
  );
  const axis = api.drawPath(
    api.progress(localFrame, beat(fig, 0.05), beat(fig, 0.14), EASE.out),
    467,
  );

  return (
    <svg className="fig fig-stairs" viewBox="0 0 888 640" aria-hidden="true">
      <defs>
        <radialGradient id="stair-halo">
          <stop
            offset="0"
            stopColor="color-mix(in srgb, var(--a2v-accent-soft-solid) 32%, transparent)"
          />
          <stop
            offset="1"
            stopColor="color-mix(in srgb, var(--a2v-accent-soft-solid) 0%, transparent)"
          />
        </radialGradient>
      </defs>
      <text className="stair-axis-label" data-el="axisLabel" x="24" y="44">
        {plainText(fig.spec.labels['axis'])}
      </text>
      <path className="stair-axis" data-el="axis" d="M26 545 L26 78" {...axis} />
      <path className="stair-base" data-el="baseline" d="M26 545 L868 545" {...baseline} />
      <g data-el="bars">
        {items.map((item, index) => {
          const start = timeline.starts[index] ?? 0;
          // 柱子长高吃的是弹簧（线性秒数），不是缓动进度：喂缓动过的进度会让
          // 弹簧的自然周期失去意义（与 NumberFigure 里注释的是同一件事）。
          const p = springBy(api.since(localFrame, start), 'firm');
          const height = stairBarHeight(index, p);
          const bar = stairBarRect(index, height);
          const note = stairNotePoint(index, height);
          const label = stairLabelPoint(index);
          const isFocus = index === timeline.activeStep;
          /*
           * 状态照抄旧实现：**每一根柱子都带 `data-a2v-state`**，
           * 非焦点是 `rest` 而不是「不写这个属性」。基元层里
           * `.a2v-surface[data-a2v-state="rest"]` 与 `.a2v-surface` 取值相同，
           * 所以两种写法看起来一样；但「同一帧只有一个 focus、其余都是 rest」
           * 是基元层的读法，缺属性的元素在那套读法里等于没有状态。
           */
          const state = isFocus ? 'focus' : 'rest';
          return (
            <g key={index} data-bar={String(index)}>
              <rect
                className="stair-bar a2v-surface"
                data-a2v-state={state}
                x={bar.x}
                y={bar.y}
                width={STAIRS.BAR_W}
                height={height}
                rx={20}
              />
              <text
                className="stair-note a2v-label"
                data-a2v-state={state}
                x={note.x}
                y={note.y}
                opacity={svgOpacity(stairNoteOpacity(p))}
              >
                {item.note}
              </text>
              <text
                className="stair-label"
                x={label.x}
                y={label.y}
                opacity={svgOpacity(stairLabelOpacity(p))}
              >
                {item.label}
              </text>
            </g>
          );
        })}
      </g>
      <StairMarker fig={fig} timeline={timeline} />
    </svg>
  );
};

/**
 * 小球入场的两个圆：位置逐帧改，光晕另乘 0.9。
 *
 * 与柱子的入场不同，小球**不**走弹簧：它是「已经到了」的那一个点，
 * 只有淡入（20 帧），起跳的动感来自位置本身。
 * 两个圆留在 SVG 里的同一个位置（柱子组之后、收尾之前），因为
 * 「谁压谁」由这个顺序决定——小球必须画在柱子上方才不会被柱子盖住。
 */
const StairMarker: FC<{ fig: FigureRuntime; timeline: StairTimeline }> = ({ fig, timeline }) => {
  const localFrame = fig.state.localFrame;
  const markerIn = fig.api.progress(
    localFrame,
    stairStartFrame(fig, 0),
    STAIRS.MARKER_IN_FRAMES,
    EASE.out,
  );
  const pos = stairMarkerPosition(
    localFrame,
    timeline.hopStarts,
    timeline.hopFrames,
    timeline.starts.length,
  );
  const attrs = stairMarkerAttrs(pos);
  return (
    <>
      <circle
        className="stair-marker-halo"
        data-el="markerHalo"
        cx={attrs.cx}
        cy={attrs.cy}
        r={64}
        opacity={svgOpacity(stairHaloOpacity(markerIn))}
      />
      <circle
        className="stair-marker"
        data-el="marker"
        cx={attrs.cx}
        cy={attrs.cy}
        r={22}
        opacity={svgOpacity(stairMarkerOpacity(markerIn))}
      />
    </>
  );
};

/** 这一幕的时间线：每根台阶的起始帧、起跳帧、当前焦点与小球的跳跃时长。 */
export interface StairTimeline {
  /** 每根台阶开始上升的绝对帧号 */
  starts: number[];
  /** 每根台阶对应的小球起跳帧（比 `starts` 早 `beat(0.05)`） */
  hopStarts: number[];
  /** 小球一次跳跃的时长（帧），即 `beat(0.05)` */
  hopFrames: number;
  /** 当前焦点台阶的下标 */
  activeStep: number;
}

/**
 * 把「比例时间点」一次换算成这一幕的帧号表。
 *
 * 抽成一个函数只为一件事：**顺序与口径唯一**。旧实现先算 `activeStep`
 * （用起始帧判定），再在逐项里用同一个起始帧算弹簧，小球循环又用一次；
 * 三处各算一遍就会漂移。这里算一次，说明文字、柱子与小球共用同一份。
 *
 * 两个换算是注入的（`startFrameOf` / `fractionToFrames`），因此这个函数不依赖
 * 运行时对象，可以脱离 React 用手算的帧号直接核对。
 */
function stairTimeline(
  localFrame: number,
  startFrameOf: (index: number) => number,
  fractionToFrames: (fraction: number) => number,
  count: number,
): StairTimeline {
  const hopFrames = fractionToFrames(0.05);
  const starts: number[] = [];
  const hopStarts: number[] = [];
  for (let index = 0; index < count; index += 1) {
    const start = startFrameOf(index);
    starts.push(start);
    hopStarts.push(start - hopFrames);
  }
  return {
    starts,
    hopStarts,
    hopFrames,
    activeStep: activeStairStep(localFrame, starts, count),
  };
}

/** 末段的视角翻转：胶囊底色与文案、箭头朝向。 */
const StairFlip: FC<{ fig: FigureRuntime }> = ({ fig }) => {
  const localFrame = fig.state.localFrame;
  const api = fig.api;
  const flipP = stairFlipProgress(
    localFrame,
    beat(fig, STAIRS.FLIP_FROM),
    beat(fig, STAIRS.FLIP_SPAN),
  );
  const style: CSSProperties = {
    opacity: String(stairFlipOpacity(api.progress(localFrame, beat(fig, 0.8), 20, EASE.out))),
  };
  return (
    <div
      className={'stair-flip' + (stairFlipState(flipP) === 'after' ? ' is-after' : '')}
      data-el="flip"
      style={style}
    >
      <span className={stairArrowClassName(flipP)} data-el="flipArrow" />
      <span data-el="flipText">
        {stairFlipText(
          flipP,
          plainText(fig.spec.labels['before']),
          plainText(fig.spec.labels['after']),
        )}
      </span>
    </div>
  );
};
