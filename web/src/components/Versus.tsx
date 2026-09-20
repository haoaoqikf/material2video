/**
 * 双栏对照（`versus`）：两种反应并排，箭头指出该从哪边转向哪边。
 *
 * 逐行对应旧组件库 `assets/figures.js` 的 `updateVersus`（第 754–817 行）与
 * `MARKUP_VERSUS`（第 819–843 行）。老实现每帧直接改 DOM，这里每帧重算样式交给 React，
 * 但**每一个数学表达式都照搬**——后面要拿新路径的抽帧与旧路径做逐像素 PSNR 对照，
 * 差一个小数位就是一堆白差。
 *
 * 四处「看起来可以简化、简化就会改画面」的地方，原样保留：
 *
 * 1. **`line` 吃的是 0.4 起点、`beat(0.1)` 时长的进度**，`head` 是 0.46 起点、固定 12 帧；
 *    两者都写进 `transform` / `opacity`（老实现也是这么写的），因此必须与
 *    `enterStyle` 出来的 `transform` 分开、不许合并成一个 transform 串。
 * 2. **`--vs-heat` 保留三位小数**（`toFixed(3)`）。它是 CSS `calc()` 里的乘数，
 *    边框透明度、底色与光晕都由它算；位数变了，这些几何量的最后一位就跟着变。
 * 3. **`--vs-heat` 写在右栏的 `style` 上，而不是再写一次 `opacity`**——老实现的注释
 *    写明了理由：入场动画刚写过 `opacity`，覆盖它会让入场在末段跳一下。
 * 4. **右侧是焦点态表面基元**（`a2v-surface` + `data-a2v-state="focus"`）。
 *    整幕的强调色占比靠它撑起来（旧路径实测 0.0289）；焦点态漏掉，
 *    闸门立刻从 0 提醒退回一条 K2。左栏是基准态 `rest`。
 *
 * 「同一帧同一结果」在这里是结构性成立的：本文件里没有计时器、随机数、CSS 动画，
 * 也没有跨帧可变状态，所有取值都是 `localFrame`（与幕长、节奏）的函数。
 * 组件里的少量内联样式由 `useFit` 提供，那个只与字体和容器宽度有关，与第几帧无关。
 */
import type { CSSProperties, FC } from 'react';

import {
  EASE,
  emphasisHtml,
  emphasisProps,
  enterStyle,
  plainText,
  sinceBeat,
  useFigure,
  useFit,
  type EmphasisOptions,
} from '@/runtime/figures';

/* ---------------- 幕内节奏（照抄 updateVersus 里的比例点与帧数） ---------------- */

/**
 * 每个元素的入场起点、位移与微动振幅。
 *
 * 老实现把这些数直接写在 `enterAlive(...)` 的调用里，这里提出来只是为了让
 * 「谁在第几拍出现、往哪个方向走多远」可以一眼看全——数值一个都没改。
 * 注意 `distance` 的**符号**是有意义的：负值从左侧进来（左栏、引子块）。
 */
export const VERSUS_ENTRANCE = {
  /** 引子（quote-block）：论点是「不是 A，而是 B」时，正文先立起来 */
  lead: { at: 0.02, distance: 48, amplitude: 3 },
  title: { at: 0.03, distance: 44, amplitude: 3 },
  /** 左栏（现状）：从左侧滑入 */
  leftSide: { at: 0.16, distance: -46, axis: 'x' as const, amplitude: 2.2 },
  /** 右栏（该转去的方向）：从右侧滑入，相位 40 与左栏错开，两栏才不会同步晃 */
  rightSide: { at: 0.24, distance: 46, axis: 'x' as const, amplitude: 2.2, phase: 40 },
} as const;

/**
 * 箭头与收束的进度参数。`line` / `heat` 的时长是**比例点**，
 * `head` / `note` 是绝对帧数（12 / 20），照抄 `updateVersus`，不要互相换。
 */
export const VERSUS_PROGRESS = {
  line: { at: 0.4, span: 0.1, ease: EASE.symmetric },
  head: { at: 0.46, span: 12, ease: EASE.out },
  heat: { at: 0.52, span: 0.14, ease: EASE.symmetric },
  note: { at: 0.62, span: 20, ease: EASE.out },
  /** 注释最终只亮到 0.9，不与正文抢注意力 */
  noteOpacity: 0.9,
  /** `emphasizeKey(state, api, lead, { at: 0.72, glow: 22, alpha: 0.18 })` */
  emphasize: { at: 0.72, span: 0.1, glow: 22, alpha: 0.18 },
} as const;

