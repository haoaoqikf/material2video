/**
 * 阶梯幕的纯函数测试：**手算核对**、幂等、以及边界输入不炸。
 *
 * 这一份不渲染组件、不引进 jsdom：阶梯的价值一半在几何与时间线上，
 * 那一半是纯数值，可以脱离 DOM 逐值核对。手算用的是**旧实现里的常量与算式**
 * （`figures.js` 第 1316–1327、1360–1463 行），所以这里的期望值不是「跑一遍
 * 看看是多少」抄下来的——它们全部能由 888 / 152 / 64 / 545 / 100 / 210 / 330 /
 * 460 与 `[0.07, 0.24, 0.48, 0.73]` 手推出来，写死在断言里。
 *
 * 三处刻意保留的旧行为也在这里钉住：
 * - 第 5 根台阶起高度回退 120（旧 `STAIRS.HEIGHTS[index] || 120`）；
 * - 时间点表外回退 0.73（旧 `START[index] === undefined ? 0.73 : ...`）；
 * - 空 `items` 不抛错：焦点为 0、跳跃表为空、落点仍是第一格柱顶。
 */
import { describe, expect, it } from 'vitest';

import {
  STAIRS,
  activeStairStep,
  normalizeStairItems,
  stairArrowClassName,
  stairBarHeight,
  stairBarRect,
  stairCaptionOpacity,
  stairCaptionText,
  stairCenter,
  stairFlipOpacity,
  stairFlipProgress,
  stairFlipState,
  stairFlipText,
  stairHaloOpacity,
  stairHeight,
  stairHopArc,
  stairHopAt,
  stairLabelOpacity,
  stairLabelPoint,
  stairMarkerAttrs,
  stairMarkerOpacity,
  stairMarkerPosition,
  stairNoteOpacity,
  stairNotePoint,
  stairStartFraction,
  stairStartFrame,
  stairTotalWidth,
  type StairTimeline,
} from '@/components/Stairs';
import type { FigureRuntime } from '@/runtime/figures';
import { springBy } from '@/runtime/motion';

/* ------------------------------------------------------------------ *
 * 手算的对照值
 * ------------------------------------------------------------------ */

/** 四根柱子的占用宽度：4 × 152 + 3 × 64 = 608 + 192 = 800。 */
const TOTAL_W = 800;
/** 居中后的左边界：(888 − 800) / 2 = 44，也就是第一根柱子的左边。 */
const LEFT = 44;
/** 柱心的步长：152 + 64 = 216。 */
const STEP = 216;
/** 四根柱子的手算柱心：44 + 76 + i × 216。 */
const CENTERS_4 = [120, 336, 552, 768];

/** 旧实现三条曲线的解析式，用来手算「第几帧应该是多少」。 */
const easeOutQuint = (t: number): number => 1 - (1 - t) ** 5;
const easeInOutCubic = (t: number): number =>
  t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;

/** 与组件里同样的曲线，用来构造跳跃中途的期望值。 */
const hopOf = (frame: number, hopStart: number, hopFrames: number): number => {
  const t = (frame - hopStart) / hopFrames;
  const clamped = t < 0 ? 0 : t > 1 ? 1 : t;
  return easeOutQuint(clamped);
};

