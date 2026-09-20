/**
 * 落差尺（gap）的纯计算对照测试。
 *
 * 这里不渲染组件、不引入任何测试库：`Gap.tsx` 导出的几个命名函数就是
 * 「旧 `updateGap` / `placeBracket` / `applyDrop` 的数学」，把它们的输入输出钉住，
 * 就等于把这一幕的几何钉住。断言里的数字全部是**照旧公式手算**出来的，
 * 不是从实现里反抄的——否则等式两边一起错，测试照样通过。
 *
 * 覆盖四件事：
 *   1. 取值与手算一致（含 `toFixed` 的位数与单位后缀，那是旧实现写进 DOM 的字符串）；
 *   2. 同输入同输出（同一帧调用多次结果必须逐位相同，抽帧对照依赖这一点）；
 *   3. 边界：进度 0 与 1 的两端状态；
 *   4. 空数据不抛错，且落到「画面仍然成立」的那一档取值。
 */
import { describe, expect, it } from 'vitest';

import {
  BRACKET_FLAT_H,
  LABEL_TOP_MAX,
  LABEL_TOP_MIN,
  TRACK_H,
  bracketPlacement,
  dropHeight,
  emphasisProgress,
  gapEmphasisHtml,
  gapFrame,
  gapText,
  type GapCalcApi,
  type GapMotionState,
  type GapText,
} from '@/components/Gap';
import { EASE, emphasisHtml } from '@/runtime/figures';
import { progress as motionProgress, range as motionRange, since as motionSince } from '@/runtime/motion';

/** 本幕在示例分镜里的取值：240 帧、normal 节奏（`examples/keynote-baseline`）。 */
const SCENE: GapMotionState = {
  localFrame: 0,
  sceneDurationFrames: 240,
  motion: 'normal',
};

/** 测试用的计算原语：与运行时 `createFigureApi` 同一份实现，只是写死 fps=30。 */
const API: GapCalcApi = {
  progress: (frame, start, duration, easing) => motionProgress(frame, start, duration, easing),
  since: (frame, startFrame = 0) => motionSince(frame, startFrame, 30),
};

/** 旧的 `beat(state, fraction)`：比例点 × 幕长 / 节奏倍率（normal = 1）。 */
const beatAt = (fraction: number) => fraction * SCENE.sceneDurationFrames;

/** 按帧号求本幕的纯计算。 */
const at = (frame: number) => gapFrame({ ...SCENE, localFrame: frame }, API, beatAt);

/** 三档缓动的期望值：与 `EASING` 里的公式同形，但在这里独立写一遍。 */
const outQuint = (t: number) => 1 - (1 - t) ** 5;
const inOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

describe('dropHeight（旧 applyDrop 的高度表达式）', () => {
  it('按 clamp(ratio,0,1) * 268 计算并保留一位小数', () => {
    expect(dropHeight(0)).toBe('0.0');
    expect(dropHeight(1)).toBe('268.0');
    expect(dropHeight(0.5)).toBe('134.0');
    // 0.123 * 268 = 32.964 → 33.0
    expect(dropHeight(0.123)).toBe('33.0');
    // 0.07 * 268 = 18.76 → 18.8
    expect(dropHeight(0.07)).toBe('18.8');
  });

  it('超界比例被钳到 0..1（两条边界都必须钉住）', () => {
    expect(dropHeight(-3)).toBe('0.0');
    expect(dropHeight(2.5)).toBe('268.0');
    expect(dropHeight(1.0001)).toBe('268.0');
  });

  it('空数据（null / undefined / NaN / 非数字串）不抛错，按 0 处理', () => {
    expect(() => dropHeight(undefined)).not.toThrow();
    expect(dropHeight(undefined)).toBe('0.0');
    expect(dropHeight(null)).toBe('0.0');
    expect(dropHeight(Number.NaN)).toBe('0.0');
    expect(dropHeight('')).toBe('0.0');
    expect(dropHeight('0.5')).toBe('134.0');
  });

  it('同输入同输出（一次算与连算十次逐位相同）', () => {
    const first = dropHeight(0.831);
    for (let i = 0; i < 10; i += 1) {
      expect(dropHeight(0.831)).toBe(first);
    }
  });
});

