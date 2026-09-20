/**
 * 飞轮几何的纯函数契约（对应 `web/src/components/Loop.tsx`）。
 *
 * 这些断言**不依赖浏览器**：宽度收的是「一行文字 → 像素宽」的函数，
 * 因此不引入 jsdom、也不需要测试库——换成一个等宽假字体之后，
 * 「矩形内接于圆、逐行数试算、量不到就降级」这三条规则本身仍然可断言。
 *
 * 字体度量的部分交给运行时（`useTextMeasure`），组件侧只负责几何。
 */
import { describe, expect, it } from 'vitest';

import {
  LOOP,
  MIN_NODE_RADIUS,
  NODE_LINE_PX,
  SURFACE_PAD,
  balanceChars,
  fitLabelToCircle,
  loopArcLength,
  loopArcPath,
  loopGeometry,
  loopLabelLines,
  loopNodeLabel,
  loopNodeLabels,
  loopPoint,
  loopStepDegrees,
  loopStops,
  type LoopFitOptions,
  type LoopLabelLayout,
} from '@/components/Loop';

/** 量尺：每个汉字按 px 计宽（CJK 的宽度基本是线性的）。 */
const perChar = (px: number) => {
  return (line: string) => Array.from(line).length * px;
};

/** 量尺：不管量哪一行都给同一个宽度（用来把某一种装法单独拎出来看）。 */
const fixed = (px: number) => {
  return () => px;
};

/** 按老实现的兜底令牌取值（`--fig-node-r-min` 76 / `--fig-surface-pad` 16）装配参数。 */
function fit(
  label: unknown,
  widthOf: (line: string) => number | null | undefined,
  options: Partial<LoopFitOptions> = {},
): LoopLabelLayout {
  return fitLabelToCircle(label, widthOf, {
    minRadius: MIN_NODE_RADIUS,
    pad: SURFACE_PAD,
    lineHeight: NODE_LINE_PX,
    ...options,
  });
}

describe('常量：写死的 76px 现在只是下限', () => {
  it('最小半径仍是旧实现里那个 76px，行高是 1.15 × 40px = 46px', () => {
    expect(LOOP.NODE_R).toBe(76);
    expect(MIN_NODE_RADIUS).toBe(76);
    expect(SURFACE_PAD).toBe(16);
    expect(NODE_LINE_PX).toBe(46);
  });
});

describe('圆盘半径：矩形内接于圆', () => {
  it('单行的判据与手算一致（3-4-5：w=80、h=60、pad=16 ⇒ r=66）', () => {
    const layout = fit('甲', fixed(80), {
      minRadius: 0,
      lineHeight: 60,
    });
    // sqrt((80/2)² + (60/2)²) + 16 = sqrt(40² + 30²) + 16 = 50 + 16
    expect(layout.radius).toBeCloseTo(66, 9);
    expect(layout.lines).toEqual(['甲']);
    expect(layout.measured).toBe(true);
  });

  it('断行结果恒为单行：老实现的 break 让多行试算不可达（照抄）', () => {
    // 4 个汉字、每个 40px、行高 60：
    //   1 行 w=160 h=60 ⇒ sqrt(80²+30²)+16 = 101.440
    //   2 行 w=80  h=120 ⇒ sqrt(40²+60²)+16 =  88.111 ← 更小，但永远比不到
    // 老实现循环末尾的 `if (lines.length === 1) break;` 在 count=1 时必然成立
    // （balanceChars(chars, 1) 只切出一行），所以循环总在第一次迭代退出。
    // 这一条断言守住「照抄」：去掉那个 break 会改画面，不是修 Bug。
    const layout = fit('甲乙丙丁', perChar(40), {
      minRadius: 0,
      lineHeight: 60,
    });
    expect(layout.lines).toEqual(['甲乙丙丁']);
    expect(layout.radius).toBeCloseTo(Math.sqrt(80 ** 2 + 30 ** 2) + 16, 6);
    expect(layout.radius).toBeCloseTo(101.44, 3);
  });

  it('四个汉字 183px、行高 44×1.15 算出来的半径大于写死的 76px（缺陷回归）', () => {
    const lineHeight = 44 * 1.15; // 50.6
    // 183px 是「四个汉字带字距」的实测宽度；旧实现把半径写死 76px（直径 152px），
    // 文字比直径还宽 31px，必然穿出圆——K8 的反例实测报穿出 16.0px。
    const layout = fit('打开选项', perChar(45.75), {
      minRadius: 76,
      lineHeight,
    });
    expect(layout.measured).toBe(true);
    expect(layout.lines).toEqual(['打开选项']);
    // sqrt((183/2)² + (50.6/2)²) + 16 = 110.933
    expect(layout.radius).toBeCloseTo(110.9333, 3);
    expect(layout.radius).toBeGreaterThan(76);
    expect(layout.radius).toBeGreaterThan(MIN_NODE_RADIUS);
    // 即便多行分支可达，两行装法所需的 88.11px 也仍然大于写死的 76px：
    // 「半径必须由内容决定」这条性质不依赖上面那个 break。
    expect(Math.sqrt(45.75 ** 2 + 50.6 ** 2) + 16).toBeGreaterThan(76);
  });

  it('算出来的半径小于最小半径时取最小半径（仍算量到了）', () => {
    const layout = fit('甲', perChar(40), { lineHeight: 46 });
    expect(layout.radius).toBe(76);
    expect(layout.measured).toBe(true);
  });
});

