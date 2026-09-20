/**
 * 冰山幕：看得见的一角与看不见的主体**不是一回事**。
 *
 * 逐行对应旧组件库 `assets/figures.js` 的：
 *   - `BERG` 几何常量（旧文件第 849–859 行）
 *   - `updateIceberg`（第 867–1005 行）
 *   - `MARKUP_ICEBERG`（第 1008–1042 行）
 *   - 用到的类名逐字符来自 `figures.css` 第 467–560 行（本组件不改那份样式）
 *
 * 与旧实现的差别只有一处，而且是 React 决定的：旧版每帧把算出来的值**写进 DOM**
 * （`svgT` / `svgO` / `setAttribute`），这里每帧**算出属性交给 React**。数值表达式
 * 一个都没动，因此同一帧算出来的数与旧路径逐位相同（抽帧对照要的就是这个）。
 *
 * ## 填充与层级：这张图的语义全在这里
 *
 * SVG 没有 z-index，**DOM 顺序就是绘制顺序**，后来者盖在先来者上面。旧 markup
 * （第 1030–1041 行）的顺序是刻意排的，照抄时必须原样保住：
 *
 * 1. `<rect class="berg-water" data-el="waterBody">` 是**水体本身**。它自己不带
 *    `fill`，填充由 `figures.css` 的 `.berg-water { fill: url(#berg-depth) }` 给
 *    （旧 CSS 第 479–482 行）——水体填充只有这一个令牌，是一条自上而下三档 alpha
 *    的渐变（`.berg-depth-1/2/3`，深到浅直到透明），所以水体下缘是「化开」的，
 *    不是一条硬边。
 * 2. `<path class="ln" data-el="waterLine">` 水面线画在水体**之后**：线压在水面上，
 *    不被水体的渐变压暗。
 * 3. `<path class="berg-tip" data-el="tip">` 水上尖端也画在水体**之后**，它的面取
 *    `--fig-surface`（实心物体那一档）、描边取 `--fig-line`（`figures.css` 第 484–489 行）
 *    ——**不是水的颜色**。这正是「看得见的一角」与「看不见的主体」在画面上被区分开的
 *    手段：一个走实心面，一个走冷色水面（见 `tests/test_figure_contrast.py` 的
 *    `TestFaceTiersStayDistinct`：三档面填充不许塌成同一个取值）。
 *    尖端底边正好压在 y=300 上，与水体矩形零重叠；即便如此也必须后画——一旦提前，
 *    水体边缘的任何抗锯齿/描边外扩都会把尖端下缘盖掉。
 * 4. `<g data-el="massGroup">` 水下主体画在**最后**，它的面取 `--fig-water`
 *    （半透明冷色，`figures.css` 第 491–498 行）并叠在水体渐变**之上**——这才是
 *    「这一大团在水里」的读法：主体被水体罩着，而不是浮在水面之前。它的顶边
 *    （y=300）与尖端底边共线，两块拼成一座完整的山。
 * 5. 光带 `<rect data-el="lightBand">` 在 `massGroup` **内部**，并被
 *    `clip-path: url(#berg-clip)` 裁到主体轮廓上；`#berg-clip` 的 `d` 与主体路径
 *    逐字相同。因此那束光只扫在主体上，不会漏到水体或水上尖端。
 *
 * 上面五条在 `Iceberg.test.ts` 里有机检（`BERG_PAINT_ORDER` 与 `BERG_LAYER_FILL`），
 * 不是只写在注释里。
 *
 * ## 一处没能逐字照搬的地方（唯一一处）
 *
 * 三条标注连线的描边长度：旧实现用 `link.getTotalLength()` **量**出来存在
 * `dataset.length` 上（第 971 行）。新组件不许读 DOM（也不该把长度藏进属性里），
 * 因此按三次贝塞尔的弧长**算**出来（`bergCalloutLinkLength`，模块加载时算一次，
 * 之后逐帧同一个值）。数值本身与浏览器量出来的相差在 0.1% 量级（三条线各 ≈154 /
 * 152 / 122 user unit，见测试里的双方法互校），只影响连线正在画出来的那 22 帧里
 * 线头不到 0.2px 的位置；描边画满（p=1）时两者完全一致。
 * 旧版还会顺手把长度写回 `data-a2v-length` 属性，那是被显式传值覆盖后的残留，
 * 这里不写——它是隐藏状态，不影响像素。
 */
import type { FC } from 'react';

import {
  EASE,
  beat,
  enterSvgAttrs,
  plainText,
  sinceBeat,
  svgOpacity,
  svgTransform,
  useFigure,
  useFit,
  type FigureApi,
} from '@/runtime/figures';
import { clamp, range, springBy, type PathDrawStyle } from '@/runtime/motion';

