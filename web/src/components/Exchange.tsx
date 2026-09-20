/**
 * 结论幕：双向关系——两个端点互相选择。
 *
 * 逐行对应旧组件库 `assets/figures.js` 的：
 *   - `updateExchange`（第 1554–1629 行，含它用的 `fitFontSize` 第 1518–1553 行与 `EXCHANGE` 常量第 1502 行）
 *   - `MARKUP_EXCHANGE`（第 1649–1665 行）
 *   - `placeArrow`（第 1631–1646 行）
 *   - 逐字揭示 `revealKeyChars`（第 1678–1717 行）与它用的 `splitEmphasis`（第 1719–1740 行）
 *
 * 迁移时**只换写法，不换数学**：每个表达式都照原样搬过来，后面要按帧做
 * 逐像素 PSNR 对照，任何"顺手化简"都会变成一片像素差。
 *
 * 三类写法差异，都是 React 决定的，改的不是画面：
 *
 * 1. **逐字揭示不再操作 DOM**。旧实现每帧 `querySelectorAll('.reveal-char')` 再逐个
 *    写 `style.opacity`，靠隐藏属性 `data-a2v-emphasis-text`（内容签名）判断要不要
 *    重建节点树。这里改成 `revealUnits()` 这个纯函数给出「每个字这一帧的不透明度」，
 *    由 React 渲染。因此**不照抄 `data-a2v-emphasis-text`**：那个属性的唯一用途是
 *    「内容没变就别重建 DOM」，而 React 按 key 复用节点，节点身份由 React 管；
 *    再挂一个签名属性等于同一件事有两处真源，还会被抽帧对照算成一个多余属性。
 * 2. **`fontSize` 的两条分支都在**（未启用预设时按字符数自算、启用预设时从字号阶挑档），
 *    分支顺序与原实现一致，见 `exchangeFitFontSize`。
 * 3. **旧实现一帧都没变过的量改成"挂载后量一次"**（箭镞几何），见 `useArrowGeometry`。
 *
 * 禁用的东西照旧：没有 CSS 动画 / transition / 定时器 / 随机数 / 跨帧可变状态，
 * 画面只由 `localFrame` 与分镜数据推导。
 */
import { useCallback, useLayoutEffect, useState, type CSSProperties, type FC } from 'react';

import {
  EASE,
  beat,
  enterSvgAttrs,
  plainText,
  revealUnits,
  sinceBeat,
  svgOpacity,
  svgTransform,
  useFigure,
  type FigureRuntime,
} from '@/runtime/figures';
// `idle` 是常驻微动的唯一真源（旧实现走 `motion.idle`）：周期与振幅都写在动效层，
// 组件只说"我要 3px 的呼吸"，不自己写一遍正弦。
import { idle, springBy } from '@/runtime/motion';

/* ============================ 几何与常量 ============================ */

/** exchange 的字号规则参数，逐值照抄旧实现的 `EXCHANGE`（第 1502 行）。 */
export const EXCHANGE = {
  WIDTH: 888,
  MAX: 96,
  MIN: 54,
  TOP: 'headline',
  FLOOR: 'body',
} as const;

/**
 * 启用预设时挑选字号档位用的字号阶（旧实现读 `window.A2V.type.levels`）。
 *
 * 数值与工程里那一份阶一致，顺序**从大到小**——旧实现的挑选循环依赖这个顺序。
 * 这里不 import `typography.ts`：那一份是"实测驱动"的排版引擎，而 `fitFontSize`
 * 的这段路径要的是"按字符数估"的旧算法，两者不能混（混了就等于改了排版结果）。
 *
 * 未启用预设时这份表根本不参与计算：那条路径逐帧不变的承诺由自算分支保证。
 */
const LEGACY_TYPE_LEVELS: ReadonlyArray<{ name: string; size: number }> = [
  { name: 'display', size: 120 },
  { name: 'headline', size: 96 },
  { name: 'title', size: 76 },
  { name: 'subtitle', size: 60 },
  { name: 'value', size: 44 },
  { name: 'body', size: 40 },
];

