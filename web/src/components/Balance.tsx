/**
 * 01 开场：天平。
 *
 * 逐行对应旧组件库 `assets/figures.js` 的 `updateBalance`（第 370–503 行）与
 * `MARKUP_BALANCE`（第 512–556 行）。结构与表达式照抄，只把「每帧写 DOM」
 * 换成「每帧算出 style / 属性交给 React」：
 *
 *   老的 `el.style.transform` / `el.textContent` / `setAttribute`
 *   →   JSX 的 `style={{…}}` 与 `transform` / `opacity` / `stroke` 属性。
 *
 * 旧实现的叙事：开场先把「害怕」压下去（左盘放上「命运的考试」、恐惧的重量），
 * 再证明它只是个空壳（实心块变成虚线、横梁弹回水平），同时右盘「一次上场」
 * 亮起强调色、标题里的「害怕」褪回墨色。颜色本身就是叙事：恐惧退场，动作上场。
 *
 * 几处「看着可以简化、简化就会改画面」的地方写在对应代码旁：
 *
 * 1. `press` 的时长是 `beat(fig, 0.14)` 而不是 14 帧——它按幕长与节奏缩放；
 * 2. 弹簧吃**线性秒数**（`sinceBeat`）、透明度/进度吃 **0..1 进度**（`progress`），
 *    同一个起点两种输入各自取用（弹簧喂缓动过的进度会让 response 失去意义）；
 * 3. `beamP` 同时是横梁的入场透明度，所以线性秒数另算一份，不能就地改掉它；
 * 4. 光晕以**自身圆心**缩放：`127 * (1 - haloScale)` 先把它挪回原点再缩放，
 *    去掉这个位移，缩放会把圆心一起拖走，光晕会从盘外飞进来。
 */
import type { CSSProperties, FC } from 'react';

import {
  EASE,
  beat,
  emphasisHtml,
  emphasisProps,
  enterStyle,
  plainText,
  sinceBeat,
  svgOpacity,
  svgTransform,
  useFigure,
  useFit,
} from '@/runtime/figures';
import { idle, springBy } from '@/runtime/motion';

import { PATH_LENGTH, SCALE, panAnchors, rightRectStroke } from './balanceGeometry';

/**
 * 纯计算部分对外导出，测试直接从本文件取用（`Balance.test.ts` 只 import 这个
 * 文件，其中没有 `document` / `window`，因此不需要 jsdom）。
 */
export { PATH_LENGTH, SCALE, panAnchors, rightRectStroke } from './balanceGeometry';
export type { PanAnchor, PanAnchors } from './balanceGeometry';

/**
 * 带自定义属性的行内样式。
 *
 * `@types/react` 的 `CSSProperties` **故意**删掉了索引签名（封闭类型），而
 * `--a2v-*` 这类自定义属性必须原样写进行内样式——它们是「组件报告档位、
 * 样式表决定落点」的唯一通道，改成写 `color` 会让行内样式盖住设计语言层。
 * 因此这里加一个只允许 `--` 前缀的索引签名，而不是 `as any`：
 * 拼错一个普通属性名仍然会报错。
 */
type FigureStyle = CSSProperties & Record<`--${string}`, string>;

/**
 * 从强调串里取回**纯文本**（去掉 `emphasize` 拼进去的标记），只给 `useFit` 用。
 *
 * 为什么要过一遍提取：旧实现是在**已有节点上**量宽度的，量到的自然是纯文本的宽度；
 * 若把带标记的串直接喂给取档引擎，`<span class="key">` 会被当成要排版的字，
 * 字宽统计随之偏大，标题会被无谓地降一档。这里只做两件事：去掉标签、解开实体。
 */
function textOf(html: string): string {
  return html
    .replace(/<[^>]*>/g, '')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&');
}