describe('降级路径：量不到宽度', () => {
  it('宽度为 0 → 单行原文 + 最小半径，不抛错', () => {
    const layout = fit('打开选项', () => 0);
    expect(layout.lines).toEqual(['打开选项']);
    expect(layout.radius).toBe(MIN_NODE_RADIUS);
    expect(layout.measured).toBe(false);
  });

  it('宽度为 null / undefined / NaN → 同样降级', () => {
    for (const widthOf of [
      () => null,
      () => undefined,
      () => Number.NaN,
    ]) {
      const layout = fit('打开选项', widthOf);
      expect(layout.lines).toEqual(['打开选项']);
      expect(layout.radius).toBe(MIN_NODE_RADIUS);
      expect(layout.measured).toBe(false);
    }
  });

  it('空文案 / 非字符串 → 空行集 + 最小半径', () => {
    for (const label of ['', null, undefined]) {
      const layout = fit(label, fixed(80));
      expect(layout.lines).toEqual([]);
      expect(layout.radius).toBe(MIN_NODE_RADIUS);
      expect(layout.measured).toBe(false);
    }
  });
});

describe('步长与节点中心距（K8）', () => {
  it('三个节点 120°、四个节点 90°', () => {
    expect(loopStops(3)).toBe(3);
    expect(loopStops(4)).toBe(4);
    expect(loopStepDegrees(loopStops(3))).toBe(120);
    expect(loopStepDegrees(loopStops(4))).toBe(90);
  });

  it('格数 = 停位数 × 2（两整圈之后条满）', () => {
    expect(loopGeometry(4)).toEqual({ stops: 4, segments: 8 });
    expect(loopGeometry(3)).toEqual({ stops: 3, segments: 6 });
    // 节点数为 0/1 时仍至少有两个停位，避免步长退化成 360°
    expect(loopGeometry(1).stops).toBe(2);
    expect(loopGeometry(0).stops).toBe(2);
  });

  it('四节点与三节点：每一步的中心距都大于 0，且等于弦长 2R·sin(步长/2)', () => {
    for (const nodeCount of [3, 4]) {
      const { stops } = loopGeometry(nodeCount);
      const stepRad = (loopStepDegrees(stops) * Math.PI) / 180;
      const expected = 2 * LOOP.R * Math.sin(stepRad / 2);
      for (let index = 0; index < stops; index += 1) {
        const from = loopPoint(index, stops);
        const to = loopPoint(index + 1, stops);
        const distance = Math.hypot(to.x - from.x, to.y - from.y);
        expect(distance).toBeGreaterThan(0);
        expect(distance).toBeCloseTo(expected, 6);
      }
    }
    expect(2 * LOOP.R * Math.sin(Math.PI / 3)).toBeCloseTo(346.4102, 4);
    expect(2 * LOOP.R * Math.sin(Math.PI / 4)).toBeCloseTo(282.8427, 4);
  });

  it('历史缺陷回归：按 3 个停位摆 4 个节点时，第 4 个会与第 1 个重合', () => {
    const wrongFrom = loopPoint(0, 3);
    const wrongTo = loopPoint(3, 3);
    expect(Math.hypot(wrongTo.x - wrongFrom.x, wrongTo.y - wrongFrom.y)).toBeLessThan(1e-9);

    // 按节点数取停位之后不再重合
    const rightFrom = loopPoint(0, 4);
    const rightTo = loopPoint(3, 4);
    expect(Math.hypot(rightTo.x - rightFrom.x, rightTo.y - rightFrom.y)).toBeGreaterThan(
      0,
    );
  });

  it('弧长与 d 与旧实现逐字符相同（4 个停位：90° 弧）', () => {
    expect(loopArcLength(4)).toBeCloseTo((200 * 90 * Math.PI) / 180, 9);
    expect(loopArcLength(3)).toBeCloseTo((200 * 120 * Math.PI) / 180, 9);
    expect(loopArcPath(loopPoint(0, 4), loopPoint(1, 4))).toBe(
      'M444.00 90.00 A 200 200 0 0 1 644.00 290.00',
    );
  });
});

describe('断行与落点', () => {
  it('balanceChars 行数固定、各行字数差不超过 1', () => {
    expect(balanceChars(['甲', '乙', '丙', '丁', '戊'], 2)).toEqual(['甲乙丙', '丁戊']);
    expect(balanceChars(['甲', '乙', '丙', '丁'], 2)).toEqual(['甲乙', '丙丁']);
    expect(balanceChars(['甲'], 1)).toEqual(['甲']);
  });

  it('单行落在圆心 y 上，多行按行盒中心对称铺开', () => {
    const single = loopLabelLines(
      { lines: ['甲'], radius: 76, lineHeight: 46, measured: true },
      444,
      290,
    );
    expect(single).toEqual([{ text: '甲', x: 444, y: 290 }]);

    const double = loopLabelLines(
      { lines: ['甲乙', '丙丁'], radius: 76, lineHeight: 46, measured: true },
      444,
      290,
    );
    expect(double).toEqual([
      { text: '甲乙', x: 444, y: 290 - 23 },
      { text: '丙丁', x: 444, y: 290 + 23 },
    ]);
  });

  it('节点标签：字符串直接用，对象取 label 再退到 id', () => {
    expect(loopNodeLabel('问题')).toBe('问题');
    expect(loopNodeLabel({ id: 'open', label: '打开选项' })).toBe('打开选项');
    expect(loopNodeLabel({ id: 'open' })).toBe('open');
    expect(loopNodeLabel(null)).toBe('');
    expect(loopNodeLabels(['问题', { label: '约束' }])).toEqual(['问题', '约束']);
    expect(loopNodeLabels(undefined)).toEqual([]);
  });
});