/**
 * 字号：按**最长一行**算能放下的字号（第 1518–1553 行）。
 *
 * 用字符数而不是实测宽度：中日韩字形宽度≈字号，而实测既拖慢逐帧渲染，
 * 也会把布局抖动带进画面（这就是这一幕不走 `typography.js` 那套实测自适应的原因）。
 */
export function exchangeFitFontSize(
  text: unknown,
  options: {
    preset?: string | undefined;
    levels?: ReadonlyArray<{ name: string; size: number }>;
  } = {},
): number {
  const lines = plainText(text).split('\n');
  let longest = 1;
  for (const line of lines) {
    if (line.length > longest) {
      longest = line.length;
    }
  }
  const heuristic = Math.max(
    EXCHANGE.MIN,
    Math.min(EXCHANGE.MAX, Math.floor(EXCHANGE.WIDTH / longest)),
  );

  if (options.preset !== 'keynote') {
    return heuristic;
  }
  const levels = options.levels?.length ? options.levels : LEGACY_TYPE_LEVELS;
  // 阶按从大到小排列；取第一个「最长行乘字号仍放得下」的档位
  let top = 0;
  let floor = levels.length - 1;
  for (let i = 0; i < levels.length; i += 1) {
    const level = levels[i]!;
    if (level.name === EXCHANGE.TOP) {
      top = i;
    }
    if (level.name === EXCHANGE.FLOOR) {
      floor = i;
    }
  }
  for (let i = top; i <= floor; i += 1) {
    const level = levels[i]!;
    if (level.size * longest <= EXCHANGE.WIDTH) {
      return level.size;
    }
  }
  // 连最下一档也放不下：仍取该档，溢出交给 K8 溢出闸门报出来
  return levels[floor]!.size;
}

/**
 * 弧线描边长度：旧的 `api.drawPath(arcTo, p, { length: 392 })` 写的是这个显式值
 * （第 1594–1595 行），不是实测路径长度。移植后同样显式给出——
 * `drawPathStyle` 不做测量，长度由调用方给。
 *
 * 数值核对过：两条二次贝塞尔的实际长度约 370.87 / 366.92，都小于 392，
 * 因此进度走到 1 时整条弧线已经画满。
 */
export const EXCHANGE_ARC_LENGTH = 392;

/** 这一幕的几何：`MARKUP_EXCHANGE` 里的全部坐标（第 1651–1664 行），一字不改。 */
export interface ExchangeGeometry {
  /** 左端点圆 */
  left: { cx: number; cy: number; r: number };
  /** 右端点圆 */
  right: { cx: number; cy: number; r: number };
  /** 去程弧（左下 → 右上）：起点、控制点、终点 */
  arcTo: { from: [number, number]; control: [number, number]; to: [number, number] };
  /** 回程弧（右上 → 左下） */
  arcBack: { from: [number, number]; control: [number, number]; to: [number, number] };
}

/**
 * 为什么把坐标收成一处常量：箭头的位置与朝向**必须由同一组常量算出来**。
 * 旧实现的注释写着「硬编码角度会在改曲线端点时静默错位」，因此这里让弧的端点与控制点
 * 成为唯一真源，`<path d>` 与切线角都由它们推导。
 */
export const EXCHANGE_GEOMETRY: ExchangeGeometry = {
  left: { cx: 150, cy: 150, r: 88 },
  right: { cx: 738, cy: 150, r: 88 },
  arcTo: { from: [262, 118], control: [445, 66], to: [628, 118] },
  arcBack: { from: [626, 182], control: [445, 234], to: [264, 182] },
};

/** 端点的圆心与半径：左 150/150/88、右 738/150/88。 */
export const EXCHANGE_NODES = {
  left: { ...EXCHANGE_GEOMETRY.left },
  right: { ...EXCHANGE_GEOMETRY.right },
} as const;

/** 端点标注的键：`labels.leftNode` / `labels.rightNode`（`define('exchange', [...])`，第 1667 行）。 */
export const EXCHANGE_LABEL_KEYS = ['leftNode', 'rightNode'] as const;

/** 二次贝塞尔 `d` 串：与 `MARKUP_EXCHANGE` 里写的格式逐字符一致。 */
export function quadraticPathData(
  from: readonly [number, number],
  control: readonly [number, number],
  to: readonly [number, number],
): string {
  return `M${from[0]} ${from[1]} Q${control[0]} ${control[1]} ${to[0]} ${to[1]}`;
}