/** 注释的最终不透明度。单独导出，测试要按它核对边界帧。 */
export const VERSUS_NOTE_OPACITY = VERSUS_PROGRESS.noteOpacity;

/* ---------------- 纯函数：帧 → 数值 ---------------- */

/** 一幕的节奏上下文：帧号、幕长、节奏名缺一不可（缺了 `beat` 就没有意义）。 */
export interface VersusTiming {
  localFrame: number;
  sceneDurationFrames: number;
  motion?: string;
}

/**
 * 推进量的纯函数：`progress` 与 `motionBeat` 都在这里就地实现，不依赖 React。
 *
 * 数学与 `@/runtime/motion` 的 `progress` / `motionBeat` **逐表达式相同**
 * （同样的钳制顺序、同样的缓动表）。这里不直接调那两个函数，是为了让「这一幕的数值」
 * 能在 Node 里被直接断言——组件的每一帧都由这几个函数算出来，测试与实现因此看的是
 * 同一份代码，而不是「测试抄一份公式再和实现比」。
 */
export function versusProgress(
  timing: VersusTiming,
  startFrame: number,
  durationFrames: number,
  easing: (t: number) => number,
): number {
  if (durationFrames <= 0) {
    return timing.localFrame >= startFrame ? 1 : 0;
  }
  const raw = (timing.localFrame - startFrame) / durationFrames;
  const t = raw < 0 ? 0 : raw > 1 ? 1 : raw;
  return easing(t);
}

/** 缓动表：只取这一幕用到的两条（`updateVersus` 用的是 outQuint / inOutCubic）。 */
export const VERSUS_EASING = {
  outQuint: (t: number): number => 1 - (1 - t) ** 5,
  inOutCubic: (t: number): number => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2),
} as const;

/** 节奏名 → 速度倍率（与 `motion.ts` 的 `TEMPO_SPEED` 同一张表）。 */
const VERSUS_TEMPO: Record<string, number> = { calm: 0.82, normal: 1, impact: 1.24 };

/**
 * 幕内比例点 → 绝对帧号，并按该幕节奏缩放（同 `motionBeat`）。
 *
 * `sceneDurationFrames` 为 0（空幕）时返回 0：这样每一支进度都退化成
 * 「要么没开始、要么已结束」，不会算出 `NaN` 把整帧样式染成 `NaNpx`。
 */
export function versusBeat(timing: VersusTiming, fraction: number): number {
  if (!timing.sceneDurationFrames) {
    return 0;
  }
  return (fraction * timing.sceneDurationFrames) / (VERSUS_TEMPO[timing.motion ?? ''] ?? 1);
}

/** 这一幕的全部推进量。**连续量只在这里算一次**，组件只负责把它们写进样式。 */
export interface VersusTimeline {
  /** 连接线的横向生长（0..1）：老实现写 `scaleX(...)` */
  line: number;
  /** 箭头头的淡入（0..1，outQuint） */
  head: number;
  /** 右栏的升温（0..1，inOutCubic）：`--vs-heat` 的值 */
  heat: number;
  /** 注释的不透明度（0..0.9） */
  note: number;
  /** 强调词光晕与底横线的强度（0..1，inOutCubic） */
  emphasize: number;
}

/**
 * 把幕内帧号算成这一幕的全部推进量。
 *
 * 与 `updateVersus` 的对应关系：
 *   `line`      ← `api.progress(f, beat(0.4), beat(0.1), EASE_SYMMETRIC)`
 *   `head`      ← `api.progress(f, beat(0.46), 12, EASE_OUT)`
 *   `heat`      ← `api.progress(f, beat(0.52), beat(0.14), EASE_SYMMETRIC)`
 *   `note`      ← `api.progress(f, beat(0.62), 20, EASE_OUT) * 0.9`
 *   `emphasize` ← `emphasizeKey(...)` 里的 `api.progress(f, beat(0.72), beat(0.1), EASE_SYMMETRIC)`
 */