/* ---------------- 照搬的常量（旧 figures.js 第 849–859 行的 BERG） ---------------- */

/** 画面与水面线：`viewBox` 与水体矩形都按这个坐标系（旧 markup 第 1010 / 1030 行）。 */
export const BERG_VIEW_WIDTH = 888;
export const BERG_VIEW_HEIGHT = 760;
/** 水面线 y。水体矩形从它起画，水上尖端的底边压在它上面，水下主体的顶边也压在它上面。 */
export const BERG_WATERLINE_Y = 300;
/** 水体矩形高度（旧 markup 第 1030 行 `height="460"`）：300 + 460 = 760，正好到底。 */
export const BERG_WATER_HEIGHT = 460;

/** 标注卡片的左边界、宽、高、三个槽位的 y（旧 BERG.CALLOUT_X / _W / _H / _Y）。 */
export const BERG_CALLOUT_X = 452;
export const BERG_CALLOUT_W = 428;
export const BERG_CALLOUT_H = 132;
export const BERG_CALLOUT_RX = 28;
/** 三个槽位的卡片顶边 y。 */
export const BERG_CALLOUT_Y = [84, 316, 548] as const;
/** 连线在这三个槽位要指向的目标点（水上 / 水下 / 出路）。 */
export const BERG_TARGETS = [
  { x: 300, y: 172 },
  { x: 300, y: 384 },
  { x: 344, y: 566 },
] as const;
/**
 * 几何表能容纳的标注数（= 三个槽位）。**这是容量上限，不是渲染上限**：
 * 超过它的条目会复用最后一格（见 `bergCalloutGeometry`），不会崩、也不会画出 NaN。
 */
export const BERG_CALLOUT_SLOTS = BERG_CALLOUT_Y.length;
/** 卡片内文字的左边距与两行文字的基线下移（旧 updateIceberg 里的 32 / 50 / 96）。 */
export const BERG_CALLOUT_TEXT_X = 32;
export const BERG_CALLOUT_LABEL_DY = 50;
export const BERG_CALLOUT_DESC_DY = 96;
/** 连线从卡片左缘往左伸出的控制点偏移与 C 段控制点偏移（旧表达式里的 44 / 70）。 */
export const BERG_LINK_BEND = 44;
export const BERG_LINK_TARGET_PULL = 70;

/** 三条标注出现的顺序：先水上、再水下、最后出路（旧 `starts`，第 964 行）。 */
export const BERG_CALLOUT_STARTS = [0.2, 0.5, 0.72] as const;
/** 槽位超出 `BERG_CALLOUT_STARTS` 时的起拍点（旧实现的 `undefined → 0.72` 兜底）。 */
export const BERG_CALLOUT_FALLBACK_START = 0.72;
/** 连线比卡片早 8 帧起画、画 22 帧（旧第 973 行 `progress(f, start - 8, 22, …)`）。 */
export const BERG_LINK_LEAD_FRAMES = 8;
export const BERG_LINK_DRAW_FRAMES = 22;
/** 卡片 / 标签 / 说明的入场位移：从右侧 34px 进来（旧 `(1 - p) * 34`）。 */
export const BERG_CALLOUT_RISE = 34;

/** 水面线的总长：`M0 300 L888 300` 就是 888（旧第 947 行显式传入）。 */
export const BERG_WATER_LINE_LENGTH = 888;

/** 水下主体升起的位移与缩放区间（旧第 959 行里的 150 / 0.94）。 */
export const BERG_MASS_RISE = 150;
export const BERG_MASS_SCALE_MIN = 0.94;

/** 光照带横向扫过的区间与自身尺寸（旧第 990 行与 markup 第 1037 行）。 */
export const BERG_BAND_X_FROM = -320;
export const BERG_BAND_X_TO = 900;
export const BERG_BAND_Y = 260;
export const BERG_BAND_W = 320;
export const BERG_BAND_H = 480;
/** 光带淡出的残量：扫过之后只退到 65%（旧 `1 - progress * 0.35`）。 */
export const BERG_BAND_TAIL = 0.35;