describe('bracketPlacement（旧 placeBracket）', () => {
  it('非平括号：top = fill * 268，height = gap * 268，标签取括号中点', () => {
    // fill 0.8 → 214.4；gap 0.3 → 80.4；中点 214.4 + 40.2 = 254.6
    // → clamp(254.6, 44, 252) = 252 （贴着尺底，旧实现的钳制就在这里生效）→ 252 - 20 = 232.0
    expect(bracketPlacement(0.8, 0.3, false)).toEqual({
      top: '214.4',
      height: '80.4',
      labelTop: '232.0',
    });
    // 中点没到上界时才是真正的「中点 - 20」：fill 0.5 / gap 0.2 → 134 + 26.8 = 160.8 → 140.8
    expect(bracketPlacement(0.5, 0.2, false)).toEqual({
      top: '134.0',
      height: '53.6',
      labelTop: '140.8',
    });
  });

  it('平括号（本来就没有）：忽略传入比例，压成贴着 0 线的一段，标签贴 0 线', () => {
    // top = 268 - 6 = 262；height = 6；center = 268 → clamp(268, 44, 252) = 252 → 232
    expect(bracketPlacement(0, 0, true)).toEqual({
      top: '262.0',
      height: '6.0',
      labelTop: '232.0',
    });
    // 传进去的比例在 flat 分支里不应产生任何影响
    expect(bracketPlacement(0.9, 0.4, true)).toEqual(bracketPlacement(0, 0, true));
  });

  it('标签落点被钳进 [44, 252]，再减去 20 的自身半高补偿', () => {
    // 括号贴地（top 268，height 0）时中点 268 超上界
    expect(bracketPlacement(1, 0, false).labelTop).toBe(`${LABEL_TOP_MAX - 20}.0`);
    // 括号贴顶（top 0，height 0）时中点 0 低于下界
    expect(bracketPlacement(0, 0, false).labelTop).toBe(`${LABEL_TOP_MIN - 20}.0`);
  });

  it('空数据不抛错，且两端都退化成「0 高度」', () => {
    expect(() => bracketPlacement(undefined, undefined, false)).not.toThrow();
    expect(bracketPlacement(undefined, undefined, false)).toEqual({
      top: '0.0',
      height: '0.0',
      labelTop: '24.0',
    });
  });

  it('常量与样式表一致：TRACK_H 268 / 平括号 6 / 标签 [44, 252]', () => {
    // 样式表 `.drop-track` / `.drop-bracket-wrap` 都是 height: 268px
    expect(TRACK_H).toBe(268);
    expect(BRACKET_FLAT_H).toBe(6);
    expect(LABEL_TOP_MAX).toBe(252);
  });
});