describe('阶梯几何（手算）', () => {
  it('占用宽度与居中左边界', () => {
    expect(stairTotalWidth()).toBe(TOTAL_W);
    expect(stairTotalWidth(4)).toBe(TOTAL_W);
    // 居中：888 减去占用宽度再对半分，就是第一根柱子的左边
    expect((888 - stairTotalWidth()) / 2).toBe(LEFT);
    expect(stairBarRect(0, 0).x).toBe(LEFT);
    // 两根：(888 − (2×152 + 64)) / 2 = (888 − 368) / 2 = 260
    expect(stairTotalWidth(2)).toBe(368);
    // 一根没有间隔：(888 − 152) / 2 = 368
    expect(stairTotalWidth(1)).toBe(152);
  });

  it('柱心按「宽 + 间隔」递推', () => {
    expect(CENTERS_4.map((_v, index) => stairCenter(index))).toEqual(CENTERS_4);
    // 表外继续按同一步长排下去（旧实现的 stairCenter 不做任何限制）
    expect(stairCenter(4)).toBe(768 + STEP);
  });

  it('柱高表与表外回退 120', () => {
    expect(stairHeight(0)).toBe(100);
    expect(stairHeight(1)).toBe(210);
    expect(stairHeight(2)).toBe(330);
    expect(stairHeight(3)).toBe(460);
    // 关键的一条：第 5 根起不是 0、不是抛错，而是 120（旧 `|| 120`）
    expect(stairHeight(4)).toBe(120);
    expect(stairHeight(9)).toBe(120);
  });

  it('柱子的矩形：高度只改上边，x 与宽不变', () => {
    expect(stairBarRect(0, 0)).toEqual({ x: 120 - 76, y: 545 });
    expect(stairBarRect(0, 100)).toEqual({ x: 44, y: 445 });
    expect(stairBarRect(3, 460)).toEqual({ x: 768 - 76, y: 85 });
  });

  it('实际高度 = 目标高度 × 钳到 0..1 的弹簧进度', () => {
    // 弹簧从 0 长起：第一帧高度必须是 0，而不是「先给出最终高度再淡入」
    expect(stairBarHeight(0, 0)).toBe(0);
    expect(stairBarHeight(1, 0.5)).toBe(105); // 210 × 0.5
    expect(stairBarHeight(3, 1)).toBe(460);
    // 过冲的进度不许把柱子拔出高度表（钳到 1）
    expect(stairBarHeight(3, 1.0002)).toBe(460);
    expect(stairBarHeight(2, -0.5)).toBe(0);
    // 第 5 根走的是 120 那条回退
    expect(stairBarHeight(4, 1)).toBe(120);
  });

  it('注写随柱顶抬高 44px，标签固定在基线下 52px', () => {
    expect(stairNotePoint(0, 0)).toEqual({ x: 120, y: 545 - 0 - 44 });
    expect(stairNotePoint(0, 100)).toEqual({ x: 120, y: 401 });
    expect(stairNotePoint(2, 330)).toEqual({ x: 552, y: 171 });
    // 标签不跟着柱子动：旧实现只在 buildOnce 里写一次 y
    expect(stairLabelPoint(0)).toEqual({ x: 120, y: 545 + 52 });
    expect(stairLabelPoint(3)).toEqual({ x: 768, y: 597 });
  });

  it('四根柱子横向不重叠、严格递增', () => {
    const rects = CENTERS_4.map((_v, index) => stairBarRect(index, stairHeight(index)));
    for (let index = 0; index < rects.length; index += 1) {
      expect(rects[index]!.x + STAIRS.BAR_W).toBeLessThanOrEqual(
        index + 1 < rects.length ? rects[index + 1]!.x : Number.POSITIVE_INFINITY,
      );
    }
  });
});