/** 5 颗上浮粒子的条数与位置（旧第 938–943 / 996–1004 行）。 */
export const BERG_SPARK_COUNT = 5;
export const BERG_SPARK_R = 8;
/** 一颗粒子比前一颗晚起 9 帧。 */
export const BERG_SPARK_STEP_FRAMES = 9;
/** 上浮起点与终点（水面下方 620 → 水面之上 168）。 */
export const BERG_SPARK_Y_FROM = 620;
export const BERG_SPARK_Y_TO = 168;
/** 横向基准与水下的三条泳道（`344 + ((index % 3) - 1) * 30`）。 */
export const BERG_SPARK_BASE_X = 344;
export const BERG_SPARK_LANE_STEP = 30;
/** 上浮途中的横向摆幅（`sin(life * π) * 10`）。 */
export const BERG_SPARK_SWAY = 10;

/* ---------------- 层级：绘制顺序与每层的填充令牌（机检用） ---------------- */

/**
 * 画面的绘制顺序 = 旧 markup 的 DOM 顺序（旧第 1030–1041 行）。
 * 数组下标越大越晚画、越靠上。层级关系依赖它，因此它是导出常量而不是注释。
 */
export const BERG_PAINT_ORDER = [
  'waterBody',
  'waterLine',
  'surfaceNote',
  'tip',
  'mass',
  'lightBand',
  'sparks',
  'callouts',
] as const;

export type BergLayer = (typeof BERG_PAINT_ORDER)[number];

/** 某一层在绘制顺序里的位置；越晚画越靠上。 */
export function bergLayerIndex(layer: BergLayer): number {
  return BERG_PAINT_ORDER.indexOf(layer);
}

/**
 * 每层用的填充令牌（来自 `figures.css`，本组件不改 CSS，只是把关系钉住）。
 *
 * `waterBody` 走的是**渐变引用**而不是某个颜色：水体是「越深越淡」的一条面，
 * 不是一块蓝。`tip` 与 `mass` 走的是面填充的两档不同令牌——这个差就是这张图的语义。
 */
export const BERG_LAYER_FILL = {
  waterBody: 'url(#berg-depth)',
  tip: 'var(--fig-surface)',
  mass: 'var(--fig-water)',
} as const;

/* ---------------- 水上 / 水下的分区（纯几何） ---------------- */

export interface BergPoint {
  x: number;
  y: number;
}

/** 水上尖端的三点（旧 markup 第 1033 行）：底边两点正好落在水面线上。 */
export const BERG_TIP_POINTS: readonly BergPoint[] = [
  { x: 215, y: 64 },
  { x: 138, y: 300 },
  { x: 296, y: 300 },
];

/** 水下主体的六点（旧 markup 第 1035 行，与 `#berg-clip` 的 d 逐字相同）。 */
export const BERG_MASS_POINTS: readonly BergPoint[] = [
  { x: 138, y: 300 },
  { x: 296, y: 300 },
  { x: 392, y: 452 },
  { x: 348, y: 632 },
  { x: 150, y: 692 },
  { x: 34, y: 500 },
];

/**
 * 一个点相对水面的位置。
 *
 * 水面线本身单列一档（`waterline`）而不是并进任何一边：它是一条零面积的线，
 * 「压在水面线上」这件事在画面上的意思是**两块拼在一起**，不是「在水里」。
 */
export function bergZone(y: number): 'above' | 'below' | 'waterline' {
  if (y < BERG_WATERLINE_Y) {
    return 'above';
  }
  return y > BERG_WATERLINE_Y ? 'below' : 'waterline';
}

/**
 * 一个多边形整体落在水面哪一侧：`above` / `below` / `spanning`（被水面切开）。
 *
 * 判据是**面积**而不是顶点：顶点允许压在水面线上（尖端的底边、主体的顶边都压着），
 * 只要另一侧还有顶点，这个多边形就确实被切开了——那时它必须按两个区分别着色，
 * 这张图里没有这样的形状。
 */
export function bergPolygonZone(points: readonly BergPoint[]): 'above' | 'below' | 'spanning' {
  let above = 0;
  let below = 0;
  for (const point of points) {
    if (point.y < BERG_WATERLINE_Y) {
      above += 1;
    } else if (point.y > BERG_WATERLINE_Y) {
      below += 1;
    }
  }
  if (above > 0 && below > 0) {
    return 'spanning';
  }
  return above > 0 ? 'above' : 'below';
}

/**
 * 分区深度：水上部分从尖端最高点到水面、水下部分从水面到主体最低点。
 * 旧 markup 里这两个数只能靠读 `d` 数出来，这里让它们成为可断言的量。
 */
export function bergZoneDepth(points: readonly BergPoint[], zone: 'above' | 'below'): number {
  const ys = points.map((point) => point.y);
  return zone === 'above'
    ? BERG_WATERLINE_Y - Math.min(...ys)
    : Math.max(...ys) - BERG_WATERLINE_Y;
}

