/**
 * exchange（结论幕）的纯函数契约。
 *
 * 这里**不渲染 React**（不引入 jsdom 与测试库）：能被抽帧对照算出差别的量——
 * 坐标、切线角、字号、逐字不透明度——全都是纯函数或纯数据，
 * 直接断言它们的取值比"挂一棵 DOM 再问它长什么样"更接近真正要守的东西。
 *
 * 三组断言：
 *   1. 两个端点与双向弧线的几何：取值与手算一致、同输入同输出；
 *   2. 逐字揭示的接线：`revealUnits` 的输入输出（单调不减、换行不计数、强调晚 6 帧）；
 *   3. 边界与空数据：进度量在 0 帧与幕末落在预期区间，空数据不抛错。
 */
import { describe, expect, it } from 'vitest';

import {
  EXCHANGE,
  EXCHANGE_ARC_LENGTH,
  EXCHANGE_ARROW_FALLBACK,
  EXCHANGE_GEOMETRY,
  EXCHANGE_LABEL_KEYS,
  EXCHANGE_NODES,
  EXCHANGE_REVEAL_BEAT,
  EXCHANGE_REVEAL_STAGGER_FRAMES,
  arcTangentDegrees,
  arrowPathData,
  exchangeFitFontSize,
  exchangeRevealUnits,
  quadraticPathData,
  readTokenPx,
} from '@/components/Exchange';
import {
  EASE,
  beat,
  createFigureApi,
  plainText,
  revealUnits,
  splitEmphasis,
  type FigureRuntime,
} from '@/runtime/figures';
import { drawPathStyle, progress, range, since } from '@/runtime/motion';

/** 造一个够用的运行时：组件只用得上 state/api/spec/data/preset 这几项。 */
function runtimeOf(
  partial: {
    localFrame?: number;
    sceneDurationFrames?: number;
    motion?: string;
    fps?: number;
    preset?: string;
    data?: Record<string, unknown>;
    labels?: Record<string, string>;
  } = {},
): FigureRuntime {
  const fps = partial.fps ?? 30;
  return {
    scene: { id: 'closing', type: 'conclusion', durationInFrames: 300, data: {} },
    sceneIndex: 5,
    sceneCount: 8,
    data: partial.data ?? {},
    spec: {
      kind: 'exchange',
      labels: partial.labels ?? { leftNode: '你', rightNode: '他' },
      params: {},
      motion: partial.motion ?? 'normal',
    },
    fps,
    preset: partial.preset,
    state: {
      localFrame: partial.localFrame ?? 0,
      sceneDurationFrames: partial.sceneDurationFrames ?? 300,
      motion: partial.motion ?? 'normal',
    },
    api: createFigureApi(fps),
  } as FigureRuntime;
}

/** 数值积分二次贝塞尔的长度：用来核对"声明长度 392 覆盖得住整条弧"。 */
function quadraticLength(
  from: readonly [number, number],
  control: readonly [number, number],
  to: readonly [number, number],
  steps = 20000,
): number {
  let length = 0;
  let previous: [number, number] = [from[0], from[1]];
  for (let i = 1; i <= steps; i += 1) {
    const t = i / steps;
    const mt = 1 - t;
    const x = mt * mt * from[0] + 2 * mt * t * control[0] + t * t * to[0];
    const y = mt * mt * from[1] + 2 * mt * t * control[1] + t * t * to[1];
    length += Math.hypot(x - previous[0], y - previous[1]);
    previous = [x, y];
  }
  return length;
}

/** 曲线在参数 t 处的点（用来断言弧线确实穿过控制点给出的中线）。 */
function quadraticPoint(
  from: readonly [number, number],
  control: readonly [number, number],
  to: readonly [number, number],
  t: number,
): [number, number] {
  const mt = 1 - t;
  return [
    mt * mt * from[0] + 2 * mt * t * control[0] + t * t * to[0],
    mt * mt * from[1] + 2 * mt * t * control[1] + t * t * to[1],
  ];
}