describe('说明文字与三处淡入', () => {
  it('注写：弹簧过 0.55 后按斜率 2.2 拉开', () => {
    expect(stairNoteOpacity(0)).toBe(0);
    expect(stairNoteOpacity(0.55)).toBe(0);
    // (0.75 − 0.55) × 2.2 = 0.44（浮点表示下用 closeTo 更稳）
    expect(stairNoteOpacity(0.75)).toBeCloseTo(0.44, 12);
    expect(stairNoteOpacity(1)).toBeCloseTo(0.99, 12);
    // 弹簧过冲也不许把不透明度推过 1
    expect(stairNoteOpacity(1.4)).toBe(1);
  });

  it('标签：弹簧过 0.3 后按斜率 2 拉开，比注写早', () => {
    expect(stairLabelOpacity(0.3)).toBe(0);
    expect(stairLabelOpacity(0.8)).toBeCloseTo(1, 12);
    expect(stairLabelOpacity(0.55)).toBeCloseTo(0.5, 12);
    expect(stairLabelOpacity(2)).toBe(1);
  });

  it('说明文字封顶 0.94', () => {
    expect(stairCaptionOpacity(0)).toBe(0);
    expect(stairCaptionOpacity(0.5)).toBeCloseTo(0.47, 12);
    expect(stairCaptionOpacity(1)).toBe(0.94);
    expect(stairCaptionOpacity(1.2)).toBe(0.94);
  });

  it('小球的光晕是小球透明度的 0.9', () => {
    expect(stairMarkerOpacity(0)).toBe(0);
    expect(stairMarkerOpacity(0.5)).toBe(0.5);
    expect(stairMarkerOpacity(2)).toBe(1);
    expect(stairHaloOpacity(1)).toBeCloseTo(0.9, 12);
    expect(stairHaloOpacity(0.5)).toBeCloseTo(0.45, 12);
  });

  it('说明文字取当前焦点那一条，越界为空串', () => {
    const items = normalizeStairItems(['第一次', { label: '第二次', desc: '第二次的说明' }]);
    expect(stairCaptionText(items, 0)).toBe('第一次');
    expect(stairCaptionText(items, 1)).toBe('第二次的说明');
    expect(stairCaptionText(items, 2)).toBe('');
    expect(stairCaptionText([], 0)).toBe('');
  });
});

describe('时间点换算（手算）', () => {
  it('比例点表与表外回退 0.73', () => {
    expect([0, 1, 2, 3].map(stairStartFraction)).toEqual([0.07, 0.24, 0.48, 0.73]);
    expect(stairStartFraction(4)).toBe(0.73);
    expect(stairStartFraction(99)).toBe(0.73);
  });

  it('比例点换算成帧号：比例 × 幕长 ÷ 节奏倍率', () => {
    // 假运行时只需要 state：换算公式与组件其余部分无关
    const runtime = {
      state: { localFrame: 0, sceneDurationFrames: 240, motion: 'normal' },
    } as unknown as FigureRuntime;
    expect(stairStartFrame(runtime, 0)).toBeCloseTo(16.8, 12); // 0.07 × 240
    expect(stairStartFrame(runtime, 3)).toBeCloseTo(175.2, 12); // 0.73 × 240
    expect(stairStartFrame(runtime, 4)).toBeCloseTo(175.2, 12); // 表外回退
  });

  it('节奏越快，同一个比例点越早到达', () => {
    const steady = {
      state: { localFrame: 0, sceneDurationFrames: 300, motion: 'normal' },
    } as unknown as FigureRuntime;
    const impact = {
      state: { localFrame: 0, sceneDurationFrames: 300, motion: 'impact' },
    } as unknown as FigureRuntime;
    expect(stairStartFrame(impact, 2)).toBeLessThan(stairStartFrame(steady, 2));
    expect(stairStartFrame(impact, 2)).toBeCloseTo((0.48 * 300) / 1.24, 12);
  });

  it('焦点逐级推进，后面的命中覆盖前面的', () => {
    const starts = [16, 57, 115, 175];
    expect(activeStairStep(0, starts)).toBe(0);
    expect(activeStairStep(16, starts)).toBe(0); // 起点当帧即命中第一级
    expect(activeStairStep(56, starts)).toBe(0);
    expect(activeStairStep(57, starts)).toBe(1);
    expect(activeStairStep(120, starts)).toBe(2);
    expect(activeStairStep(175, starts)).toBe(3);
    expect(activeStairStep(1000, starts)).toBe(3); // 收尾时焦点仍在最后一级
  });

  it('items 数为 2–5 时焦点都在合法区间内', () => {
    for (let count = 2; count <= 5; count += 1) {
      const starts = Array.from({ length: count }, (_v, index) => 16 + index * 40);
      for (const frame of [0, 1, 25, 80, 200, 500]) {
        const active = activeStairStep(frame, starts, count);
        expect(active).toBeGreaterThanOrEqual(0);
        expect(active).toBeLessThan(count);
      }
      // 最后一帧的焦点必须是最后一根（否则末段的翻转视角没有落点）
      expect(activeStairStep(500, starts, count)).toBe(count - 1);
    }
  });
});