/* ---------------- 标注几何（纯计算，逐个表达式照搬） ---------------- */

export interface BergCalloutGeometry {
  /** 实际取用的槽位：超出几何表的条目复用最后一格，因此这个值恒在表内。 */
  slot: number;
  /** 卡片顶边 y。 */
  y: number;
  /** 连线指向的目标点。 */
  target: BergPoint;
  /** 连线的 `d`（旧实现每帧拼出来的那条三次贝塞尔）。 */
  linkD: string;
  /** 卡片与文字的 x / y。 */
  boxX: number;
  boxW: number;
  boxH: number;
  labelX: number;
  labelY: number;
  descX: number;
  descY: number;
}

/**
 * 某个槽位的标注几何——**与旧实现同一个表达式**，包括那条连线的字符串拼法。
 *
 * 超出几何表的 `index` 会钳到最后一格：旧实现会在这里取到 `undefined`，
 * 于是 `d` 里出现 `NaN`（浏览器丢弃整条路径）、卡片拿到 `y="undefined"`。
 * 「画不出来」不该表现为一串无效属性，因此这里让它**稳定地复用最后一格**：
 * 多出来的标注会叠在最后一张卡片上，看得见地提示「这一幕超容量了」，
 * 而不会崩、也不会画出一个 NaN。
 */
export function bergCalloutGeometry(index: number): BergCalloutGeometry {
  const safeIndex = Number.isFinite(index) ? Math.max(0, Math.trunc(index)) : 0;
  const slot = Math.min(safeIndex, BERG_CALLOUT_SLOTS - 1);
  const y: number = BERG_CALLOUT_Y[slot];
  const target: BergPoint = BERG_TARGETS[slot];
  const midY = y + BERG_CALLOUT_H / 2;
  return {
    slot,
    y,
    target,
    // 照抄旧第 889–894 行的字符串拼法（数值全是整数，因此两种写法逐字符相同）
    linkD:
      'M' + BERG_CALLOUT_X + ' ' + midY +
      ' C ' + (BERG_CALLOUT_X - BERG_LINK_BEND) + ' ' + midY +
      ', ' + (target.x + BERG_LINK_TARGET_PULL) + ' ' + target.y +
      ', ' + target.x + ' ' + target.y,
    boxX: BERG_CALLOUT_X,
    boxW: BERG_CALLOUT_W,
    boxH: BERG_CALLOUT_H,
    labelX: BERG_CALLOUT_X + BERG_CALLOUT_TEXT_X,
    labelY: y + BERG_CALLOUT_LABEL_DY,
    descX: BERG_CALLOUT_X + BERG_CALLOUT_TEXT_X,
    descY: y + BERG_CALLOUT_DESC_DY,
  };
}

/** 某一条连线起画的拍点：表里没有的槽位走 0.72 兜底（旧第 966 行）。 */
export function bergCalloutStart(index: number): number {
  return BERG_CALLOUT_STARTS[index] ?? BERG_CALLOUT_FALLBACK_START;
}

/**
 * 三次贝塞尔弧长（纯数值，无 DOM）。
 *
 * 为什么需要它：旧实现用 `path.getTotalLength()` 量连线的长度并缓存
 * （旧第 971–972 行）。新组件不读 DOM，所以把这条曲线的弧长直接算出来。
 * 做法是自适应 Simpson：先整段二分，两侧 Simpson 之和与整段之差超过 15ε 就继续细分，
 * 深度封顶保证一定会停。曲线光滑（无尖点、无回折），因此收敛很快，
 * 与 2×10⁵ 段折线求和的差在 1e-9 量级（测试里两种方法互校）。
 *
 * 注意：浏览器量出来的是**另一种近似**（它按平坦度把曲线折线化），
 * 两者相差在 0.1% 量级，见文件头的说明。
 */
export function cubicArcLength(
  p0: BergPoint,
  c1: BergPoint,
  c2: BergPoint,
  p3: BergPoint,
  tolerance = 1e-10,
): number {
  const speed = (t: number): number => {
    const mt = 1 - t;
    const dx =
      3 * mt * mt * (c1.x - p0.x) + 6 * mt * t * (c2.x - c1.x) + 3 * t * t * (p3.x - c2.x);
    const dy =
      3 * mt * mt * (c1.y - p0.y) + 6 * mt * t * (c2.y - c1.y) + 3 * t * t * (p3.y - c2.y);
    return Math.hypot(dx, dy);
  };
  const simpson = (a: number, b: number): number => {
    const m = (a + b) / 2;
    return ((b - a) / 6) * (speed(a) + 4 * speed(m) + speed(b));
  };
  const whole = simpson(0, 1);
  const refine = (a: number, b: number, eps: number, estimate: number, depth: number): number => {
    const m = (a + b) / 2;
    const left = simpson(a, m);
    const right = simpson(m, b);
    const delta = left + right - estimate;
    if (depth <= 0 || Math.abs(delta) <= 15 * eps) {
      return left + right + delta / 15;
    }
    return (
      refine(a, m, eps / 2, left, depth - 1) + refine(m, b, eps / 2, right, depth - 1)
    );
  };
  return refine(0, 1, tolerance, whole, 40);
}