describe('exchange 的几何：两个端点与双向弧线', () => {
  it('端点圆心与半径与旧标记一致（左 150/150/88、右 738/150/88）', () => {
    expect(EXCHANGE_NODES.left).toEqual({ cx: 150, cy: 150, r: 88 });
    expect(EXCHANGE_NODES.right).toEqual({ cx: 738, cy: 150, r: 88 });
    expect(EXCHANGE_GEOMETRY.left).toEqual({ cx: 150, cy: 150, r: 88 });
    expect(EXCHANGE_GEOMETRY.right).toEqual({ cx: 738, cy: 150, r: 88 });
    // 两个端点标注的键就是 define('exchange', ["leftNode", "rightNode"]) 声明的那两个
    expect([...EXCHANGE_LABEL_KEYS]).toEqual(['leftNode', 'rightNode']);
  });

  it('两条弧的 d 串与 MARKUP_EXCHANGE 逐字符相同', () => {
    expect(
      quadraticPathData(
        EXCHANGE_GEOMETRY.arcTo.from,
        EXCHANGE_GEOMETRY.arcTo.control,
        EXCHANGE_GEOMETRY.arcTo.to,
      ),
    ).toBe('M262 118 Q445 66 628 118');
    expect(
      quadraticPathData(
        EXCHANGE_GEOMETRY.arcBack.from,
        EXCHANGE_GEOMETRY.arcBack.control,
        EXCHANGE_GEOMETRY.arcBack.to,
      ),
    ).toBe('M626 182 Q445 234 264 182');
  });

  it('两条弧都在 t=0.5 处取得旧标记写下的顶点，且端点就是圆的切点', () => {
    // 去程弧最高点 y=92（控制点 y=66 的中点），回程弧最低点 y=208
    expect(quadraticPoint(EXCHANGE_GEOMETRY.arcTo.from, EXCHANGE_GEOMETRY.arcTo.control, EXCHANGE_GEOMETRY.arcTo.to, 0.5)).toEqual([445, 92]);
    expect(quadraticPoint(EXCHANGE_GEOMETRY.arcBack.from, EXCHANGE_GEOMETRY.arcBack.control, EXCHANGE_GEOMETRY.arcBack.to, 0.5)).toEqual([445, 208]);

    /*
     * 弧的端点**不在圆上**，而是落在圆的近旁，两条弧还不对称：
     *   去程起点 (262,118) 距左圆心 (150,150)：sqrt(112² + 32²) ≈ 116.48
     *   去程终点 (628,118) 距右圆心 (738,150)：sqrt(110² + 32²) ≈ 114.56
     *   回程起点 (626,182) 距右圆心：sqrt(112² + 32²) ≈ 116.48
     *   回程终点 (264,182) 距左圆心：sqrt(114² + 32²) ≈ 118.41
     * 弧刻意起在圆的外侧、往上/下拱出去，箭镞与圆之间才留出可见间隙；
     * 四个距离互不相同是标记里本来就这样写的，不许"顺手对称化"。
     */
    const distance = (a: readonly [number, number], b: { cx: number; cy: number }) =>
      Math.hypot(a[0] - b.cx, a[1] - b.cy);
    expect(distance(EXCHANGE_GEOMETRY.arcTo.from, EXCHANGE_GEOMETRY.left)).toBeCloseTo(
      Math.hypot(112, 32),
      10,
    );
    expect(distance(EXCHANGE_GEOMETRY.arcTo.to, EXCHANGE_GEOMETRY.right)).toBeCloseTo(
      Math.hypot(110, 32),
      10,
    );
    expect(distance(EXCHANGE_GEOMETRY.arcBack.from, EXCHANGE_GEOMETRY.right)).toBeCloseTo(
      Math.hypot(112, 32),
      10,
    );
    expect(distance(EXCHANGE_GEOMETRY.arcBack.to, EXCHANGE_GEOMETRY.left)).toBeCloseTo(
      Math.hypot(114, 32),
      10,
    );
    // 去程端点都在圆心水平线之上（y=118），回程端点都在之下（y=182），上下对称
    expect(EXCHANGE_GEOMETRY.arcTo.from[1] - EXCHANGE_GEOMETRY.left.cy).toBe(-32);
    expect(EXCHANGE_GEOMETRY.arcTo.to[1] - EXCHANGE_GEOMETRY.right.cy).toBe(-32);
    expect(EXCHANGE_GEOMETRY.arcBack.from[1] - EXCHANGE_GEOMETRY.right.cy).toBe(32);
    expect(EXCHANGE_GEOMETRY.arcBack.to[1] - EXCHANGE_GEOMETRY.left.cy).toBe(32);
  });

  it('弧线在 0.5 处的斜率与切线角手算一致', () => {
    // 去程弧 0.5 处斜率 = (628-262)/(2*(445-262)) = 1 -> 45°
    const slopeTo =
      (EXCHANGE_GEOMETRY.arcTo.to[0] - EXCHANGE_GEOMETRY.arcTo.from[0]) /
      (2 * (EXCHANGE_GEOMETRY.arcTo.control[0] - EXCHANGE_GEOMETRY.arcTo.from[0]));
    expect(slopeTo).toBeCloseTo(1, 12);
    expect((Math.atan(slopeTo) * 180) / Math.PI).toBeCloseTo(45, 12);
    // 回程弧 0.5 处斜率 = (264-626)/(2*(445-626)) = 1 -> 45°（对称）
    const slopeBack =
      (EXCHANGE_GEOMETRY.arcBack.to[0] - EXCHANGE_GEOMETRY.arcBack.from[0]) /
      (2 * (EXCHANGE_GEOMETRY.arcBack.control[0] - EXCHANGE_GEOMETRY.arcBack.from[0]));
    expect(slopeBack).toBeCloseTo(1, 12);
  });

  it('箭镞的切线角 = atan2(终点−控制点)，两条弧一升一降', () => {
    // 去程：atan2(118-66, 628-445) = atan2(52, 183) ≈ 15.8627°
    expect(arcTangentDegrees(EXCHANGE_GEOMETRY.arcTo)).toBeCloseTo(
      (Math.atan2(52, 183) * 180) / Math.PI,
      12,
    );
    expect(arcTangentDegrees(EXCHANGE_GEOMETRY.arcTo)).toBeCloseTo(15.8627, 4);
    // 回程：atan2(182-234, 264-445) = atan2(-52, -181) -> 第三象限方向 ≈ -163.9738°
    expect(arcTangentDegrees(EXCHANGE_GEOMETRY.arcBack)).toBeCloseTo(
      (Math.atan2(-52, -181) * 180) / Math.PI,
      12,
    );
    expect(arcTangentDegrees(EXCHANGE_GEOMETRY.arcBack)).toBeCloseTo(-163.9710, 4);
    // 两条弧一升一降：去程略向上（正），回程指向左下（第三象限）
    expect(arcTangentDegrees(EXCHANGE_GEOMETRY.arcTo)).toBeGreaterThan(0);
    expect(arcTangentDegrees(EXCHANGE_GEOMETRY.arcBack)).toBeLessThan(-90);
  });

  it('箭镞三角的 d 由常量算出，兜底值与设计令牌一致', () => {
    expect(EXCHANGE_ARROW_FALLBACK).toEqual({ length: 34, half: 16 });
    expect(arrowPathData(EXCHANGE_ARROW_FALLBACK.length, EXCHANGE_ARROW_FALLBACK.half)).toBe(
      'M0 0 L-34 -16 L-34 16 Z',
    );
    // 令牌读出别的值时，三角跟着走——不允许出现第二处写死的箭镞尺寸
    expect(arrowPathData(48, 20)).toBe('M0 0 L-48 -20 L-48 20 Z');
  });

  it('读令牌：取不到节点、读不到值、非正数一律回落兜底', () => {
    expect(readTokenPx(null, '--fig-arrow-len', 34)).toBe(34);
    const element = {} as Element;
    // 有值时按令牌走：三角跟着设计层改档
    expect(readTokenPx(element, '--fig-arrow-len', 34, () => ' 48px')).toBe(48);
    // 读不到、空串、非正数、非数一律回落兜底（照抄 tokenPx 的判据）
    expect(readTokenPx(element, '--fig-arrow-len', 34, () => '')).toBe(34);
    expect(readTokenPx(element, '--fig-arrow-len', 34, () => '0px')).toBe(34);
    expect(readTokenPx(element, '--fig-arrow-len', 34, () => '-8px')).toBe(34);
    expect(readTokenPx(element, '--fig-arrow-len', 34, () => 'auto')).toBe(34);
    // 不同令牌各读各的，兜底值也各用各的
    expect(readTokenPx(element, '--fig-arrow-half', 16, () => '20px')).toBe(20);
  });

  it('弧线的显式长度 392 覆盖得住整条弧（同输入同输出）', () => {
    const lengthTo = quadraticLength(
      EXCHANGE_GEOMETRY.arcTo.from,
      EXCHANGE_GEOMETRY.arcTo.control,
      EXCHANGE_GEOMETRY.arcTo.to,
    );
    const lengthBack = quadraticLength(
      EXCHANGE_GEOMETRY.arcBack.from,
      EXCHANGE_GEOMETRY.arcBack.control,
      EXCHANGE_GEOMETRY.arcBack.to,
    );
    expect(lengthTo).toBeGreaterThan(360);
    expect(lengthTo).toBeLessThan(EXCHANGE_ARC_LENGTH);
    expect(lengthBack).toBeLessThan(EXCHANGE_ARC_LENGTH);

    // 画完（进度 1）时偏移为 0，一半时偏移正好是一半：`drawPathStyle` 的行为不许漂
    expect(drawPathStyle(1, EXCHANGE_ARC_LENGTH)).toEqual({
      strokeDasharray: '392',
      strokeDashoffset: '0',
      opacity: '1',
    });
    expect(drawPathStyle(0, EXCHANGE_ARC_LENGTH).strokeDashoffset).toBe('392');
    expect(drawPathStyle(0.5, EXCHANGE_ARC_LENGTH).strokeDashoffset).toBe('196');
    // 同输入同输出：连调用两次也完全一致
    expect(drawPathStyle(0.25, EXCHANGE_ARC_LENGTH)).toEqual(drawPathStyle(0.25, EXCHANGE_ARC_LENGTH));
  });

  it('字号：按最长一行自算，且落在未启用预设的夹取区间内', () => {
    // 先量出每条测试文案的字符数，再断言字号——避免"以为写了 9 个字其实是 10 个"
    const ten = '选择是双向的彼此成就';
    expect(Array.from(ten)).toHaveLength(10);
    expect(exchangeFitFontSize(ten)).toBe(88); // 888/10 = 88

    const thirteen = '你挑别人的时候别人也在挑你';
    expect(Array.from(thirteen)).toHaveLength(13);
    expect(exchangeFitFontSize(thirteen)).toBe(68); // 888/13 = 68

    // 超长行被抬到下限
    const long = '你挑别人的时候别人也在挑你这就是双向选择这不是单向的挑选';
    expect(Array.from(long).length).toBeGreaterThan(16);
    expect(exchangeFitFontSize(long)).toBe(EXCHANGE.MIN);

    // 更长的一行仍被夹在下限，不会出现比 MIN 更小的字号
    expect(exchangeFitFontSize('一'.repeat(80))).toBe(EXCHANGE.MIN);
    // 很短的一行被夹在上限
    expect(exchangeFitFontSize('双向')).toBe(EXCHANGE.MAX);
    // 取最长的一行，而不是总字数：888/9 = 98.67 → 98，再被 MAX=96 夹住
    expect(exchangeFitFontSize('短\n这是一个比较长的行')).toBe(
      Math.max(EXCHANGE.MIN, Math.min(EXCHANGE.MAX, Math.floor(EXCHANGE.WIDTH / 9))),
    );
    // 空数据不抛错，落在区间内
    expect(exchangeFitFontSize('')).toBe(EXCHANGE.MAX);
    expect(exchangeFitFontSize(undefined)).toBe(EXCHANGE.MAX);
    // 同输入同输出
    expect(exchangeFitFontSize('双向')).toBe(exchangeFitFontSize('双向'));
  });

  it('字号：启用预设时从字号阶自大到小挑第一个放得下的档位', () => {
    const levels = [
      { name: 'display', size: 120 },
      { name: 'headline', size: 96 },
      { name: 'title', size: 76 },
      { name: 'body', size: 40 },
    ];
    // 10 个字：120*10=1200 与 96*10=960 都放不下，76*10=760 ≤ 888 -> 取 76（阶上的值）
    const ten = '选择是双向的彼此成就';
    expect(Array.from(ten)).toHaveLength(10);
    expect(exchangeFitFontSize(ten, { preset: 'keynote', levels })).toBe(76);
    // 13 个字：76*13=988 放不下，40*13=520 放得下 -> 40
    const thirteen = '你挑别人的时候别人也在挑你';
    expect(exchangeFitFontSize(thirteen, { preset: 'keynote', levels })).toBe(40);
    // 连 FLOOR 都放不下时仍取 FLOOR（溢出交给闸门报），不返回越界的自算值
    const tiny = [
      { name: 'headline', size: 96 },
      { name: 'body', size: 40 },
    ];
    expect(exchangeFitFontSize('一二三四五六七八九十', { preset: 'keynote', levels: tiny })).toBe(40);
    // 未启用预设时自算（68）与预设路径（40）不同，说明两条分支确实都在
    expect(exchangeFitFontSize(thirteen)).not.toBe(
      exchangeFitFontSize(thirteen, { preset: 'keynote', levels }),
    );
  });
});