describe('小球的跳跃（手算）', () => {
  it('跳跃进度：起跳前为 0，整段走完为 1', () => {
    expect(stairHopAt(40, 41, 24)).toBe(0);
    expect(stairHopAt(41, 41, 24)).toBe(0);
    // 半程的时间点上，进度**不是** 0.5 而是 1 − 0.5⁵ = 0.96875：
    // 这一跳走的是 outQuint，前半段就把大部分位移走完了
    expect(stairHopAt(53, 41, 24)).toBeCloseTo(0.96875, 12);
    expect(stairHopAt(65, 41, 24)).toBe(1);
    expect(stairHopAt(80, 41, 24)).toBe(1);
    // 跳跃时长为 0 时不除零：起跳即到位
    expect(stairHopAt(41, 41, 0)).toBe(1);
  });

  it('跳跃进度吃的是 outQuint，不是线性', () => {
    expect(stairHopAt(47, 41, 24)).toBeCloseTo(easeOutQuint(0.25), 12);
    expect(stairHopAt(59, 41, 24)).toBeCloseTo(easeOutQuint(0.75), 12);
  });

  it('跳跃弧：x 线性插值，y 再抬一个正弦拱', () => {
    const from = { x: 120, y: 445 };
    const to = { x: 336, y: 335 };
    expect(stairHopArc(from, to, 0)).toEqual({ x: 120, y: 445 });
    expect(stairHopArc(from, to, 1)).toEqual({ x: 336, y: 335 });
    // 半程：x 在中点，y 在高度中点之上再抬 96
    expect(stairHopArc(from, to, 0.5).x).toBeCloseTo(228, 12);
    expect(stairHopArc(from, to, 0.5).y).toBeCloseTo((445 + 335) / 2 - 96, 12);
  });

  it('落点：第一格柱顶起步，逐格落在该格柱顶', () => {
    const hopStarts = [16.8 - 12, 57.6 - 12, 115.2 - 12, 175.2 - 12];
    const hopFrames = 12;
    // 起点：`stairCenter(0)` 与 `BASE − HEIGHTS[0]`
    expect(stairMarkerPosition(0, hopStarts, hopFrames)).toEqual({ x: 120, y: 445 });
    // 第一跳过程中：用的是「上一格柱顶 → 本格柱顶」这条弧
    const mid = stairMarkerPosition(hopStarts[1]! + 6, hopStarts, hopFrames);
    const expected = stairHopArc(
      { x: 120, y: 545 - 100 },
      { x: 336, y: 545 - 210 },
      hopOf(hopStarts[1]! + 6, hopStarts[1]!, hopFrames),
    );
    expect(mid.x).toBeCloseTo(expected.x, 12);
    expect(mid.y).toBeCloseTo(expected.y, 12);
    // 整段走完之后：正好停在当前这一格的柱顶（插值到 1 会带一点浮点尾巴，
    // 因此这里比到 12 位小数，而不是要求逐位相等）
    const landed = stairMarkerPosition(1000, hopStarts, hopFrames);
    expect(landed.x).toBeCloseTo(768, 12);
    expect(landed.y).toBeCloseTo(545 - 460, 12);
  });

  it('还没起跳的格子不会把小球提前拉过去', () => {
    const hopStarts = [16.8 - 12, 57.6 - 12, 115.2 - 12, 175.2 - 12];
    // 第三格尚未起跳时，小球仍在第二格柱顶（不是第三格）
    const pos = stairMarkerPosition(hopStarts[2]! - 1, hopStarts, 12);
    expect(pos).toEqual({ x: 336, y: 545 - 210 });
  });

  it('items 数为 2–5 时不越界，空 items 停在第一格', () => {
    for (let count = 2; count <= 5; count += 1) {
      const hopStarts = Array.from({ length: count }, (_v, index) => 10 + index * 30);
      for (const frame of [0, 5, 40, 100, 400]) {
        const pos = stairMarkerPosition(frame, hopStarts, 12, count);
        expect(Number.isFinite(pos.x)).toBe(true);
        expect(Number.isFinite(pos.y)).toBe(true);
      }
      // 第 5 根走 120 那条回退（否则这里会取到 undefined）
      const last = stairMarkerPosition(400, hopStarts, 12, count);
      expect(last.y).toBeCloseTo(545 - stairHeight(count - 1), 12);
    }
    // 空 items：起点仍是第一格柱顶，且不抛错
    expect(stairMarkerPosition(123, [], 12, 0)).toEqual({ x: 120, y: 445 });
  });

  it('坐标写成一位小数（与旧 toFixed(1) 同形）', () => {
    expect(stairMarkerAttrs({ x: 120, y: 445 })).toEqual({ cx: '120.0', cy: '445.0' });
    expect(stairMarkerAttrs({ x: 227.96, y: 300.04 })).toEqual({ cx: '228.0', cy: '300.0' });
    expect(stairMarkerAttrs({ x: 12.34, y: 56.78 })).toEqual({ cx: '12.3', cy: '56.8' });
  });
});