describe('gapFrame：与旧表达式逐个对照', () => {
  it('第 0 帧：除了已开始的入场，一切都是起点状态', () => {
    const r = at(0);
    // progress(0, 0, 20) = 0
    expect(r.ruleP).toBe(0);
    // beat(0.02) = 4.8，第 0 帧还没到；引号停在下方 26px 处等入场
    // （旧第 592 行：`api.range(markP, -26, 0)`，即 -26 + 26·markP）
    expect(r.markP).toBe(0);
    expect(r.markShift).toBe('-26.0');
    expect(r.ownP).toBe(0);
    expect(r.dropP).toBe(0);
    expect(r.aFill).toBe(0);
    expect(r.aGhost).toBe(0);
    expect(r.gapP).toBe(0);
    expect(r.flatP).toBe(0);
    expect(r.fadeP).toBe(0);
    expect(r.panelAOpacity).toBe(1);
    expect(r.fillAHeight).toBe('0.0');
    expect(r.ghostAHeight).toBe('0.0');
    expect(r.bracketA).toEqual({ top: '0.0', height: '0.0', labelTop: '24.0' });
    // 右边那一栏从头就是「压平的括号」
    expect(r.bracketB).toEqual({ top: '262.0', height: '6.0', labelTop: '232.0' });
    expect(r.fillBHeight).toBe('0.0');
    expect(r.ghostBHeight).toBe('0.0');
    expect(r.flatOpacity).toBe(0);
  });

  it('第 240 帧（幕末）：两端状态全部到位', () => {
    const r = at(240);
    expect(r.ruleP).toBe(1);
    expect(r.markP).toBe(1);
    // 到位：`range(1, -26, 0)` = 0，引号回到基线
    expect(r.markShift).toBe('0.0');
    expect(r.ownP).toBe(1);
    expect(r.dropP).toBe(1);
    // 左柱归零、虚线停在满格：差值就是这一幕要量的「失去」
    expect(r.aFill).toBe(0);
    expect(r.aGhost).toBe(1);
    expect(r.fillAHeight).toBe('0.0');
    expect(r.ghostAHeight).toBe('268.0');
    expect(r.gapP).toBe(1);
    // 左括号：从 0 量到 268（满格）
    expect(r.bracketA).toEqual({ top: '0.0', height: '268.0', labelTop: '114.0' });
    expect(r.flatP).toBe(1);
    expect(r.flatOpacity).toBe(1);
    expect(r.fadeP).toBe(1);
    expect(r.panelAOpacity).toBeCloseTo(0.45, 12);
    // 右括号：0.012 * 268 = 3.216 → 3.2，但仍被 flat 分支压成 [262, 268)
    expect(r.bracketB).toEqual({ top: '262.0', height: '6.0', labelTop: '232.0' });
  });

  it('第 120 帧：逐值手算对照（含 beat 与三条缓动的取值）', () => {
    const r = at(120);
    // beat(0.26) = 62.4，进度 (120 - 62.4) / 21.6 = 2.666… → 钳到 1 → outQuint(1) = 1
    expect(r.ownP).toBe(1);
    // beat(0.38) = 91.2，dropP 的时长是 beat(0.08) = 19.2 帧：(120-91.2)/19.2 = 1.5 → 钳到 1
    expect(r.dropP).toBe(1);
    expect(r.aFill).toBe(0);
    // beat(0.48) = 115.2，时长 beat(0.1) = 24 帧：(120-115.2)/24 = 0.2 → inOutCubic(0.2) = 0.032
    expect(r.gapP).toBeCloseTo(inOutCubic(0.2), 12);
    // aGhost - aFill = 1，因此括号高度 = 1 × 0.032 × 268 = 8.576 → 8.6
    expect(r.bracketA.height).toBe('8.6');
    expect(r.bracketA.top).toBe('0.0');
    // 标签中点 = 0 + 8.576 / 2 = 4.288 → 钳到 44 → 44 - 20 = 24.0
    expect(r.bracketA.labelTop).toBe('24.0');
    // beat(0.56) = 134.4：第 120 帧还没开始
    expect(r.flatP).toBe(0);
    // beat(0.54) = 129.6：同样还没开始
    expect(r.fadeP).toBe(0);
    expect(r.panelAOpacity).toBe(1);
    // 引号：beat(0.02) = 4.8，时长 24 帧：(120-4.8)/24 > 1 → 1；不透明度 0.14
    expect(r.markP).toBe(1);
    expect(r.markShift).toBe('0.0');
  });

  it('左柱高度是 ownP * (1 - dropP) 的乘积，不是两条曲线各自取整', () => {
    // dropP 的起点是 beat(0.38)=91.2：第 100 帧时 (100-91.2)/19.2 = 0.4583…
    const dropP = inOutCubic((100 - 91.2) / 19.2);
    const r = at(100);
    expect(r.ownP).toBe(1);
    expect(r.dropP).toBeCloseTo(dropP, 12);
    expect(r.aFill).toBeCloseTo(1 * (1 - dropP), 12);
    // 虚线留在 ownP 的高度上，与柱高无关
    expect(r.ghostAHeight).toBe('268.0');
    expect(r.fillAHeight).toBe((r.aFill * TRACK_H).toFixed(1));
  });

  it('右侧柱子与虚线恒为 0，与帧号无关', () => {
    for (const frame of [0, 30, 90, 150, 200, 240]) {
      const r = at(frame);
      expect(r.fillBHeight).toBe('0.0');
      expect(r.ghostBHeight).toBe('0.0');
      expect(r.bracketB.top).toBe('262.0');
      expect(r.bracketB.height).toBe('6.0');
      expect(r.bracketB.labelTop).toBe('232.0');
      expect(r.flatOpacity).toBe(r.flatP);
    }
  });

  it('同输入同输出：连算两次逐字段相同', () => {
    const a = at(137);
    const b = at(137);
    expect(b).toEqual(a);
    // 也钉住「先算第 240 帧再算第 137 帧」与直接算第 137 帧相同（没有跨帧状态）
    at(240);
    expect(at(137)).toEqual(a);
  });

  it('幕长为 0 时不抛错（beat 全部落到第 0 帧）', () => {
    const empty = gapFrame({ localFrame: 0, sceneDurationFrames: 0 }, API, () => 0);
    expect(empty.ruleP).toBe(0);
    expect(empty.aFill).toBe(0);
    expect(Number.isFinite(empty.panelAOpacity)).toBe(true);
  });
});