export function versusTimeline(timing: VersusTiming): VersusTimeline {
  const { outQuint, inOutCubic } = VERSUS_EASING;
  return {
    line: versusProgress(
      timing,
      versusBeat(timing, VERSUS_PROGRESS.line.at),
      versusBeat(timing, VERSUS_PROGRESS.line.span),
      inOutCubic,
    ),
    head: versusProgress(
      timing,
      versusBeat(timing, VERSUS_PROGRESS.head.at),
      VERSUS_PROGRESS.head.span,
      outQuint,
    ),
    heat: versusProgress(
      timing,
      versusBeat(timing, VERSUS_PROGRESS.heat.at),
      versusBeat(timing, VERSUS_PROGRESS.heat.span),
      inOutCubic,
    ),
    note:
      versusProgress(
        timing,
        versusBeat(timing, VERSUS_PROGRESS.note.at),
        VERSUS_PROGRESS.note.span,
        outQuint,
      ) * VERSUS_NOTE_OPACITY,
    emphasize: versusProgress(
      timing,
      versusBeat(timing, VERSUS_PROGRESS.emphasize.at),
      versusBeat(timing, VERSUS_PROGRESS.emphasize.span),
      inOutCubic,
    ),
  };
}

/** 老实现写进样式的字符串格式：连接线四位、升温三位（照抄 `toFixed`）。 */
export function versusLineTransform(line: number): string {
  return `scaleX(${line.toFixed(4)})`;
}

export function versusHeatValue(heat: number): string {
  return heat.toFixed(3);
}

export function versusOpacityValue(value: number): string {
  return String(value);
}

/**
 * 空数据安全的取值：分镜字段可能整个缺失（`comparison` 场景没有 `text`，
 * `quote + versus` 又没有 `left` / `right`），此时一律留空而不是显示 `undefined`。
 */
export function versusText(value: unknown): string {
  return plainText(value);
}

/**
 * 引子那一小段文字的渲染属性。
 *
 * 强调词（`<span class="key">` + 下划线与光晕的行内值）交给运行时的
 * `emphasisHtml` / `emphasisProps`：那是旧实现 `emphasize`（拼标记）与
 * `emphasizeKey`（写行内值）的合体，逐字保留了「每个短语各替换第一处出现」。
 * 组件不再自己拼标记——两处各拼一遍，强调词的位置迟早会漂移。
 *
 * 光晕上限照抄 `emphasizeKey` 的调用参数（`glow: 22` / `alpha: 0.18`），
 * 不是运行时的缺省 26 / 0.22：这一处是老实现显式传过的值。
 */
export function versusEmphasisProps(
  text: unknown,
  phrases: unknown,
  options: { progress: number; preset: boolean; range: EmphasisOptions['range'] },
): { dangerouslySetInnerHTML: { __html: string } } {
  return emphasisProps(
    emphasisHtml(text, phrases, {
      underline: true,
      progress: options.progress,
      preset: options.preset,
      glowPx: VERSUS_PROGRESS.emphasize.glow,
      glowAlpha: VERSUS_PROGRESS.emphasize.alpha,
      range: options.range,
    }),
  );
}

/* ---------------- 组件 ---------------- */