/** 某条标注连线的长度。几何是常量，因此这里算的是常量——逐帧同一个值。 */
export function bergCalloutLinkLength(index: number): number {
  const geo = bergCalloutGeometry(index);
  const midY = geo.y + BERG_CALLOUT_H / 2;
  return cubicArcLength(
    { x: BERG_CALLOUT_X, y: midY },
    { x: BERG_CALLOUT_X - BERG_LINK_BEND, y: midY },
    { x: geo.target.x + BERG_LINK_TARGET_PULL, y: geo.target.y },
    { x: geo.target.x, y: geo.target.y },
  );
}

/** 三条连线的长度表；模块加载时算一次，逐帧只读，不重复计算。 */
export const BERG_CALLOUT_LINK_LENGTHS: readonly number[] = BERG_CALLOUT_Y.map((_y, index) =>
  bergCalloutLinkLength(index),
);

/* ---------------- 条目归一（纯计算） ---------------- */

export interface BergItem {
  label: string;
  desc: string;
}

/** 旧实现写的是 `entry.label || ''`：假值（空串 / 0 / null）一律留空。 */
function oldTextOrEmpty(value: unknown): string {
  return value ? String(value) : '';
}

/**
 * `data.items` 归一成 `{label, desc}`：字符串项按 `{label: 字符串}` 处理（旧第 878 行）。
 *
 * 空值、非数组、非字符串非对象的项都退成空标签而不是抛错：分镜缺字段时应当**画不全**，
 * 不该整幕崩掉（这条是新加的，旧实现会在 `entry.label` 上抛 TypeError）。
 */
export function normalizeBergItems(items: unknown): BergItem[] {
  if (!Array.isArray(items)) {
    return [];
  }
  return items.map((item) => {
    if (typeof item === 'string') {
      return { label: item, desc: '' };
    }
    if (item && typeof item === 'object' && !Array.isArray(item)) {
      const entry = item as Record<string, unknown>;
      return { label: oldTextOrEmpty(entry['label']), desc: oldTextOrEmpty(entry['desc']) };
    }
    return { label: '', desc: '' };
  });
}

/* ---------------- 每帧的数值（纯计算） ---------------- */

/** 本幕的帧输入；与 `fig.state` 同形，便于直接传入。 */
export interface BergMotionState {
  localFrame: number;
  sceneDurationFrames: number;
  motion?: string;
}

/**
 * 本幕用到的运行时原语；由组件的 `fig.api`（`createFigureApi(fps)`）或测试的桩提供。
 * 只取用得到的四项，组件因此不能顺手去碰别的东西。
 */
export type BergCalcApi = Pick<FigureApi, 'progress' | 'since' | 'range' | 'drawPath'>;

export interface BergSparkPose {
  /** `cx` / `cy`：旧实现写的是 `toFixed(1)` 的字符串，这里保持字符串。 */
  cx: string;
  cy: string;
  opacity: string;
}

/**
 * 一颗上浮粒子在 `life`（0..1）处的位置与不透明度。
 *
 * 照搬旧第 996–1004 行：纵向 620→168（`api.range` 默认钳制）、横向按 `index % 3`
 * 分三条泳道再叠一个 `sin(life·π)` 的摆幅（中途最偏、两端归位），
 * 不透明度走 `sin(life·π) * 0.9`——淡入淡出，不会突然出现或消失。
 */
export function bergSparkPose(index: number, life: number): BergSparkPose {
  const y = range(life, BERG_SPARK_Y_FROM, BERG_SPARK_Y_TO);
  const x =
    BERG_SPARK_BASE_X +
    ((index % 3) - 1) * BERG_SPARK_LANE_STEP +
    Math.sin(life * Math.PI) * BERG_SPARK_SWAY;
  return {
    cx: x.toFixed(1),
    cy: y.toFixed(1),
    opacity: String(Math.sin(clamp(life, 0, 1) * Math.PI) * 0.9),
  };
}