describe('exchange 的逐字揭示接线', () => {
  const text = '你挑人\n人也在挑你';
  const phrases = ['人也在挑你'];

  it('结构：每个强调/普通片段一个单位，每个字一个 isBreak 标记正确的字符节点', () => {
    const units = revealUnits(text, phrases, { frame: 0, startFrame: 0, staggerFrames: 2 });
    expect(units.map((unit) => unit.key)).toEqual([false, true]);
    // 换行符是独立字符节点，并且被标成 isBreak
    const breakChars = units.flatMap((unit) => unit.chars.filter((item) => item.isBreak));
    expect(breakChars).toHaveLength(1);
    expect(breakChars[0]!.char).toBe('\n');
    // 换行符占位但恒为可见，不参与不透明度计算
    expect(breakChars[0]!.opacity).toBe(1);
    // 与 splitEmphasis 的切分一致（同一份规则，不是复制的一份实现）
    expect(units.map((unit) => unit.key)).toEqual(
      splitEmphasis(text, phrases).map((unit) => unit.key),
    );
  });

  it('不透明度随帧号单调不减，且从第 0 帧到幕末落在 0..1', () => {
    const flat = (frame: number) =>
      revealUnits(text, phrases, { frame, startFrame: 0, staggerFrames: 2 })
        .flatMap((unit) => unit.chars)
        .filter((item) => !item.isBreak)
        .map((item) => item.opacity);

    let previous = flat(0);
    for (let frame = 0; frame <= 40; frame += 1) {
      const current = flat(frame);
      expect(current).toHaveLength(previous.length);
      current.forEach((opacity, index) => {
        expect(opacity).toBeGreaterThanOrEqual(previous[index]!);
        expect(opacity).toBeGreaterThanOrEqual(0);
        expect(opacity).toBeLessThanOrEqual(1);
      });
      previous = current;
    }
    // 幕末（远超最后一个字的起始帧）全部可见
    expect(flat(200).every((opacity) => opacity === 1)).toBe(true);
  });

  it('强调片段整体比正文晚 6 帧，换行不占序号', () => {
    // 文本 = '你挑人\n' + '人也在挑你'：换行落在普通片段里，前 3 个可见字是正文
    const layout = revealUnits(text, phrases, { frame: 0, startFrame: 0, staggerFrames: 2 });
    expect(layout.map((unit) => unit.key)).toEqual([false, true]);
    expect(Array.from(splitEmphasis(text, phrases)[0]!.text)).toEqual(['你', '挑', '人', '\n']);

    const at = (frame: number) =>
      revealUnits(text, phrases, { frame, startFrame: 0, staggerFrames: 2 })
        .flatMap((unit) => unit.chars)
        .filter((item) => !item.isBreak);

    // 正文第 3 个字：起点 0 + 2*2 = 4 帧。第 4 帧那一帧的进度是 (4-4)/2 = 0，
    // 第 5 帧 0.5，第 6 帧走满
    expect(at(3)[2]!.opacity).toBe(0);
    expect(at(4)[2]!.opacity).toBe(0);
    expect(at(5)[2]!.opacity).toBe(0.5);
    expect(at(6)[2]!.opacity).toBe(1);

    // 强调片段首字：可见序号 3（换行不计数）+ 6 帧延迟 -> 起点 6 + 6 = 12 帧
    expect(at(11)[3]!.opacity).toBe(0);
    expect(at(12)[3]!.opacity).toBe(0);
    expect(at(13)[3]!.opacity).toBe(0.5);
    expect(at(14)[3]!.opacity).toBe(1);

    /*
     * "晚 6 帧"用输入输出来断言，而不是复制实现里的常数：
     * 同一序号（第 4 个可见字）若属正文，起点是 6；属强调，起点是 12。差 6 帧。
     */
    const plainOnly = revealUnits('四个字的正文', undefined, {
      frame: 12,
      startFrame: 0,
      staggerFrames: 2,
    })
      .flatMap((unit) => unit.chars)
      .filter((item) => !item.isBreak);
    expect(plainOnly[3]!.opacity).toBe(1);
    // 对照：同一帧、同一序号位置，出现在强调片段里就还没亮
    expect(at(12)[3]!.opacity).toBe(0);

    // 找不到强调词时整段都是普通片段，没有延迟
    const noMatch = revealUnits(text, ['不存在的词'], { frame: 12, startFrame: 0, staggerFrames: 2 });
    expect(noMatch.every((unit) => !unit.key)).toBe(true);
    expect(noMatch.flatMap((unit) => unit.chars).filter((item) => !item.isBreak)[3]!.opacity).toBe(1);
  });

  it('接线：起始帧取 beat(state, 0.02)、步进 2 帧，与旧实现同一组参数', () => {
    const runtime = runtimeOf({ localFrame: 30, sceneDurationFrames: 300 });
    const units = exchangeRevealUnits(runtime, text, phrases);
    expect(units).toEqual(
      revealUnits(text, phrases, {
        frame: runtime.state.localFrame,
        startFrame: beat(runtime, EXCHANGE_REVEAL_BEAT),
        staggerFrames: EXCHANGE_REVEAL_STAGGER_FRAMES,
      }),
    );
    // 参数本身：步进 2 帧、起始点 0.02
    expect(EXCHANGE_REVEAL_STAGGER_FRAMES).toBe(2);
    expect(EXCHANGE_REVEAL_BEAT).toBeCloseTo(0.02, 12);
    /*
     * 30 帧时全部走满：起始点 0.02×300 = 6，最大序号 7（共 8 个可见字）
     * 对应 6 + 7×2 = 20，强调片段再晚 6 帧 = 26，都早于 30。
     */
    const visible = units.flatMap((unit) => unit.chars).filter((item) => !item.isBreak);
    expect(visible).toHaveLength(8);
    expect(visible.every((item) => item.opacity === 1)).toBe(true);
    /*
     * 20 帧时还差最后几个字：序号 3（强调片段首字）起点 6 + 6 + 6 = 18，已走满；
     * 序号 6 起点 6 + 12 + 6 = 24，尚未开始——强调片段整体晚 6 帧就体现在这里。
     */
    const early = exchangeRevealUnits(
      runtimeOf({ localFrame: 20, sceneDurationFrames: 300 }),
      text,
      phrases,
    )
      .flatMap((unit) => unit.chars)
      .filter((item) => !item.isBreak);
    expect(early[3]!.opacity).toBe(1);
    expect(early[6]!.opacity).toBe(0);
  });

  it('空文本 / 非字符串输入不抛错，也不产生多余节点', () => {
    const empty = exchangeRevealUnits(runtimeOf(), undefined, undefined);
    expect(empty.flatMap((unit) => unit.chars)).toHaveLength(0);
    expect(exchangeRevealUnits(runtimeOf(), '', []).flatMap((unit) => unit.chars)).toHaveLength(0);
    // 数字之类的非字符串一律按空串处理，而不是画出 "undefined"
    expect(exchangeRevealUnits(runtimeOf(), 42, undefined).flatMap((unit) => unit.chars)).toHaveLength(
      plainText(42).length,
    );
    expect(plainText(undefined)).toBe('');
  });
});

