/**
 * 落差尺幕：量出「真正失去了多少」——一侧从满到空，另一侧从头就没有。
 *
 * 逐行对应旧组件库 `assets/figures.js` 的：
 *   - `updateGap`（旧文件第 570–644 行）
 *   - `placeBracket`（第 689–704 行）与 `applyDrop`（第 678–682 行）
 *   - `emphasizeKey`（第 652–675 行，本幕用的是它的缺省档 `at: 0.7` / `span: 0.1`）
 *   - `MARKUP_GAP`（第 707–742 行）
 *
 * 与旧实现的差别只有一处，而且是 React 决定的：旧版每帧把算出来的值**写进 DOM**
 * （`el.style.height = …`、`key.style.setProperty(…)`），这里每帧**算出样式交给 React**。
 * 数学一个表达式都没动，因此同一帧算出来的数值与旧路径逐位相同（抽帧对照要的就是这个）；
 * 落在节点上的强调行内值（下划线 `scaleX`、`--a2v-emphasis-glow` / `text-shadow`）
 * 由运行时的 `emphasisHtml` 拼进标记，组件自己不碰 DOM、也不写容器级权宜值。
 *
 * 三条必须守住的细节，改动时最容易踩：
 *
 * 1. **左边柱子的高度是 `ownP * (1 - dropP)`**，有「拥有 → 被拿走」两段，
 *    结尾归零是设计，不是漏画；虚线（ghost）留在 `ownP` 的高度上，差值才是「失去」；
 * 2. **右边柱子恒为 0**，虚线也为 0；它的括号被压成贴着 0 线的一段（`flat`），
 *    这样「失去全部」和「无可失去」在同一把尺上可以直接比长度；
 * 3. **入场吃的是线性秒数**（`sinceBeat`），不是缓动过的进度：弹簧自己就是曲线。
 */
import type { FC } from 'react';

import type { EasingName } from '@/runtime/motion';

import {
  EASE,
  beat,
  emphasisHtml,
  emphasisProps,
  enterStyle,
  plainText,
  sinceBeat,
  useFigure,
  useFit,
} from '@/runtime/figures';

/* ---------------- 照搬的常量（旧 figures.js 第 562 行） ---------------- */

/** 竖尺的像素高度。柱子、虚线、括号的 top/height 全部由它乘出来。 */
export const TRACK_H = 268;

/** 「本来就没有」那一侧括号被压平后的高度（旧 placeBracket 里写死的 6）。 */
export const BRACKET_FLAT_H = 6;

/** 落差标签的顶端可落区间（旧 placeBracket 里写死的 44 / 268 - 16）。 */
export const LABEL_TOP_MIN = 44;
export const LABEL_TOP_MAX = TRACK_H - 16;

/* ---------------- 纯计算：与旧实现逐个表达式对照 ---------------- */

/** 纯计算需要的运行时输入；与 `fig.state` 同形，便于直接传入。 */
export interface GapMotionState {
  localFrame: number;
  sceneDurationFrames: number;
  motion?: string;
}

/** 本幕用到的进度/秒数原语；由组件的 `fig.api` 或测试的桩实现提供。 */
export interface GapCalcApi {
  /**
   * = `api.progress(frame, startFrame, duration, easing)`，返回 0..1。
   *
   * 缓动名照 `EasingName` 收窄而不是 `string`：`fig.api` 的类型是后者，
   * 因此组件里不用做任何转换就能直接把运行时交给纯计算。
   */
  progress: (frame: number, start: number, duration: number, easing?: EasingName) => number;
  /** = `api.since(frame, startFrame)`，返回秒数 */
  since: (frame: number, startFrame?: number) => number;
}

/**
 * 数值兜底：非有限值（空数据 / 缺字段）按 0 处理。
 *
 * 旧实现没有这一步：`clampStatic(NaN, 0, 1)` 会原样返回 NaN，写进 CSS 之后
 * 浏览器整条声明失效、元素保持样式表里的初值。两者在「空数据」这一支上得到同一画面，
 * 而这里把 NaN 归一成 0 之后，**同一个纯函数才有确定输出**（可以写测试断言）。
 */