export const VersusFigure: FC = () => {
  const fig = useFigure();
  const { localFrame } = fig.state;
  const data = fig.data;
  const labels = fig.spec.labels ?? {};

  // 老实现：left / right 优先取分镜字段，其他场景类型（quote + versus）退回标注
  const leftText = versusText(data['left'] ?? labels['left']);
  const rightText = versusText(data['right'] ?? labels['right']);
  const titleText = versusText(data['title']);
  const noteText = versusText(labels['note']);
  const leadText = versusText(data['text']);

  // 引子：comparison 场景没有 text，这一段整个不占位（老实现设 display: none）
  const showLead = Boolean(data['text']);

  const timing: VersusTiming = {
    localFrame,
    sceneDurationFrames: fig.state.sceneDurationFrames,
    motion: fig.state.motion,
  };
  const timeline = versusTimeline(timing);

  const lead = useFit({ level: 'lead', text: leadText });
  const title = useFit({ level: 'title', text: titleText });
  const left = useFit({ level: 'lead', text: leftText });
  const right = useFit({ level: 'lead', text: rightText });
  const note = useFit({ level: 'caption', text: noteText });

  // 强调词只由「文案 + 短语 + 预设」决定，与帧号无关（同一帧永远得到同一串标记）
  const leadHtml = versusEmphasisProps(data['text'], data['emphasis'], {
    progress: timeline.emphasize,
    // 预设决定光晕写在哪一层：预设只写自定义属性，非预设才写行内 text-shadow
    preset: fig.preset === 'keynote',
    range: fig.api.range,
  });

  return (
    <>
      {/*
        引子块：没有文案时**仍然渲染**，只是 `display: none`——与旧实现一致
        （旧实现写的是 `lead.style.display = 'none'`，元素始终在 DOM 里）。
        这一条不是洁癖：动效扫描（`motion.sweep`）按元素逐个量入场，
        条件渲染会让「没有引子」的那一幕少一个入场元素，
        M0 的计数与旧路径对不上（实测 89 vs 90、8 vs 9 个有位移）。
        它无条件参与入场计算——旧实现也是先算 `enterAlive` 再决定显示的。
      */}
      <div
        className="quote-block"
        data-el="lead"
        ref={lead.ref}
        style={{
          ...enterStyle(fig, sinceBeat(fig, VERSUS_ENTRANCE.lead.at), {
            distance: VERSUS_ENTRANCE.lead.distance,
            amplitude: VERSUS_ENTRANCE.lead.amplitude,
          }),
          display: showLead ? undefined : 'none',
        }}
      >
        <span className="quote-mark" data-el="mark">
          &ldquo;
        </span>
        <span className="quote-rule" data-el="rule" />
        <p
          className="quote-text"
          data-el="leadText"
          data-a2v-fit="lead"
          style={lead.style}
          {...leadHtml}
        />
      </div>
      <h2
        className="section-title"
        data-el="title"
        data-a2v-fit="title"
        ref={title.ref}
        style={{
          ...enterStyle(fig, sinceBeat(fig, VERSUS_ENTRANCE.title.at), {
            distance: VERSUS_ENTRANCE.title.distance,
            amplitude: VERSUS_ENTRANCE.title.amplitude,
          }),
          ...title.style,
        }}
      >
        {titleText}
      </h2>
      <div className="vs-board">
        {/*
          两侧都是表面基元：左是基准态，右是当前焦点。
          焦点态的底块由 `a2v-surface[data-a2v-state="focus"]` 的 `background-color`
          给出（`--a2v-focus-mix` 默认 1 = 完整焦点外观），这是这一幕强调色占比的来源，
          因此 `a2v-surface` 与 `data-a2v-state` 一个都不能少、也不能改名。
        */}
        <div
          className="vs-side is-left a2v-surface"
          data-a2v-state="rest"
          data-el="leftSide"
          ref={left.ref}
          style={{
            ...enterStyle(fig, sinceBeat(fig, VERSUS_ENTRANCE.leftSide.at), {
              distance: VERSUS_ENTRANCE.leftSide.distance,
              axis: VERSUS_ENTRANCE.leftSide.axis,
              amplitude: VERSUS_ENTRANCE.leftSide.amplitude,
            }),
            ...left.style,
          }}
        >
          <p className="vs-text" data-el="leftText" data-a2v-fit="lead">
            {leftText}
          </p>
        </div>
        <div className="vs-link" aria-hidden="true">
          {/* 连接线：先长出来（scaleX），再点亮右栏。老实现同样只改 transform */}
          <span
            className="vs-line"
            data-el="line"
            style={{ transform: versusLineTransform(timeline.line) }}
          />
          <span
            className="vs-head"
            data-el="head"
            style={{ opacity: versusOpacityValue(timeline.head) }}
          />
        </div>
        <div
          className="vs-side is-right a2v-surface"
          data-a2v-state="focus"
          data-el="rightSide"
          ref={right.ref}
          style={
            {
              ...enterStyle(fig, sinceBeat(fig, VERSUS_ENTRANCE.rightSide.at), {
                distance: VERSUS_ENTRANCE.rightSide.distance,
                axis: VERSUS_ENTRANCE.rightSide.axis,
                amplitude: VERSUS_ENTRANCE.rightSide.amplitude,
                phase: VERSUS_ENTRANCE.rightSide.phase,
              }),
              ...right.style,
              // 连续量写成内联自定义属性：不覆盖入场写下的 opacity，
              // 也不写行内 `color`（行内优先级最高，会让设计语言层失效）
              '--vs-heat': versusHeatValue(timeline.heat),
            } as CSSProperties
          }
        >
          <p className="vs-text" data-el="rightText" data-a2v-fit="lead">
            {rightText}
          </p>
        </div>
      </div>
      <p
        className="vs-note"
        data-el="note"
        data-a2v-fit="caption"
        ref={note.ref}
        style={{ opacity: versusOpacityValue(timeline.note), ...note.style }}
      >
        {noteText}
      </p>
    </>
  );
};