export interface BergCalloutFrame {
  index: number;
  /** 最后一个条目是焦点（旧 `isAccent = index === items.length - 1`）。 */
  isAccent: boolean;
  label: string;
  desc: string;
  /** 连线长度（模块级常量，逐帧同值）。 */
  linkLength: number;
  /** 连线的描边进度属性（`drawPath`：dasharray = 长度，dashoffset = 长度×(1−p)，opacity = p）。 */
  link: PathDrawStyle;
  /** 卡片 / 标签 / 说明共用的横向位移（旧 `svgT(x, 0)`）。 */
  shift: string;
  /** 卡片与标签的不透明度。 */
  bodyOpacity: string;
  /** 说明的不透明度：比标签早一点走完（`p * 1.1`）。 */
  descOpacity: string;
}

/**
 * 三条标注在这一帧的状态。
 *
 * 逐项照搬旧第 962–984 行：起拍点 `[0.2, 0.5, 0.72]`、弹簧用 `firm`、
 * 连线比卡片早 8 帧开画并用 `outCubic` 走 22 帧、卡片/标签/说明从右侧 34px 进来，
 * 说明的淡入比标签快一档（`p * 1.1`）。
 */
export function bergCallouts(
  state: BergMotionState,
  api: BergCalcApi,
  beatAt: (fraction: number) => number,
  items: unknown,
): BergCalloutFrame[] {
  const f = state.localFrame;
  const list = normalizeBergItems(items);
  return list.map((item, index) => {
    const start = beatAt(bergCalloutStart(index));
    // 弹簧吃的是**线性秒数**：喂缓动过的进度会让它的自然周期失去意义
    const p = springBy(api.since(f, start), 'firm');
    const linkLength = BERG_CALLOUT_LINK_LENGTHS[Math.min(index, BERG_CALLOUT_SLOTS - 1)]!;
    return {
      index,
      isAccent: index === list.length - 1,
      label: item.label,
      desc: item.desc,
      linkLength,
      link: api.drawPath(
        api.progress(f, start - BERG_LINK_LEAD_FRAMES, BERG_LINK_DRAW_FRAMES, EASE.soft),
        linkLength,
      ),
      shift: svgTransform((1 - p) * BERG_CALLOUT_RISE, 0),
      bodyOpacity: svgOpacity(p),
      descOpacity: svgOpacity(p * 1.1),
    };
  });
}

export interface BergFrameCalc {
  /** 水面线的描边进度属性（旧 `drawPath(waterLine, progress(f, 0.02, 0.1, out), {length: 888})`）。 */
  waterLine: PathDrawStyle;
  /** 水体的不透明度（旧 `svgO(waterBody, progress(f, 0.06, 0.14, symmetric))`）。 */
  waterOpacity: string;
  /** 水面标注的不透明度（旧 `progress(f, 0.1, 0.08, soft)`）。 */
  surfaceNoteOpacity: string;
  /** 水下主体的升起（位移 + 缩放）与不透明度。 */
  mass: { transform: string; opacity: string };
  /** 光照带：横向位置与不透明度。 */
  lightBand: { x: string; opacity: string };
  /** 5 颗上浮粒子。 */
  sparks: BergSparkPose[];
}

/**
 * 本幕一帧的纯计算：**输入相同，输出必然相同**。
 *
 * `beat` 由调用方以 `beatAt` 传入（运行时的 `beat(fig, …)`），本函数不自己推导节拍，
 * 免得出现第二份定义。表达式逐条对应旧 `updateIceberg`，顺序也照着旧代码走。
 */