/**
 * 弧线末端的切线方向（角度制）。二次贝塞尔在终点的切向是「终点 − 控制点」，
 * 与旧实现第 1600 / 1602 行的 `Math.atan2(终点.y − 控制点.y, 终点.x − 控制点.x) *
 * 180 / Math.PI` 是同一个式子。
 */
export function arcTangentDegrees(arc: {
  control: readonly [number, number];
  to: readonly [number, number];
}): number {
  return (Math.atan2(arc.to[1] - arc.control[1], arc.to[0] - arc.control[0]) * 180) / Math.PI;
}

/**
 * 箭镞尺寸的兜底值。旧实现从设计令牌读（`--fig-arrow-len` / `--fig-arrow-half`，
 * `tokenPx()` 第 270–276 行），取不到或不是正数就用这两个数（34 / 16）——
 * 而这两个数正是 `tokens.css` 里那两个令牌的取值，因此兜底路径与预设路径在当前
 * 设计语言下逐像素相同。
 */
export const EXCHANGE_ARROW_FALLBACK = { length: 34, half: 16 } as const;

/** 箭镞三角的 `d`：旧实现 `placeArrow()` 里拼的那一串（第 1642–1644 行）。 */
export function arrowPathData(length: number, half: number): string {
  return `M0 0 L-${length} -${half} L-${length} ${half} Z`;
}