describe('末段翻转（手算）', () => {
  it('进度：`beat(0.84)` 起横跨 `beat(0.1)`，吃 inOutCubic', () => {
    expect(stairFlipProgress(201, 201, 24)).toBe(0);
    expect(stairFlipProgress(213, 201, 24)).toBeCloseTo(0.5, 12);
    expect(stairFlipProgress(213, 201, 24)).toBeCloseTo(easeInOutCubic(0.5), 12);
    expect(stairFlipProgress(225, 201, 24)).toBe(1);
    expect(stairFlipProgress(400, 201, 24)).toBe(1);
    // 时长为 0 时不除零
    expect(stairFlipProgress(201, 201, 0)).toBe(1);
    expect(stairFlipProgress(200, 201, 0)).toBe(0);
  });

  it('翻转判据：进度过半才换视角', () => {
    expect(stairFlipState(0)).toBe('before');
    expect(stairFlipState(0.5)).toBe('before'); // 严格大于 0.5，正好一半不算翻
    expect(stairFlipState(0.5001)).toBe('after');
    expect(stairFlipState(1)).toBe('after');
  });

  it('文案与箭头朝向同时换手', () => {
    expect(stairFlipText(0, '公司在挑你', '你在挑公司')).toBe('公司在挑你');
    expect(stairFlipText(1, '公司在挑你', '你在挑公司')).toBe('你在挑公司');
    expect(stairArrowClassName(0)).toBe('flip-arrow is-left');
    expect(stairArrowClassName(1)).toBe('flip-arrow is-right');
  });

  it('翻转条的透明度与视角是两条独立的线（先露出来、后翻）', () => {
    expect(stairFlipOpacity(0)).toBe(0);
    expect(stairFlipOpacity(1)).toBe(1);
    // 透明度封顶在 1：`beat(0.8)` 起 20 帧走完，之后一直 1
    expect(stairFlipOpacity(2)).toBe(1);
  });
});

describe('边界：items 数超出建议区间与空 items', () => {
  it('字符串与对象混排都能归一', () => {
    expect(normalizeStairItems(['第一', { label: '第二', desc: '说明' }])).toEqual([
      { label: '第一', note: '', desc: '第一' },
      { label: '第二', note: '', desc: '说明' },
    ]);
    expect(normalizeStairItems([{ label: '第一', note: '注', desc: '说明' }])).toEqual([
      { label: '第一', note: '注', desc: '说明' },
    ]);
  });

  it('缺字段补空串，不出现 undefined 字样', () => {
    expect(normalizeStairItems([{}])).toEqual([{ label: '', note: '', desc: '' }]);
    expect(normalizeStairItems([{ label: '只有标签' }])).toEqual([
      { label: '只有标签', note: '', desc: '' },
    ]);
  });

  it('空 items 与非法 items 都不抛错', () => {
    expect(normalizeStairItems([])).toEqual([]);
    expect(normalizeStairItems(undefined)).toEqual([]);
    expect(normalizeStairItems(null)).toEqual([]);
    expect(normalizeStairItems('不是数组')).toEqual([]);
    expect(normalizeStairItems(5)).toEqual([]);
    // 空表下焦点是 0，跳跃表为空，落点仍在第一格
    expect(activeStairStep(0, [], 0)).toBe(0);
    expect(activeStairStep(999, [], 0)).toBe(0);
    expect(stairMarkerPosition(0, [], 12, 0)).toEqual({ x: 120, y: 445 });
  });

  it('5 根（超出建议区间上限）时高度与柱心仍可算', () => {
    expect([0, 1, 2, 3, 4].map(stairHeight)).toEqual([100, 210, 330, 460, 120]);
    const centers = [0, 1, 2, 3, 4].map(stairCenter);
    expect(centers).toEqual([120, 336, 552, 768, 984]);
    for (const center of centers) {
      expect(Number.isFinite(center)).toBe(true);
    }
  });
});