export function bergFrame(
  state: BergMotionState,
  api: BergCalcApi,
  beatAt: (fraction: number) => number,
): BergFrameCalc {
  const f = state.localFrame;

  // 水面先画出来，再露出水上的一角（旧第 945–948 行）
  const waterLine = api.drawPath(
    api.progress(f, beatAt(0.02), beatAt(0.1), EASE.out),
    BERG_WATER_LINE_LENGTH,
  );
  const waterOpacity = svgOpacity(api.progress(f, beatAt(0.06), beatAt(0.14), EASE.symmetric));
  const surfaceNoteOpacity = svgOpacity(api.progress(f, beatAt(0.1), beatAt(0.08), EASE.soft));

  // 水下那一大团从深处升上来（旧第 957–960 行）：位移线性收窄、缩放 0.94→1。
  // 缩放走 `clamp: false`，让弹簧的轻微过冲也能被看见（与旧实现同一条）
  const massP = springBy(api.since(f, beatAt(0.3)), 'enter');
  const mass = {
    transform: svgTransform(
      0,
      (1 - massP) * BERG_MASS_RISE,
      0,
      api.range(massP, BERG_MASS_SCALE_MIN, 1, { clamp: false }),
    ),
    opacity: svgOpacity(massP),
  };

  // 光照：一束光扫过水下那团（旧第 986–992 行）。
  // 位置吃 `inOutCubic` 的位移，不透明度吃另一条 outCubic 的加法式淡入淡出——
  // 两件事的节奏不同，这是刻意的：光扫到位时最亮，退场时只褪到 65%
  const sweep = api.progress(f, beatAt(0.56), beatAt(0.2), EASE.symmetric);
  const bandIn = api.progress(f, beatAt(0.56), 20, EASE.soft);
  const bandOut = api.progress(f, beatAt(0.78), 24, EASE.soft);
  const lightBand = {
    x: String(api.range(sweep, BERG_BAND_X_FROM, BERG_BAND_X_TO)),
    opacity: svgOpacity(bandIn * (1 - bandOut * BERG_BAND_TAIL)),
  };

  // 光扫过之后浮出水面的一股上升（旧第 994–1004 行）：位置固定在冰山右侧的空白水域
  const sparks: BergSparkPose[] = [];
  for (let index = 0; index < BERG_SPARK_COUNT; index += 1) {
    const start = beatAt(0.62) + index * BERG_SPARK_STEP_FRAMES;
    const life = api.progress(f, start, beatAt(0.28), EASE.linear);
    sparks.push(bergSparkPose(index, life));
  }

  return { waterLine, waterOpacity, surfaceNoteOpacity, mass, lightBand, sparks };
}

/* ---------------- 组件 ---------------- */

/**
 * 幕的画面结构：文案元素留空由分镜注入（照抄 MARKUP_ICEBERG）。
 *
 * 结构上有三处「看着可以合并、合并就会改画面/改层级」的地方：
 *
 * 1. **两个根元素**（`<h2 class="section-title">` 与 `<svg class="fig fig-berg">`）
 *    而不是一个包裹层：旧实现是把这段 markup 直接写进 `.a2v-safe` 的，
 *    多一层 div 会改掉 `.a2v-safe` 的 flex 排布；
 * 2. **`<svg>` 上不写 `width` / `height`**：尺寸来自 `.fig` / `.fig-berg` 的样式表；
 * 3. **`<g data-el="massGroup">` 与 `lightBand` 的嵌套关系照抄**：光带在主体组内部、
 *    并被 `#berg-clip` 裁到轮廓上，层级与裁剪都不能挪。
 */