export const BalanceFigure: FC = () => {
  const fig = useFigure();
  const f = fig.state.localFrame;
  const data = fig.data;
  const ann = fig.spec.labels;

  // 标题里的强调词随空壳一起褪色：恐惧退场，动作上场。
  // 旧实现把这个档位写成 `.key` 节点上的**行内**自定义属性（第 501–504 行），
  // 因此必须由 `emphasisHtml` 拼进标记里，而不是挂在 `<h1>` 上：
  // 样式表的 `.key` 规则自己声明了 `--a2v-emphasis-mix: 0`，
  // 挂在祖先上会被元素自身的声明盖掉（实测强调词一直停在强调色，差 7/255）。
  const cool = fig.api.progress(f, beat(fig, 0.62), beat(fig, 0.16), EASE.symmetric);
  const emphasisMix = fig.api.range(cool, 0, 1);

  // 标题走运行时的 `emphasisHtml`（返回 HTML 串）+ dangerouslySetInnerHTML，
  // 与旧实现的 `setText`→`innerHTML` 逐字符相同：换成节点拼装会改变
  // 「后一个短语匹配不到前一个短语插入的标记」这条规则，强调词的位置会跟着变。
  //
  // **不传 `progress`**：本幕的旧实现没有给强调词写光晕（对比 `emphasizeKey`
  // 那条路径），传 0 也会写出一串行内 `text-shadow` / `--a2v-emphasis-glow`。
  const titleHtml = emphasisHtml(data['text'], data['emphasis'], {
    vars: { '--a2v-emphasis-mix': emphasisMix.toFixed(4) },
  });

  // 副标题按硬换行切成两行：`data.subtitle` 里的 `\n` 是作者断的行，不是自动折行。
  // 旧实现写 `String(...).split('\n')`，缺行时给空串（不是 undefined）。
  const lines = String(data['subtitle'] ?? '').split('\n');
  const sub1 = lines[0] ?? '';
  const sub2 = lines[1] ?? '';

  // 两个吊盘的文字都用本幕的标注。左盘在实心/空壳两份节点上各写一次，
  // 是为了「换成空壳」的那一帧两处文字都已就位——内容切换不伴随重排。
  const leftPanText = plainText(ann['leftPan']);
  const rightPanText = plainText(ann['rightPan']);

  // ---- 支架：立柱自下而上画出，底座与斜撑随后 --------------------------------
  // 长度显式给出（PATH_LENGTH 按 `d` 算好），不再从 DOM 的 data-a2v-length /
  // getTotalLength() 读回来——那是隐藏状态。
  const pillar = fig.api.drawPath(
    fig.api.progress(f, beat(fig, 0.15), 26, EASE.out),
    PATH_LENGTH.pillar,
  );
  const legL = fig.api.drawPath(
    fig.api.progress(f, beat(fig, 0.22), 20, EASE.out),
    PATH_LENGTH.legL,
  );
  const legR = fig.api.drawPath(
    fig.api.progress(f, beat(fig, 0.22), 20, EASE.out),
    PATH_LENGTH.legR,
  );
  const base = fig.api.drawPath(
    fig.api.progress(f, beat(fig, 0.24), 20, EASE.out),
    PATH_LENGTH.base,
  );
  const pivot = fig.api.progress(f, beat(fig, 0.24), 18, EASE.out);

  // ---- 倾角：恐惧压下左盘 → 看穿空壳 → 弹回水平 ------------------------------
  const press = fig.api.progress(f, beat(fig, 0.42), beat(fig, 0.14), EASE.symmetric);
  const relief = springBy(fig.api.since(f, beat(fig, 0.62)), 'snap');
  // 倾角是「压下去」与「弹回来」的乘积：relief 到 1 时 theta 归零、横梁水平。
  // 两段各自独立求值（不写成状态机），因此任意一帧都能直接算出来，
  // 拖动进度条跳到中间也不会得到不同的结果。
  const theta = SCALE.TILT * press * (1 - relief);
  const anchors = panAnchors(theta);

  const beamP = fig.api.progress(f, beat(fig, 0.25), 26, EASE.out);
  // 弹簧要的是线性秒数，透明度要的是 0..1 进度：同一个起点、两种输入，各自取用。
  // beamP 还要当透明度用，所以不能就地改掉它。
  const beamSeconds = fig.api.since(f, beat(fig, 0.25));
  const beamSettle = fig.api.progress(f, beat(fig, 0.7), 40, EASE.symmetric);
  const beamDrift = idle(f, { amplitude: 2 }) * beamSettle;
  const beamTransform = svgTransform(
    SCALE.PIVOT_X,
    SCALE.PIVOT_Y + beamDrift,
    theta,
    // 弹簧过冲会把 scale 推过 1；clamp: false 让过冲照实表现（旧实现同样如此）
    fig.api.range(springBy(beamSeconds, 'firm'), 0.55, 1, { clamp: false }),
  );

  // ---- 吊盘：跟着横梁端点平移，落位后保持垂直 --------------------------------
  const panP = springBy(fig.api.since(f, beat(fig, 0.28)), 'firm');
  const panSettle = fig.api.progress(f, beat(fig, 0.28), 40, EASE.symmetric);
  const dropIn = (1 - panP) * 60;
  // 两个吊盘的常驻微动相位差 50 帧：同相位会读成整幅画在一起晃。
  const driftL = idle(f, { amplitude: 2.4 }) * panSettle;
  const driftR = idle(f, { amplitude: 2.4, phase: 50 }) * panSettle;
  const panOpacity = svgOpacity(fig.api.clamp(panP * 1.5, 0, 1));
  const panLeftTransform = svgTransform(anchors.left.x, anchors.left.y + dropIn + driftL);
  const panRightTransform = svgTransform(anchors.right.x, anchors.right.y + dropIn + driftR);

  // ---- 左盘的重物落下 --------------------------------------------------------
  const loadP = springBy(fig.api.since(f, beat(fig, 0.34)), 'lively');
  const loadDrop = (1 - loadP) * -170;
  const reveal = fig.api.progress(f, beat(fig, 0.54), beat(fig, 0.16), EASE.symmetric);
  const loadLeftOpacity = svgOpacity(fig.api.clamp(loadP, 0, 1));
  // 位移由 loadP 给、缩放由 reveal 给：两条曲线不同步，合并成一个进度会改画面。
  const loadLeftTransform = svgTransform(0, loadDrop, 0, 1 - reveal * 0.06);

  // ---- 右盘的「一次上场」：轻，但它是最后亮起来的那一个 ----------------------
  const tokenP = springBy(fig.api.since(f, beat(fig, 0.3)), 'lively');
  const loadRightOpacity = svgOpacity(fig.api.clamp(tokenP, 0, 1));
  const loadRightTransform = svgTransform(
    0,
    (1 - tokenP) * -120,
    0,
    fig.api.range(tokenP, 0.9, 1, { clamp: false }),
  );

  const glow = fig.api.progress(f, beat(fig, 0.66), beat(fig, 0.16), EASE.symmetric);
  const haloScale = fig.api.range(glow, 0.6, 1.1, { clamp: false });
  // 光晕以自身圆心（cy=127）缩放，否则缩放会把圆心一起拖走。
  const haloTransform = svgTransform(0, 127 * (1 - haloScale), 0, haloScale);
  const haloOpacity = svgOpacity(glow * 0.85);

  // 右盘描边的浓度逐帧来自 glow（28%→90%），落点本身是主题令牌。
  const rectStroke = rightRectStroke(glow);

  // 右盘那行字的亮度：预设下报告 0..1 的档位，由样式表决定落点；
  // 未启用预设时旧实现整支跳过（`presetActive()` 为假就不写），
  // 这里保持同样的行为——不写行内值，也就不会覆盖样式表的墨色。
  const rightTextStyle: FigureStyle =
    fig.preset === 'keynote' ? { '--a2v-token-glow': glow.toFixed(4) } : {};

  // 标题的取档（`data-a2v-fit="display"` 声明的档位）。
  //
  // 旧页面在预设生效时对它调过 `autofit`，因此预设下标题的字号、行高、字距
  // 来自引擎而不是样式表；`useFit` 与它同一口径（未启用预设时返回空样式，
  // 元素照样式表渲染）。**取档只改这几个数值，不改文字**，所以与
  // `dangerouslySetInnerHTML` 的强调标记不冲突。
  const titleFit = useFit({ level: 'display', text: textOf(titleHtml) });

  const titleStyle: FigureStyle = {
    ...enterStyle(fig, sinceBeat(fig, 0.03), { distance: 58, amplitude: 4 }),
    ...titleFit.style,
  };

  return (
    <>
      <h1
        className="title-text"
        data-el="text"
        data-a2v-fit="display"
        ref={titleFit.ref}
        style={titleStyle}
        // `emphasisProps` 返回的 `{ __html: string }` 比 React 的
        // `{ __html: string | TrustedHTML }` 窄一位（运行时不依赖 TrustedHTML），
        // 展开时按 React 的 props 类型断言，不改运行时的返回形状。
        {...(emphasisProps(titleHtml) as {
          dangerouslySetInnerHTML: { __html: string };
        })}
      />
      <p className="title-sub">
        <span
          className="title-sub-line"
          data-el="sub1"
          style={enterStyle(fig, sinceBeat(fig, 0.46), {
            distance: 24,
            amplitude: 3,
            periodFrames: 150,
            phase: 20,
          })}
        >
          {sub1}
        </span>
        <span
          className="title-sub-line"
          data-el="sub2"
          style={enterStyle(fig, sinceBeat(fig, 0.7), {
            distance: 24,
            amplitude: 3,
            periodFrames: 150,
            phase: 60,
          })}
        >
          {sub2}
        </span>
      </p>
      {/* 天平：恐惧把「命运的考试」压下去，随后证明它只是个空壳 */}
      <svg className="fig fig-scale" viewBox="0 0 888 430" aria-hidden="true">
        <defs>
          {/*
            `stop-color` 里带 `color-mix(...)`：React 对 SVG 属性只做
            「有同名的 DOM 属性就照写」，因此写 `stopColor` 与旧标记的
            `stop-color` 落到同一个属性上，颜色表达式不许多一个空格。
          */}
          <radialGradient id="scale-halo">
            <stop
              offset="0"
              stopColor="color-mix(in srgb, var(--a2v-accent-soft-solid) 45%, transparent)"
            />
            <stop
              offset="1"
              stopColor="color-mix(in srgb, var(--a2v-accent-soft-solid) 0%, transparent)"
            />
          </radialGradient>
        </defs>
        <path
          className="ln"
          data-el="pillar"
          d="M444 372 L444 96"
          strokeDasharray={pillar.strokeDasharray}
          strokeDashoffset={pillar.strokeDashoffset}
          style={{ opacity: pillar.opacity }}
        />
        <path
          className="ln"
          data-el="legL"
          d="M444 368 L364 404"
          strokeDasharray={legL.strokeDasharray}
          strokeDashoffset={legL.strokeDashoffset}
          style={{ opacity: legL.opacity }}
        />
        <path
          className="ln"
          data-el="legR"
          d="M444 368 L524 404"
          strokeDasharray={legR.strokeDasharray}
          strokeDashoffset={legR.strokeDashoffset}
          style={{ opacity: legR.opacity }}
        />
        <path
          className="ln"
          data-el="base"
          d="M364 404 L524 404"
          strokeDasharray={base.strokeDasharray}
          strokeDashoffset={base.strokeDashoffset}
          style={{ opacity: base.opacity }}
        />
        {/*
          `pivot` 的圆点用 `opacity` **属性**（不是 style）：圆点同时带
          `.scale-pivot` 的 `fill`，样式表若在某处写了 `opacity`，属性会被盖掉——
          旧实现写的正是 `setAttribute('opacity', …)`，这里保持一致。
        */}
        <circle
          className="scale-pivot"
          data-el="pivot"
          cx="444"
          cy="96"
          r="13"
          opacity={svgOpacity(pivot)}
        />
        <g data-el="beam" transform={beamTransform} opacity={svgOpacity(beamP)}>
          <path className="ln" d="M-300 0 L300 0" />
        </g>
        <g data-el="panLeft" transform={panLeftTransform} opacity={panOpacity}>
          <path className="scale-rope" d="M0 0 L0 168" />
          <path className="scale-plate" d="M-130 168 L130 168 L110 198 L-110 198 Z" />
          <g data-el="loadLeft" transform={loadLeftTransform} opacity={loadLeftOpacity}>
            <g data-el="loadLeftSolid" opacity={svgOpacity(1 - reveal)}>
              <rect className="load-solid" x="-116" y="52" width="232" height="116" rx="16" />
              {/*
                旧代码写的是 `setPlainText(pick('loadLeftText'), ann.leftPan)`，
                但 `MARKUP_BALANCE` 里**没有** `data-el="loadLeftText"`
                （见下面「照抄时补的一个锚点」）。这里保留这个名字。
              */}
              <text className="load-text" data-el="loadLeftText" x="0" y="112">
                {leftPanText}
              </text>
            </g>
            <g data-el="loadLeftHollow" opacity={svgOpacity(reveal)}>
              <rect className="load-hollow" x="-116" y="52" width="232" height="116" rx="16" />
              <text className="load-text is-ink" data-el="loadLeftTextHollow" x="0" y="112">
                {leftPanText}
              </text>
            </g>
          </g>
        </g>
        <g data-el="panRight" transform={panRightTransform} opacity={panOpacity}>
          <circle
            className="scale-halo"
            data-el="rightHalo"
            cx="0"
            cy="127"
            r="118"
            transform={haloTransform}
            opacity={haloOpacity}
          />
          <path className="scale-rope" d="M0 0 L0 168" />
          <path className="scale-plate" d="M-130 168 L130 168 L110 198 L-110 198 Z" />
          <g data-el="loadRight" transform={loadRightTransform} opacity={loadRightOpacity}>
            <rect
              className="load-token a2v-surface"
              data-a2v-state="focus"
              data-el="loadRightRect"
              x="-84"
              y="86"
              width="168"
              height="82"
              rx="14"
              stroke={rectStroke}
            />
            <text
              className="load-text is-ink"
              data-el="loadRightText"
              x="0"
              y="128"
              style={rightTextStyle}
            >
              {rightPanText}
            </text>
          </g>
        </g>
      </svg>
    </>
  );
};