/** 读一个自定义属性的像素值；取不到、非数或非正就用兜底值（照抄 `tokenPx`）。 */
export function readTokenPx(
  element: Element | null,
  name: string,
  fallback: number,
  computed?: (el: Element, property: string) => string,
): number {
  if (!element) {
    return fallback;
  }
  /*
   * 平台依赖只在这一处：没有 `window`（例如 node 环境）时回落兜底值，
   * 与旧实现 `tokenPx` 的判据一致。调用方显式传了读数函数时就用它——
   * 那表示平台由调用方负责，函数本身因此可以在没有浏览器的环境里被验证。
   */
  const read =
    computed ??
    (typeof window !== 'undefined' && window.getComputedStyle
      ? (el: Element, property: string) => window.getComputedStyle(el).getPropertyValue(property)
      : null);
  if (!read) {
    return fallback;
  }
  const parsed = parseFloat(read(element, name));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

/**
 * 箭镞尺寸在挂载后量一次。
 *
 * 为什么不写死：设计层改档位时画面要跟着走，"几何只有一处真源"是这一层的规矩；
 * 为什么量一次就够：这两个令牌与第几帧无关，因此「同一帧同一画面」不受影响——
 * 这与运行时 `useFit` 的取舍是同一条（`useLayoutEffect` 只在依赖变化时重量）。
 */
function useArrowGeometry(): {
  length: number;
  half: number;
  attach: (element: Element | null) => void;
} {
  const [attached, setAttached] = useState(0);
  const [element, setElement] = useState<Element | null>(null);
  // 类型写开：`as const` 的兜底值会把 state 钉成字面量 34/16，令牌读出别的值就赋不进去
  const [size, setSize] = useState<{ length: number; half: number }>({
    ...EXCHANGE_ARROW_FALLBACK,
  });

  useLayoutEffect(() => {
    if (!element) {
      return;
    }
    const next = {
      length: readTokenPx(element, '--fig-arrow-len', EXCHANGE_ARROW_FALLBACK.length),
      half: readTokenPx(element, '--fig-arrow-half', EXCHANGE_ARROW_FALLBACK.half),
    };
    // 只在真变了时更新：逐帧重建对象会让 React 每帧都重渲染整棵子树
    setSize((previous) =>
      previous.length === next.length && previous.half === next.half ? previous : next,
    );
  }, [element, attached]);

  return {
    length: size.length,
    half: size.half,
    /*
     * 回调 ref 必须**身份稳定**：React 只在 ref 身份变化时才重新挂载它，
     * 而这里每渲染一次就新建一个箭头函数的话，React 会卸载再挂载 → `setAttached`
     * → 又渲染一次 → 无限循环（React #185：Maximum update depth exceeded）。
     * `Loop.tsx` 里 `attachText` 用的是同一条取舍。
     */
    attach: useCallback((el: Element | null) => {
      setElement(el);
      setAttached((count) => count + 1);
    }, []),
  };
}

/* ============================ 逐字揭示的接线 ============================ */

/** 逐字揭示的起始比例点与步进帧数：`beat(state, 0.02)`、`staggerFrames: 2`（第 1574–1575 行）。 */
export const EXCHANGE_REVEAL_BEAT = 0.02;
export const EXCHANGE_REVEAL_STAGGER_FRAMES = 2;

/**
 * 这一幕这一帧的逐字节点树。
 *
 * 强调片段比正文晚 6 帧出现这条规则**已经写在 `revealUnits` 里**
 * （`REVEAL_KEY_DELAY_FRAMES`），这里不再算一遍——两处各算一次，
 * 早晚会有一处先被改掉。
 */
export function exchangeRevealUnits(
  runtime: FigureRuntime,
  text: unknown,
  phrases: readonly string[] | undefined,
): ReturnType<typeof revealUnits> {
  return revealUnits(plainText(text), phrases, {
    frame: runtime.state.localFrame,
    startFrame: beat(runtime, EXCHANGE_REVEAL_BEAT),
    staggerFrames: EXCHANGE_REVEAL_STAGGER_FRAMES,
  });
}

/* ============================ 组件 ============================ */

export const ExchangeFigure: FC = () => {
  const fig = useFigure();
  const { localFrame } = fig.state;
  const data = fig.data;
  const labels = fig.spec.labels;

  const text = plainText(data['text']);
  const emphasisList = data['emphasis'];
  const emphasis = Array.isArray(emphasisList)
    ? emphasisList.filter((phrase): phrase is string => typeof phrase === 'string')
    : undefined;
  const actionText = plainText(data['action']);

  const arrow = useArrowGeometry();

  /*
   * 字号走行内样式，与旧实现的 `text.style.fontSize = fitFontSize(...) + 'px'` 等价。
   * `data-a2v-fit` 照旧**不挂**：这一幕走的是"按字符数算字号"的老路，
   * 挂上取档锚点就会让取档引擎接管排版，字号不再与旧渲染逐像素相同。
   */
  const fontSize = exchangeFitFontSize(text, { preset: fig.preset });
  const units = exchangeRevealUnits(fig, text, emphasis);

  /*
   * 高亮交给**第一个强调片段**：旧实现是 `text.querySelector('.key')`，
   * 而 `.key` 正是 `splitEmphasis` 标出来的那一段。找不到强调词就没有 `.key` 节点，
   * 也就没有光晕——这一条与旧实现一致。
   */
  const keyUnitIndex = units.findIndex((unit) => unit.key);
  const highlight = fig.api.progress(
    localFrame,
    beat(fig, 0.56),
    beat(fig, 0.1),
    EASE.symmetric,
  );
  /*
   * 旧实现分两支：启用预设时写 `--a2v-emphasis-glow`（光晕的模糊与浓度由设计语言层给），
   * 未启用时写行内 `text-shadow`（第 1607–1618 行）。这里**只保留变量那一支**：
   * 行内 text-shadow 的优先级最高，会把 `figures.css` 里
   * `[data-a2v-preset='keynote'] .key` 那条规则整个盖掉，而两条分支在未启用预设时的
   * 差异（30px/0.24 对 26px/0.22）正是设计层已经收成一档的那两档。
   * 这是本次迁移唯一的画面近似，已记在交付说明里。
   */
  const keyStyle =
    keyUnitIndex >= 0
      ? ({ '--a2v-emphasis-glow': highlight.toFixed(4) } as CSSProperties)
      : undefined;

  /*
   * 双向弧线：两条弧用同一个显式长度 392、同一条 `outCubic`，只是起点与时长不同
   * （第 1594–1595 行）。
   */
  const arcToStyle = fig.api.drawPath(
    fig.api.progress(localFrame, beat(fig, 0.36), beat(fig, 0.1), EASE.soft),
    EXCHANGE_ARC_LENGTH,
  );
  const arcBackStyle = fig.api.drawPath(
    fig.api.progress(localFrame, beat(fig, 0.44), beat(fig, 0.1), EASE.soft),
    EXCHANGE_ARC_LENGTH,
  );

  // 箭镞：位置与朝向由弧的端点/控制点算出（`placeArrow`），出现进度吃 `outQuint`
  const arrowToAngle = arcTangentDegrees(EXCHANGE_GEOMETRY.arcTo);
  const arrowBackAngle = arcTangentDegrees(EXCHANGE_GEOMETRY.arcBack);
  const arrowToTransform = svgTransform(
    EXCHANGE_GEOMETRY.arcTo.to[0],
    EXCHANGE_GEOMETRY.arcTo.to[1],
    arrowToAngle,
  );
  const arrowBackTransform = svgTransform(
    EXCHANGE_GEOMETRY.arcBack.to[0],
    EXCHANGE_GEOMETRY.arcBack.to[1],
    arrowBackAngle,
  );
  const arrowToOpacity = fig.api.progress(localFrame, beat(fig, 0.46), 14, EASE.out);
  const arrowBackOpacity = fig.api.progress(localFrame, beat(fig, 0.54), 14, EASE.out);
  const arrowData = arrowPathData(arrow.length, arrow.half);

  /*
   * 行动句：位移吃**弹簧的线性秒数**，横向微动是 `idle(f, { amplitude: 3 })` 乘上一个
   * 对称缓动的门控，不透明度吃 28 帧的 `outQuint`（第 1620–1628 行）。
   * 三个量各取所需，最后合成同一个 transform 串。
   *
   * 弹簧必须按**名字**取：旧实现写的是 `motion.spring(actionSeconds, 'enter')`，
   * 而旧运行时的 `motion.spring` 是 `springBy`——第二个参数是档位名，
   * 映射到 `SPRINGS.enter`（response 0.5 / ζ 1，临界阻尼）。
   * 写成不带名字的 `spring(seconds)` 会落到默认档 firm（0.44 / 0.9）：
   * 曲线前段差得不多，但第 150 帧实测位移 22.68px vs 24.95px，跨路径比对直接掉到 45 dB。
   */
  const actionShift = fig.api.range(
    springBy(fig.api.since(localFrame, beat(fig, 0.64)), 'enter'),
    34,
    0,
    { clamp: false },
  );
  const actionDrift =
    idle(localFrame, { amplitude: 3 }) *
    fig.api.progress(localFrame, beat(fig, 0.64), 40, EASE.symmetric);
  const actionProgress = fig.api.progress(localFrame, beat(fig, 0.64), 28, EASE.out);
  const actionStyle: CSSProperties = {
    transform: `translate3d(${actionShift.toFixed(2)}px,${actionDrift.toFixed(2)}px,0)`,
    opacity: String(fig.api.clamp(actionProgress, 0, 1)),
  };

  return (
    <>
      <p className="closing-text" data-el="text" style={{ fontSize: `${fontSize}px` }}>
        {units.map((unit, unitIndex) => (
          <span
            key={`${unit.key ? 'key' : 'plain'}-${unitIndex}`}
            className={unit.key ? 'key' : 'plain'}
            style={unitIndex === keyUnitIndex ? keyStyle : undefined}
          >
            {/*
              单字节点：换行符占位但不可见（`.reveal-char.is-break`），并且**不参与计数**——
              序号只随可见字前进，这一条由 `revealUnits` 保证，这里不再自己数一遍。
            */}
            {unit.chars.map((item, charIndex) => (
              <span
                key={charIndex}
                className={item.isBreak ? 'reveal-char is-break' : 'reveal-char'}
                style={{ opacity: String(item.opacity) }}
              >
                {item.char}
              </span>
            ))}
          </span>
        ))}
      </p>

      {/*
        双向箭头：挑人不是单向的。`viewBox` / `width` / `height` 与每个 `<path>` 的 `d`
        逐字符照抄 `MARKUP_EXCHANGE`（第 1651–1664 行）；只有箭镞的 `d` 从标记里的占位
        `M0 0 L0 0` 换成按帧算出的三角——旧实现同样每帧重写它（`placeArrow`）。
        `class` / `data-el` / `data-a2v-state` 一个都没动。
      */}
      <svg
        className="fig fig-exchange"
        viewBox="0 0 888 300"
        aria-hidden="true"
        ref={arrow.attach}
      >
        <g
          data-el="nodeLeft"
          {...enterSvgAttrs(fig, sinceBeat(fig, 0.2), {
            distance: 34,
            amplitude: 2.5,
            axis: 'x',
            scale: 0.94,
          })}
        >
          <circle
            className="ex-node-disc a2v-connector"
            data-a2v-state="rest"
            cx={EXCHANGE_GEOMETRY.left.cx}
            cy={EXCHANGE_GEOMETRY.left.cy}
            r={EXCHANGE_GEOMETRY.left.r}
          />
          <text
            className="ex-node-text"
            data-el="nodeLeftText"
            x={EXCHANGE_GEOMETRY.left.cx}
            y={EXCHANGE_GEOMETRY.left.cy}
          >
            {plainText(labels['leftNode'])}
          </text>
        </g>
        <g
          data-el="nodeRight"
          {...enterSvgAttrs(fig, sinceBeat(fig, 0.26), {
            distance: -34,
            amplitude: 2.5,
            axis: 'x',
            scale: 0.94,
          })}
        >
          <circle
            className="ex-node-disc a2v-connector"
            data-a2v-state="focus"
            cx={EXCHANGE_GEOMETRY.right.cx}
            cy={EXCHANGE_GEOMETRY.right.cy}
            r={EXCHANGE_GEOMETRY.right.r}
          />
          <text
            className="ex-node-text"
            data-el="nodeRightText"
            x={EXCHANGE_GEOMETRY.right.cx}
            y={EXCHANGE_GEOMETRY.right.cy}
          >
            {plainText(labels['rightNode'])}
          </text>
        </g>
        <path
          className="ex-arc a2v-connector"
          data-a2v-state="rest"
          data-el="arcTo"
          d={quadraticPathData(
            EXCHANGE_GEOMETRY.arcTo.from,
            EXCHANGE_GEOMETRY.arcTo.control,
            EXCHANGE_GEOMETRY.arcTo.to,
          )}
          data-a2v-length={EXCHANGE_ARC_LENGTH}
          strokeDasharray={arcToStyle.strokeDasharray}
          strokeDashoffset={arcToStyle.strokeDashoffset}
          style={{ opacity: arcToStyle.opacity }}
        />
        <path
          className="ex-arrow a2v-connector"
          data-a2v-state="rest"
          data-el="arrowTo"
          d={arrowData}
          transform={arrowToTransform}
          style={{ opacity: svgOpacity(arrowToOpacity) }}
        />
        <path
          className="ex-arc a2v-connector"
          data-a2v-state="focus"
          data-el="arcBack"
          d={quadraticPathData(
            EXCHANGE_GEOMETRY.arcBack.from,
            EXCHANGE_GEOMETRY.arcBack.control,
            EXCHANGE_GEOMETRY.arcBack.to,
          )}
          data-a2v-length={EXCHANGE_ARC_LENGTH}
          strokeDasharray={arcBackStyle.strokeDasharray}
          strokeDashoffset={arcBackStyle.strokeDashoffset}
          style={{ opacity: arcBackStyle.opacity }}
        />
        <path
          className="ex-arrow a2v-connector"
          data-a2v-state="focus"
          data-el="arrowBack"
          d={arrowData}
          transform={arrowBackTransform}
          style={{ opacity: svgOpacity(arrowBackOpacity) }}
        />
      </svg>

      {/*
        行动句。旧实现是「没有 action 就 `display: none`」；React 里直接不渲染——
        少一个节点与隐藏一个节点在画面上是同一件事，而条件渲染让"空数据不画东西"
        成为结构上的事实，不必再靠一个内联 `display` 兜底。
        `data-a2v-fit="body"` 照抄旧标记（锚点一字不改）。
      */}
      {actionText ? (
        <p className="closing-action" data-el="action" data-a2v-fit="body" style={actionStyle}>
          {actionText}
        </p>
      ) : null}
    </>
  );
};