export const IcebergFigure: FC = () => {
  const fig = useFigure();
  const { data, spec, state } = fig;

  // `beat(fig, fraction)` 就是旧的 `beat(state, …)`；本幕所有拍点都从它取
  const beatAt = (fraction: number) => beat(fig, fraction);
  const calc = bergFrame(state, fig.api, beatAt);
  const callouts = bergCallouts(state, fig.api, beatAt, data['items']);

  const titleText = plainText(data['title']);
  const title = useFit({ level: 'title', text: titleText });
  const surfaceNote = plainText(spec.labels['surface']);

  /*
   * 水上尖端：入场吃**线性秒数**（`sinceBeat`），弹簧自己就是曲线。
   * 位移 34px、常驻微动 2px 照抄旧第 952–955 行的 `{distance: 34, amplitude: 2}`。
   */
  const tip = enterSvgAttrs(fig, sinceBeat(fig, 0.1), { distance: 34, amplitude: 2 });

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
      {/* 冰山：看得见的「失去」只是一角，水面下那团才是本体 */}
      <svg className="fig fig-berg" viewBox="0 0 888 760" aria-hidden="true">
        <defs>
          <clipPath id="berg-clip">
            <path d="M138 300 L296 300 L392 452 L348 632 L150 692 L34 500 Z" />
          </clipPath>
          <linearGradient id="berg-light" x1="0" y1="0" x2="1" y2="0">
            <stop
              offset="0"
              stopColor="color-mix(in srgb, var(--a2v-accent-soft-solid) 0%, transparent)"
            />
            <stop
              offset="0.5"
              stopColor="color-mix(in srgb, var(--a2v-accent-soft-solid) 55%, transparent)"
            />
            <stop
              offset="1"
              stopColor="color-mix(in srgb, var(--a2v-accent-soft-solid) 0%, transparent)"
            />
          </linearGradient>
          {/*
            水深的三档：由调色板里「水」的颜色推导，而不是手挑一个蓝。
            兜底值是原来的字面量：未启用预设时逐帧不变。
          */}
          <linearGradient id="berg-depth" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="var(--a2v-berg-depth-1, rgba(45, 78, 120, 0.17))" />
            <stop offset="0.75" stopColor="var(--a2v-berg-depth-2, rgba(45, 78, 120, 0.06))" />
            <stop offset="1" stopColor="var(--a2v-berg-depth-3, rgba(45, 78, 120, 0))" />
          </linearGradient>
        </defs>
        {/*
          第 1 层（最底）：水体。它自己不写 fill——填充由 `.berg-water { fill: url(#berg-depth) }`
          给，水体只有这一个令牌。`opacity` 属性每帧由 `svgO` 推。
        */}
        <rect
          className="berg-water"
          data-el="waterBody"
          x="0"
          y="300"
          width="888"
          height="460"
          opacity={calc.waterOpacity}
        />
        {/* 第 2 层：水面线压在水体之上。描边走 `drawPath`：dasharray/dashoffset 是属性，
            opacity 是内联样式（旧实现就是 `style.opacity`，与 svgO 的属性写法不同） */}
        <path
          className="ln"
          data-el="waterLine"
          d="M0 300 L888 300"
          strokeDasharray={calc.waterLine.strokeDasharray}
          strokeDashoffset={calc.waterLine.strokeDashoffset}
          style={{ opacity: calc.waterLine.opacity }}
        />
        {/* 第 3 层：水面标注（水面之上，故在水体之后） */}
        <text
          className="berg-surface-note"
          data-el="surfaceNote"
          x="24"
          y="274"
          opacity={calc.surfaceNoteOpacity}
        >
          {surfaceNote}
        </text>
        {/* 第 4 层：水上尖端。面取 `--fig-surface`（实心档），与水下主体的 `--fig-water` 不同档 */}
        <path
          className="berg-tip"
          data-el="tip"
          d="M215 64 L138 300 L296 300 Z"
          transform={tip.transform}
          opacity={tip.opacity}
        />
        {/* 第 5 层：水下主体（连同被裁到它轮廓内的光带） */}
        <g data-el="massGroup" transform={calc.mass.transform} opacity={calc.mass.opacity}>
          <path className="berg-mass" d="M138 300 L296 300 L392 452 L348 632 L150 692 L34 500 Z" />
          <g clipPath="url(#berg-clip)">
            <rect
              data-el="lightBand"
              x={calc.lightBand.x}
              y="260"
              width="320"
              height="480"
              fill="url(#berg-light)"
              opacity={calc.lightBand.opacity}
            />
          </g>
        </g>
        {/* 第 6 层：5 颗上浮粒子（半径与初始圆心照抄旧结构，逐帧只改 cx/cy/opacity） */}
        <g data-el="sparks">
          {calc.sparks.map((spark, index) => (
            <circle
              key={index}
              className="berg-spark"
              r="8"
              cx={spark.cx}
              cy={spark.cy}
              opacity={spark.opacity}
            />
          ))}
        </g>
        {/* 第 7 层：三条标注（连线 → 卡片 → 标签 → 说明，顺序即旧 appendChild 的顺序） */}
        <g data-el="callouts">
          {callouts.map((frame) => {
            const geo = bergCalloutGeometry(frame.index);
            // 焦点标注走基元的 `focus` 态：填充定焦点、文字说清是什么（旧实现是 `.is-accent`）
            const focusState = frame.isAccent ? 'focus' : 'rest';
            return (
              <g key={frame.index} data-callout={String(frame.index)}>
                <path
                  className="berg-link a2v-connector"
                  data-a2v-state={focusState}
                  d={geo.linkD}
                  strokeDasharray={frame.link.strokeDasharray}
                  strokeDashoffset={frame.link.strokeDashoffset}
                  style={{ opacity: frame.link.opacity }}
                />
                <rect
                  className="berg-callout a2v-surface"
                  data-a2v-state={focusState}
                  x={geo.boxX}
                  y={geo.y}
                  width={geo.boxW}
                  height={geo.boxH}
                  rx={BERG_CALLOUT_RX}
                  transform={frame.shift}
                  opacity={frame.bodyOpacity}
                />
                <text
                  className="berg-callout-label a2v-label"
                  data-a2v-state={focusState}
                  x={geo.labelX}
                  y={geo.labelY}
                  transform={frame.shift}
                  opacity={frame.bodyOpacity}
                >
                  {frame.label}
                </text>
                <text
                  className="berg-callout-desc"
                  x={geo.descX}
                  y={geo.descY}
                  transform={frame.shift}
                  opacity={frame.descOpacity}
                >
                  {frame.desc}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </>
  );
};