function finite(value: unknown): number {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

function clampRange(value: number, min: number, max: number): number {
  return value < min ? min : value > max ? max : value;
}

/**
 * 竖尺填充高度（旧 `applyDrop` 的表达式）：
 * `(clamp(ratio, 0, 1) * TRACK_H).toFixed(1) + 'px'`。
 *
 * 保留一位小数再给 CSS：旧实现写的是那个字符串，四舍五入发生在写 DOM 之前，
 * 因此这里必须返回**字符串**，不能返回数字让浏览器自己格式化。
 */
export function dropHeight(ratio: unknown): string {
  return (clampRange(finite(ratio), 0, 1) * TRACK_H).toFixed(1);
}

/** 落差标签的 left/width 与括号几何来自样式表，这里只算 top 与 height。 */
export interface BracketPlacement {
  /** 括号顶端的 `top`（px 字符串，一位小数） */
  top: string;
  /** 括号高度（px 字符串，一位小数） */
  height: string;
  /** 标签顶端（px 字符串，一位小数） */
  labelTop: string;
}

/**
 * 落差括号的位置（旧 `placeBracket`，第 689–704 行）。
 *
 * `flat` 为真时（本来就没有）忽略传入的两个比例，压成 `[TRACK_H - 6, TRACK_H]`
 * 这一小段：它量的是「无可失去」，而不是「损失为 0」。
 * 标签的落点在 flat 时取 TRACK_H（贴 0 线），否则取括号中点；
 * 两种落点都钳进 `[44, TRACK_H - 16]`，避免压到尺外或压到读不出来的位置。
 */
export function bracketPlacement(
  fillRatio: unknown,
  gapRatio: unknown,
  flat: boolean,
): BracketPlacement {
  let top = clampRange(finite(fillRatio), 0, 1) * TRACK_H;
  let height = clampRange(finite(gapRatio), 0, 1) * TRACK_H;
  if (flat) {
    top = TRACK_H - BRACKET_FLAT_H;
    height = BRACKET_FLAT_H;
  }
  const center = flat ? TRACK_H : top + height / 2;
  return {
    top: top.toFixed(1),
    height: height.toFixed(1),
    labelTop: (clampRange(center, LABEL_TOP_MIN, LABEL_TOP_MAX) - 20).toFixed(1),
  };
}

/** 一帧里本幕所有由帧号推出的数值。每个字段都对应旧 updateGap 里的一个表达式。 */
export interface GapFrameCalc {
  /** `api.progress(f, 0, 20, EASE_OUT)`：左侧竖线的生长 */
  ruleP: number;
  /** `api.progress(f, beat(0.02), 24, EASE_OUT)`：引号的不透明度（再乘 0.14） */
  markP: number;
  /** `api.range(markP, -26, 0).toFixed(1)`：引号的下沉位移 */
  markShift: string;
  /** `api.progress(f, beat(0.26), beat(0.09), EASE_OUT)` */
  ownP: number;
  /** `api.progress(f, beat(0.38), beat(0.08), EASE_SYMMETRIC)` */
  dropP: number;
  /** `ownP * (1 - dropP)`：左柱当前高度比 */
  aFill: number;
  /** `ownP`：左柱虚线（曾经有多少）的高度比 */
  aGhost: number;
  /** `api.progress(f, beat(0.48), beat(0.1), EASE_SYMMETRIC)` */
  gapP: number;
  /** `api.progress(f, beat(0.56), beat(0.1), EASE_SYMMETRIC)` */
  flatP: number;
  /** `api.progress(f, beat(0.54), beat(0.14), EASE_SYMMETRIC)`：左栏淡出为「假设」 */
  fadeP: number;
  /** `1 - fadeP * 0.55`：左栏最终不透明度 */
  panelAOpacity: number;
  /** 左括号：`placeBracket(…, aFill, (aGhost - aFill) * gapP, false)` */
  bracketA: BracketPlacement;
  /** 左柱填充高度 */
  fillAHeight: string;
  /** 左柱虚线高度 */
  ghostAHeight: string;
  /** 右括号：`placeBracket(bracketB, labelB, 0, flatP * 0.012, true)` */
  bracketB: BracketPlacement;
  /** 右柱填充高度（恒为 0，写出来是为了让「本来就空」在代码里可见） */
  fillBHeight: string;
  /** 右柱虚线高度（恒为 0） */
  ghostBHeight: string;
  /** 右括号与右标签的不透明度 `flatP` */
  flatOpacity: number;
}

/**
 * 本幕一帧的纯计算：**输入相同，输出必然相同**。
 *
 * `beat` 用 `motionBeat` 的公式就地展开（`fraction * 幕长 / 节奏倍率`）这件事
 * 交给调用方传进来的 `beatAt`——它是运行时的 `beat(fig, …)`，本函数不自己推导，
 * 免得出现第二份节拍定义。
 */
export function gapFrame(
  state: GapMotionState,
  api: GapCalcApi,
  beatAt: (fraction: number) => number,
): GapFrameCalc {
  const f = state.localFrame;

  // 左侧竖线：0→20 帧长出，与文案无关，因此不随节奏缩放
  const ruleP = api.progress(f, 0, 20, EASE.out);
  // 引号：起于 beat(0.02)，24 帧；不透明度只有 0.14——它是装饰，不是内容
  const markP = api.progress(f, beatAt(0.02), 24, EASE.out);

  // 左边：拥有 → 被拿走 → 落差拉满。两段各自缓动，柱高是两者的乘积
  const ownP = api.progress(f, beatAt(0.26), beatAt(0.09), EASE.out);
  const dropP = api.progress(f, beatAt(0.38), beatAt(0.08), EASE.symmetric);
  const aFill = ownP * (1 - dropP);
  const aGhost = ownP;

  // 落差括号在第 0.48 拍开始量：从「现在还剩多少」量到「曾经有多少」
  const gapP = api.progress(f, beatAt(0.48), beatAt(0.1), EASE.symmetric);
  // 右边：本来就没有。平括号只长 1.2% 的尺高，读起来是「没有落差」而不是「落差很小」
  const flatP = api.progress(f, beatAt(0.56), beatAt(0.1), EASE.symmetric);
  // 左边淡出为「假设」：它只是观众脑内的剧本，最多褪到 0.45，不完全消失
  const fadeP = api.progress(f, beatAt(0.54), beatAt(0.14), EASE.symmetric);

  return {
    ruleP,
    markP,
    // 旧实现是 `api.range(markP, -26, 0).toFixed(1)`，即 -26 + 26·markP：
    // 引号从下方 26px 处升到位。写成 `markP * -26` 会让它**停在下沉位置**，
    // 到位后一直歪着（实测第 500 帧差 26px）。
    markShift: (-26 + 26 * markP).toFixed(1),
    ownP,
    dropP,
    aFill,
    aGhost,
    gapP,
    flatP,
    fadeP,
    panelAOpacity: 1 - fadeP * 0.55,
    bracketA: bracketPlacement(aFill, (aGhost - aFill) * gapP, false),
    fillAHeight: dropHeight(aFill),
    ghostAHeight: dropHeight(aGhost),
    bracketB: bracketPlacement(0, flatP * 0.012, true),
    fillBHeight: dropHeight(0),
    ghostBHeight: dropHeight(0),
    flatOpacity: flatP,
  };
}

/**
 * 关键短语的强调进度（旧 `emphasizeKey`，本幕走缺省档 `at 0.7 / span 0.1`）。
 *
 * 与旧实现同一个表达式：`api.progress(f, beat(state, at), beat(state, span), EASE_SYMMETRIC)`。
 */
export function emphasisProgress(
  state: GapMotionState,
  api: GapCalcApi,
  beatAt: (fraction: number) => number,
  options: { at?: number; span?: number } = {},
): number {
  const at = options.at === undefined ? 0.7 : options.at;
  const span = options.span === undefined ? 0.1 : options.span;
  return api.progress(state.localFrame, beatAt(at), beatAt(span), EASE.symmetric);
}

/** 分镜注入的文案：全部来自 `data` 与 `labels`，组件不存默认值。 */
export interface GapText {
  /** 主文案原文（未加标记），交给 `gapEmphasisHtml` 拼强调节点 */
  text: unknown;
  /** 重点短语列表（分镜的 `emphasis`），原样交给运行时的强调实现 */
  phrases: unknown;
  capA: string;
  capB: string;
  labelA: string;
  labelB: string;
}

/**
 * 文案的纯计算：把 `data` / `labels` 翻成主文案与四个短标注。
 *
 * 这里**不再自己拼 HTML**：标记与行内样式都由运行时的 `emphasisHtml` 一处负责，
 * 组件多拼一份就会与别的幕漂移（下划线有没有、光晕写在哪一层都可能不一致）。
 * `underline` 恒为 true（旧 updateGap 的 `setText(text, data.text, data.emphasis, true)`）。
 */
export function gapText(
  data: Record<string, unknown> | undefined,
  labels: Record<string, string> | undefined,
): GapText {
  const source = data ?? {};
  const ann = labels ?? {};
  return {
    text: source['text'],
    phrases: source['emphasis'],
    capA: plainText(ann['assumption']),
    capB: plainText(ann['fact']),
    labelA: plainText(ann['dropLabel']),
    labelB: plainText(ann['noDropLabel']),
  };
}

/** `gapEmphasisHtml` 的入参：强调进度 + 由谁写光晕 + 插值函数。 */
export interface GapEmphasisOptions {
  /** 由 `emphasisProgress` 算出的 0..1 */
  progress: number;
  /** 设计语言预设是否生效（`fig.preset` 有值即生效） */
  preset: boolean;
  /** `fig.api.range`：非预设下把进度映到模糊半径与浓度 */
  range: (value: number, from: number, to: number) => number;
}

/**
 * 主文案的完整 HTML：强调标记 + 行内样式（旧 `emphasize` + `emphasizeKey` 的合体）。
 *
 * 三件事都落在节点上，而不是落在容器上——这是旧实现的语义，也是这次补通道的原因：
 * 下划线的 `transform: scaleX(p)` 是连续量，样式表里没有它；预设下写
 * `--a2v-emphasis-glow`（模糊与浓度交给设计语言层）；非预设下才写行内 `text-shadow`。
 * 挂到容器上时前两者都不会生效——下划线节点读的是**自己**的 transform，
 * 光晕规则也写在 `.key` 上。
 */
export function gapEmphasisHtml(text: GapText, options: GapEmphasisOptions): string {
  return emphasisHtml(text.text, text.phrases, {
    underline: true,
    progress: options.progress,
    preset: options.preset,
    range: options.range,
  });
}

/* ---------------- 组件 ---------------- */

/**
 * 幕的画面结构：文案元素留空，由分镜注入（照抄 MARKUP_GAP）。
 *
 * 结构上有两处「看着可以合并、合并就会改画面」的地方：
 *
 * 1. **两个根元素**（`.quote-block` 与 `.drop-board`）而不是一个包裹层：
 *    旧实现是把这段 markup 直接写进 `.a2v-safe` 的，多一层 div 会改掉
 *    `.a2v-safe` 的 flex 排布（它是 `gap: 46px` 的纵向 flex）；
 * 2. **注释节点也照抄**：它原本就在 markup 里，位置与内容一字不改。
 */
export const GapFigure: FC = () => {
  const fig = useFigure();
  const { data, spec, state } = fig;

  // `beat(fig, fraction)` 与 `fig.api.since` 的组合就是旧的 `beat(state, …)` / `since(f, …)`
  const beatAt = (fraction: number) => beat(fig, fraction);
  const calc = gapFrame(state, fig.api, beatAt);
  const text = gapText(data, spec.labels);

  /*
   * 强调进度与旧 `emphasizeKey` 同一个表达式，且**无论有没有命中短语都照算**：
   * 旧实现是「先算 progress 再去找 .key」，只是找不到节点时不写；这里把值交给
   * `emphasisHtml`，由它在没有强调片段时自然不写任何行内样式。
   */
  const keyProgress = emphasisProgress(state, fig.api, beatAt);
  const html = gapEmphasisHtml(text, {
    progress: keyProgress,
    // 预设生效与否决定光晕写在哪一层：行内 `text-shadow` 会盖掉设计语言层
    preset: Boolean(fig.preset),
    range: fig.api.range,
  });

  // 容器的行内样式只剩入场：强调的行内值全部落在 `emphasisHtml` 生成的节点上
  const textStyle = enterStyle(fig, sinceBeat(fig, 0.04), { distance: 50, amplitude: 3 });

  /*
   * 两栏的入场位移必须与不透明度合成同一条 style：
   * 旧实现先 `enterAlive`（写入位移、缩放与微动），随后**覆写**不透明度
   * （第 599–608 行与第 636–640 行），因此最终 opacity 是后写的那一支，
   * transform 仍来自入场。少写 transform 会让两栏原地淡入——静止的截图上看不出，
   * 动起来才发现少了那 40px 的入场。
   */
  const panelAStyle = {
    ...enterStyle(fig, sinceBeat(fig, 0.16), { distance: 40, amplitude: 2.5, phase: 0 }),
    opacity: String(calc.panelAOpacity),
  };
  const panelBStyle = enterStyle(fig, sinceBeat(fig, 0.22), {
    distance: 40,
    amplitude: 2.5,
    phase: 40,
  });

  /*
   * 引文的取档（`data-a2v-fit="lead"`）：旧页面在预设生效时对它调过 `autofit`，
   * 字号、均衡断行与 `data-a2v-fit-*` 结论都来自引擎。少了这一步，预设下这段
   * 引文会按样式表的默认字号排版——**断行位置跟着变**，整幕的像素对不上，
   * 而溢出闸门也会因为找不到 `data-a2v-fit-fits` 而静默通过。
   */
  const textFit = useFit({ level: 'lead', text: plainText(data['text']) });

  return (
    <>
      <div className="quote-block">
        <span
          className="quote-mark"
          data-el="mark"
          style={{
            opacity: String(calc.markP * 0.14),
            transform: `translateY(${calc.markShift}px)`,
          }}
        >
          {'\u201C'}
        </span>
        <span
          className="quote-rule"
          data-el="rule"
          style={{ transform: `scaleY(${calc.ruleP.toFixed(4)})`, opacity: String(calc.ruleP) }}
        />
        <p
          className="quote-text"
          data-el="text"
          data-a2v-fit="lead"
          ref={textFit.ref}
          style={{ ...textStyle, ...textFit.style }}
          {...emphasisProps(html)}
        />
      </div>
      {/* 落差尺：左边是「先拥有再被拿走」，右边是「本来就没有」 */}
      <div className="drop-board">
        <div className="drop-panel" data-el="panelA" style={panelAStyle}>
          <div className="drop-cap" data-el="capA">
            {text.capA}
          </div>
          <div className="drop-stage">
            <div className="drop-track">
              <span className="drop-ghost" data-el="ghostA" style={{ height: `${calc.ghostAHeight}px` }} />
              <span className="drop-fill" data-el="fillA" style={{ height: `${calc.fillAHeight}px` }} />
              <span className="drop-zero" />
            </div>
            <div className="drop-bracket-wrap">
              <span
                className="drop-bracket"
                data-el="bracketA"
                style={{ top: `${calc.bracketA.top}px`, height: `${calc.bracketA.height}px` }}
              />
              <span
                className="drop-label"
                data-el="labelA"
                style={{ top: `${calc.bracketA.labelTop}px` }}
              >
                {text.labelA}
              </span>
            </div>
          </div>
        </div>
        <div className="drop-panel is-fact" data-el="panelB" style={panelBStyle}>
          <div className="drop-cap" data-el="capB">
            {text.capB}
          </div>
          <div className="drop-stage">
            <div className="drop-track">
              <span className="drop-ghost" data-el="ghostB" style={{ height: `${calc.ghostBHeight}px` }} />
              <span className="drop-fill" data-el="fillB" style={{ height: `${calc.fillBHeight}px` }} />
              <span className="drop-zero" />
            </div>
            <div className="drop-bracket-wrap">
              <span
                className="drop-bracket is-flat"
                data-el="bracketB"
                style={{
                  top: `${calc.bracketB.top}px`,
                  height: `${calc.bracketB.height}px`,
                  opacity: String(calc.flatOpacity),
                }}
              />
              <span
                className="drop-label is-flat"
                data-el="labelB"
                style={{ top: `${calc.bracketB.labelTop}px`, opacity: String(calc.flatOpacity) }}
              >
                {text.labelB}
              </span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};