describe('emphasisProgress（旧 emphasizeKey 的缺省档 at 0.7 / span 0.1）', () => {
  it('与 progress(f, beat(0.7), beat(0.1), inOutCubic) 一致', () => {
    // beat(0.7) = 168，beat(0.1) = 24：第 180 帧时 (180-168)/24 = 0.5 → inOutCubic(0.5) = 0.5
    expect(emphasisProgress({ ...SCENE, localFrame: 180 }, API, beatAt)).toBeCloseTo(0.5, 12);
    // 第 168 帧刚到起点
    expect(emphasisProgress({ ...SCENE, localFrame: 168 }, API, beatAt)).toBe(0);
    // 第 192 帧（168 + 24）走完
    expect(emphasisProgress({ ...SCENE, localFrame: 192 }, API, beatAt)).toBe(1);
    // 第 164 帧还在起点之前
    expect(emphasisProgress({ ...SCENE, localFrame: 164 }, API, beatAt)).toBe(0);
  });

  it('两端状态分别是 0 与 1，同输入同输出', () => {
    const zero = emphasisProgress({ ...SCENE, localFrame: 0 }, API, beatAt);
    const one = emphasisProgress({ ...SCENE, localFrame: 240 }, API, beatAt);
    expect(zero).toBe(0);
    expect(one).toBe(1);
    expect(emphasisProgress({ ...SCENE, localFrame: 240 }, API, beatAt)).toBe(one);
  });
});

describe('gapText（文案取自分镜，组件不存默认值）', () => {
  /**
   * 不带行内样式的强调标记：旧 `emphasize(text, phrases, true)` 的输出。
   * 这里直接用运行时的 `emphasisHtml`（`gapEmphasisHtml` 只是在它外面固定了
   * `underline` 与光晕上限），因此断言的是同一份标记。
   */
  const markup = (text: GapText) =>
    emphasisHtml(text.text, text.phrases, { underline: true });

  it('强调短语被包成 .key，并挂上底横线节点', () => {
    const text = gapText(
      { text: '选择消耗的\n是做决定的力气', emphasis: ['力气'] },
      {
        assumption: '以为需要',
        fact: '真正需要',
        dropLabel: '比较用掉',
        noDropLabel: '从未拥有',
      },
    );
    expect(markup(text)).toBe(
      '选择消耗的\n是做决定的<span class="key">力气<span class="key-underline"></span></span>',
    );
    expect(text.capA).toBe('以为需要');
    expect(text.capB).toBe('真正需要');
    expect(text.labelA).toBe('比较用掉');
    expect(text.labelB).toBe('从未拥有');
  });

  it('没命中短语时不多出节点', () => {
    const text = gapText({ text: '一句话', emphasis: ['不存在的词'] }, {});
    expect(markup(text)).toBe('一句话');
  });

  it('空数据不抛错：文案全为空串', () => {
    expect(() => gapText(undefined, undefined)).not.toThrow();
    expect(gapText(undefined, undefined)).toEqual({
      text: undefined,
      phrases: undefined,
      capA: '',
      capB: '',
      labelA: '',
      labelB: '',
    });
    expect(gapText({}, {})).toEqual(gapText(undefined, undefined));
    expect(markup(gapText(undefined, undefined))).toBe('');
  });

  it('文本里的尖括号被转义（强调短语是拼进标记里的）', () => {
    const text = gapText({ text: '<b>x</b>', emphasis: ['x'] }, undefined);
    expect(markup(text)).toBe('&lt;b&gt;<span class="key">x<span class="key-underline"></span></span>&lt;/b&gt;');
  });

  it('给出进度时行内样式落在节点上：预设下只写光晕档位，非预设下写 text-shadow', () => {
    const text = gapText({ text: '要自由', emphasis: ['自由'] }, {});
    const preset = gapEmphasisHtml(text, { progress: 0.5, preset: true, range: (v, f, t) => f + (t - f) * v });
    expect(preset).toContain('--a2v-emphasis-glow: 0.5000;');
    expect(preset).toContain('transform: scaleX(0.5000);');
    expect(preset).not.toContain('text-shadow');

    const plain = gapEmphasisHtml(text, { progress: 0.5, preset: false, range: (v, f, t) => f + (t - f) * v });
    expect(plain).toContain('text-shadow: 0 0 13.0px rgba(var(--a2v-accent-rgb), 0.110);');
    expect(plain).not.toContain('--a2v-emphasis-glow');
  });
});

describe('缓动名与旧实现同一口径', () => {
  it('本幕只用 outQuint 与 inOutCubic', () => {
    expect(EASE.out).toBe('outQuint');
    expect(EASE.symmetric).toBe('inOutCubic');
    // 独立复核两条曲线的手算值（防止 EASING 被改动而测试无感）
    expect(outQuint(0.5)).toBeCloseTo(0.96875, 12);
    expect(inOutCubic(0.25)).toBeCloseTo(0.0625, 12);
    expect(motionRange(0.5, -26, 0)).toBe(-13);
  });
});