/*
 * ---------------------------------------------------------------------------
 * 迁移注记：这一支与旧实现的对照结论，写在这里以免被读成「完全一致」。
 *
 * 1. `--a2v-emphasis-mix` 的挂点（**曾经是一处真实的画面偏差，已修**）。
 *    旧实现是 `title.querySelector('.key').style.setProperty('--a2v-emphasis-mix', …)`
 *    （`figures.js` 第 501–504 行），值必须落在 `.key` 这个 span 上：`figures.css`
 *    与 `keynote.css` 都给 `.key` 声明了 `--a2v-emphasis-mix: 0`，而**元素上的
 *    声明优先于继承**，写在祖先（h1）上的值会被 `.key` 自己的 0 盖掉。
 *    画面表现就是「强调词永远停在强调色，褪色从不发生」——不报错、不崩溃，
 *    只是这一处不动（实测第 120 帧该 span 的计算色差 7/255）。
 *
 *    修法是给 `emphasisHtml` 加一条 `vars` 通道：行内声明由它拼进**第一个强调
 *    片段**上，与下划线、光晕走同一条路。不需要改样式表，也不需要组件读 DOM。
 *
 * 2. 左盘文字（**原先记成偏差，实际不是**）：旧 `MARKUP_BALANCE` 里是有
 *    `data-el="loadLeftText"` 的（第 539 行），`updateBalance` 也真的把
 *    `ann.leftPan` 写进了实心块（第 387 行）；空壳那一份同理（第 388 / 543 行）。
 *    这里两处都写，与旧实现一致，没有需要「改回空串」的地方。
 *
 * 另外两处**看起来像偏差、实际不是**，一并记下：
 *
 * - 标题取档：旧页面在预设下对 `.title-text` 调过 `autofit`，这里用 `useFit`
 *   （同一口径：未启用预设返回空样式）。取档只改字号/行高/字距，不改文字，
 *   因此与 `dangerouslySetInnerHTML` 的强调标记不冲突；喂进引擎的是去标签后的
 *   纯文本（旧实现在节点上量宽度，量到的也是纯文本的宽度）。
 * - 左盘文字的读法：旧实现的 `ann.leftPan` 走的是 `labels` 对象，
 *   这里同样是 `fig.spec.labels['leftPan']`，那份 `var lines = String(data.subtitle
 *   || '')` 的切行也照抄（缺行给空串）。
 * ---------------------------------------------------------------------------
 */