describe('同输入同输出', () => {
  it('每个纯函数取两次结果完全相同', () => {
    const items: unknown = ['甲', { label: '乙' }, 42];
    const samples: Array<() => unknown> = [
      () => stairTotalWidth(3),
      () => stairCenter(2),
      () => stairHeight(1),
      () => stairBarHeight(1, 0.37),
      () => stairBarRect(1, 77.7),
      () => stairNotePoint(1, 77.7),
      () => stairLabelPoint(1),
      () => stairNoteOpacity(0.61),
      () => stairLabelOpacity(0.61),
      () => stairCaptionOpacity(0.61),
      () => stairMarkerOpacity(0.61),
      () => stairHaloOpacity(0.61),
      () => stairStartFraction(3),
      () => activeStairStep(120, [16, 57, 115, 175]),
      () => stairHopAt(70, 41, 24),
      () => stairHopArc({ x: 1, y: 2 }, { x: 3, y: 4 }, 0.3),
      () => stairMarkerPosition(120, [4, 45, 103, 163], 12),
      () => stairMarkerAttrs({ x: 12.345, y: 67.891 }),
      () => stairFlipProgress(213, 201, 24),
      () => stairFlipState(0.6),
      () => stairFlipText(0.6, 'a', 'b'),
      () => stairArrowClassName(0.6),
      () => stairFlipOpacity(0.4),
      () => normalizeStairItems(items),
      () => stairCaptionText(normalizeStairItems(['甲', '乙']), 1),
    ];
    for (const sample of samples) {
      expect(sample()).toEqual(sample());
    }
  });

  it('帧号是唯一输入：打乱顺序逐个求值与顺序求值一致', () => {
    const frames = [0, 1, 17, 40, 119, 240, 479];
    const timelineOf = (frame: number): StairTimeline => ({
      starts: [16, 57, 115, 175],
      hopStarts: [11, 52, 110, 170],
      hopFrames: 5,
      activeStep: activeStairStep(frame, [16, 57, 115, 175]),
    });
    const sample = (frame: number): unknown[] => {
      const timeline = timelineOf(frame);
      return [
        timeline.activeStep,
        stairMarkerPosition(frame, timeline.hopStarts, timeline.hopFrames),
        stairMarkerOpacity(frame / 20),
        stairFlipProgress(frame, 201, 24),
        stairFlipState(stairFlipProgress(frame, 201, 24)),
        stairArrowClassName(stairFlipProgress(frame, 201, 24)),
        springBy((frame - 16) / 30, 'firm'),
      ];
    };
    const sequential = frames.map(sample);
    for (const frame of [...frames].reverse()) {
      expect(sample(frame)).toEqual(sequential[frames.indexOf(frame)]);
    }
  });

  it('柱高只由弹簧进度决定：进度相同则高度相同', () => {
    for (const p of [0, 0.2, 0.5, 0.9, 1]) {
      expect(stairBarHeight(2, p)).toBe(stairBarHeight(2, p));
      expect(stairBarHeight(2, p)).toBe(stairHeight(2) * p);
    }
  });
});