describe('exchange 的边界帧与节奏', () => {
  it('两端点入场：第 0 帧进度为 0、幕末为 1，且左右错开', () => {
    const runtime = runtimeOf({ localFrame: 0 });
    const left = since(0, beat(runtime, 0.2), runtime.fps);
    const right = since(0, beat(runtime, 0.26), runtime.fps);
    expect(left).toBe(0);
    expect(right).toBe(0);

    const last = runtimeOf({ localFrame: 299 });
    expect(since(299, beat(last, 0.2), last.fps)).toBeGreaterThan(0);
    expect(since(299, beat(last, 0.26), last.fps)).toBeGreaterThan(0);
    // 左右起点差 0.06 幕长：左先右后
    expect(beat(last, 0.26)).toBeGreaterThan(beat(last, 0.2));
  });

  it('弧线、箭镞与行动句的进度在 0 帧与幕末都落在 0..1', () => {
    const frames = [0, 1, 90, 298, 299];
    for (const frame of frames) {
      const runtime = runtimeOf({ localFrame: frame, sceneDurationFrames: 300 });
      const values = [
        // 两条弧：0.36 / 0.44 起，时长 0.1 幕长，outCubic
        progress(frame, beat(runtime, 0.36), beat(runtime, 0.1), EASE.soft),
        progress(frame, beat(runtime, 0.44), beat(runtime, 0.1), EASE.soft),
        // 两个箭镞：0.46 / 0.54 起，14 帧，outQuint
        progress(frame, beat(runtime, 0.46), 14, EASE.out),
        progress(frame, beat(runtime, 0.54), 14, EASE.out),
        // 重点光：0.56 起，0.1 幕长，inOutCubic
        progress(frame, beat(runtime, 0.56), beat(runtime, 0.1), EASE.symmetric),
        // 行动句：0.64 起，28 帧，outQuint（以及它的微动门控 40 帧）
        progress(frame, beat(runtime, 0.64), 28, EASE.out),
        progress(frame, beat(runtime, 0.64), 40, EASE.symmetric),
      ];
      for (const value of values) {
        expect(value).toBeGreaterThanOrEqual(0);
        expect(value).toBeLessThanOrEqual(1);
      }
      // 幕末所有进度都走满
      if (frame === 299) {
        expect(values.slice(0, 6).every((value) => value === 1)).toBe(true);
      }
    }
    // 第 0 帧：两条弧与两个箭镞都还没出现
    const zero = runtimeOf({ localFrame: 0, sceneDurationFrames: 300 });
    expect(progress(0, beat(zero, 0.36), beat(zero, 0.1), EASE.soft)).toBe(0);
    expect(progress(0, beat(zero, 0.46), 14, EASE.out)).toBe(0);
  });

  it('行动句的位移吃线性秒数、从 34px 收敛到 0（不过冲，clamp: false）', () => {
    const runtime = runtimeOf({ localFrame: 0, sceneDurationFrames: 300, fps: 30 });
    const shiftAt = (frame: number) =>
      range(since(frame, beat(runtime, 0.64), runtime.fps), 34, 0, { clamp: false });
    expect(shiftAt(0)).toBe(34);
    expect(shiftAt(beat(runtime, 0.64))).toBe(34);
    expect(shiftAt(beat(runtime, 0.64) + 30)).toBe(0);
    // clamp:false 的意义：开始之前要给 34，而不是被钳回区间端点之外
    expect(shiftAt(beat(runtime, 0.64) - 10)).toBe(34);
  });

  it('空数据（没有 text/action/emphasis）不抛错，字号与揭示都能算出来', () => {
    const runtime = runtimeOf({ data: {}, localFrame: 10 });
    const text = plainText(runtime.data['text']);
    expect(text).toBe('');
    expect(() => exchangeFitFontSize(text, { preset: runtime.preset })).not.toThrow();
    expect(() => exchangeRevealUnits(runtime, runtime.data['text'], undefined)).not.toThrow();
    /*
     * 空文本的揭示结果是**一个没有字的普通片段**，不是空数组——这与旧实现一致：
     * `splitEmphasis('')` 返回 `[{ text: '', key: false }]`，`revealKeyChars` 于是造出
     * 一个空的 `span.plain`。断言这一条是为了防止有人"顺手"把空串特判成不渲染：
     * 那会改变文档结构，抽帧对照能看出来（少一个 inline 元素会影响换行）。
     */
    const emptyUnits = exchangeRevealUnits(runtime, runtime.data['text'], undefined);
    expect(emptyUnits).toEqual([{ key: false, chars: [] }]);
    expect(emptyUnits.flatMap((unit) => unit.chars)).toHaveLength(0);
    // 标注缺失时端点文字为空串，而不是 "undefined"
    expect(plainText(runtime.spec.labels['leftNode'])).toBe('你');
    expect(plainText(({} as Record<string, string | undefined>)['nope'])).toBe('');
  });
});
