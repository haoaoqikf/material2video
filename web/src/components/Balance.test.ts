/**
 * 天平幕纯函数的逐值断言。
 *
 * 只测**纯函数**：不引入 jsdom、不装测试库，也不渲染组件——组件里的每一处
 * 表达式都会逐帧落到像素上，因此它们必须能在没有浏览器的情况下被钉住。
 *
 * 期望值有两条来源：
 *   1. **手算**：`panAnchors` 是一道三角题（`x = PIVOT ± ARM·cosθ`、
 *      `y = PIVOT ∓ ARM·sinθ`），因此期望值直接由 `PIVOT` / `ARM` / `θ` 算出，
 *      而不是把实现跑一遍的返回值抄进测试（那样只能证明「两次一样」）；
 *   2. **旧实现的字面值**：`.agents/skills/article2video/assets/figures.js`
 *      第 339–344、347–361、409–412、471–474 行，写进测试里就是对照锚点。
 *
 * 这些断言挡的是「改一个数、画面整体错开、而校验照常通过」这一类问题：
 * 倾角符号反了、挂点忘了乘 cos、描边长度少算 4px、浓度取整取错位置——
 * 四种都不会报错，只会让抽帧对照的 PSNR 掉下去。
 */

import { describe, expect, it } from 'vitest';

import {
  PATH_LENGTH,
  SCALE,
  panAnchors,
  rightRectStroke,
  type PanAnchors,
} from '@/components/Balance';

/** 手算：把「横梁倾角」这道三角题按定义写一遍，作为独立参照。 */
function handCalculated(theta: number): PanAnchors {
  const rad = (theta * Math.PI) / 180;
  return {
    left: {
      x: SCALE.PIVOT_X - SCALE.ARM * Math.cos(rad),
      y: SCALE.PIVOT_Y - SCALE.ARM * Math.sin(rad),
    },
    right: {
      x: SCALE.PIVOT_X + SCALE.ARM * Math.cos(rad),
      y: SCALE.PIVOT_Y + SCALE.ARM * Math.sin(rad),
    },
  };
}

describe('SCALE：天平几何常量', () => {
  it('逐值与冻结资产 figures.js 第 339–344 行相同', () => {
    // 这四个数是画面本身：抽帧对照的像素位置全由它们推出。
    expect(SCALE.PIVOT_X).toBe(444);
    expect(SCALE.PIVOT_Y).toBe(96);
    expect(SCALE.ARM).toBe(300);
    // TILT 是**负角**，符号决定「哪头下沉」；改成 +9 整幕的意思就反了。
    expect(SCALE.TILT).toBe(-9);
  });
});

describe('panAnchors：倾角 → 两个吊盘挂点', () => {
  it('0° 时两挂点等高、与支点等距，形成一条水平横梁', () => {
    const { left, right } = panAnchors(0);
    expect(left.y).toBe(SCALE.PIVOT_Y);
    expect(right.y).toBe(SCALE.PIVOT_Y);
    expect(left.y).toBe(right.y);
    // 端点与支点的距离恰是臂长：横梁总长就是 2 × ARM
    expect(Math.abs(left.x - SCALE.PIVOT_X)).toBe(SCALE.ARM);
    expect(Math.abs(right.x - SCALE.PIVOT_X)).toBe(SCALE.ARM);
    expect(right.x - left.x).toBe(2 * SCALE.ARM);
    // 手算：cos0 = 1、sin0 = 0
    expect(left).toEqual({ x: 144, y: 96 });
    expect(right).toEqual({ x: 744, y: 96 });
  });

  it('取本幕的倾角（SCALE.TILT = -9°）时左端下沉、右端抬起，落点与手算一致', () => {
    const theta = SCALE.TILT;
    const anchors = panAnchors(theta);
    const expected = handCalculated(theta);

    // 先对几何关系下断言：负角让左端 y 变大（SVG 里向下 = 下沉）。
    // 「恐惧把左盘压下去」这一层叙事就压在这个不等号上。
    expect(anchors.left.y).toBeGreaterThan(SCALE.PIVOT_Y);
    expect(anchors.right.y).toBeLessThan(SCALE.PIVOT_Y);
    // 两端一升一降，落差是 2·ARM·|sinθ|
    expect(anchors.left.y - SCALE.PIVOT_Y).toBeCloseTo(
      SCALE.ARM * Math.abs(Math.sin((theta * Math.PI) / 180)),
      10,
    );

    // 再对逐个数值下断言（与实现走同一条手算式，但写成独立的定义式）
    for (const side of ['left', 'right'] as const) {
      expect(anchors[side].x).toBeCloseTo(expected[side].x, 10);
      expect(anchors[side].y).toBeCloseTo(expected[side].y, 10);
    }

    // 手算到 3 位的字面值：cos9° = 0.9876883405951378 → 300·cos9° = 296.306502，
    // sin9° = 0.15643446504023087 → 300·sin9° = 46.9303395
    // （toBeCloseTo 的第 3 位是「|差| < 0.0005」的边界，这里给到 2 位，
    //   留一位余量——这一条要钉的是「少乘了 cos」，不是浮点末位）
    expect(anchors.left.x).toBeCloseTo(147.69, 2);
    expect(anchors.left.y).toBeCloseTo(142.93, 2);
    expect(anchors.right.x).toBeCloseTo(740.31, 2);
    expect(anchors.right.y).toBeCloseTo(49.07, 2);
  });

  it('镜像对称：两挂点关于过支点的竖轴互为镜像，且到支点距离恒为 ARM', () => {
    for (const theta of [-9, -4.5, 0, 1, 7.25]) {
      const { left, right } = panAnchors(theta);
      expect(left.x + right.x).toBeCloseTo(2 * SCALE.PIVOT_X, 10);
      expect(left.y + right.y).toBeCloseTo(2 * SCALE.PIVOT_Y, 10);
      expect(Math.hypot(left.x - SCALE.PIVOT_X, left.y - SCALE.PIVOT_Y)).toBeCloseTo(
        SCALE.ARM,
        9,
      );
      expect(Math.hypot(right.x - SCALE.PIVOT_X, right.y - SCALE.PIVOT_Y)).toBeCloseTo(
        SCALE.ARM,
        9,
      );
    }
  });

  it('两挂点始终关于支点中心对称：交换左右得到的是同一对点', () => {
    const { left, right } = panAnchors(SCALE.TILT);
    expect(left.x - SCALE.PIVOT_X).toBeCloseTo(-(right.x - SCALE.PIVOT_X), 10);
    expect(left.y - SCALE.PIVOT_Y).toBeCloseTo(-(right.y - SCALE.PIVOT_Y), 10);
  });

  it('单调性：倾角从 -90° 增到 +90°，右端相对左端一直抬起、横梁在水平方向一直收拢', () => {
    // 注意角度域：cos 在 [0°, 90°] 与 [-90°, 0°] 上各有一段单调区间，
    // **合起来不是单调的**——所以跨度只在负半段与正半段内分别断言。
    // （第一版把 -60° 与 60° 放在同一串里比较，跨度 300 对 300，
    //   量到的是 cos60° = cos(-60°) 的相等，不是单调性。）
    for (const thetas of [
      [-90, -60, -30, -9, 0],
      [0, 9, 30, 60, 90],
    ]) {
      for (let i = 1; i < thetas.length; i += 1) {
        const before = panAnchors(thetas[i - 1]!);
        const after = panAnchors(thetas[i]!);
        /*
         * 另外注意「左端的 y 一直增大」也是**错的**：y 走余弦那一支的相反数
         * （`left.y = PIVOT_Y - ARM·sinθ`），在 -90°→+90° 上先降后升。
         * 真正单调的是**两端的落差** sinθ，以及横梁的水平跨度 cosθ。
         * 写成「左端一直下沉」的断言会把一个正确的实现判成错——
         * 这正是这条测试第一版的样子，留在注释里以免再写一遍。
         */
        // 两端的落差 = 2·ARM·sinθ，随倾角单调增大（右端抬起、左端相对下沉）
        expect(after.right.y - after.left.y).toBeGreaterThan(
          before.right.y - before.left.y - 1e-9,
        );
        // 水平跨度 = 2·ARM·cosθ，逐值对照定义式。
        //
        // 这里**不能**顺手写一句「跨度随 |θ| 增大而收拢」：真实跨度在
        // |θ| 增大时是**变大**的（0° 的 600 → 60° 的 300 → 90° 的 0），
        // 收拢发生在 60°→90° 这一段。第一版按「随手一想」写成
        // `after <= before + 1e-9`，被 i=1 的 300 > 1e-9 判成失败——
        // 断言的方向错了，实现是对的。方向写进注释以免再错一次。
        expect(after.right.x - after.left.x).toBeCloseTo(
          2 * SCALE.ARM * Math.cos((thetas[i]! * Math.PI) / 180),
          9,
        );
        // 端点永远不超出臂长所及的圆
        expect(Math.abs(after.left.x - SCALE.PIVOT_X)).toBeLessThanOrEqual(SCALE.ARM + 1e-9);
      }
    }
    // 端到端的两条极端：-90° 时左端被压到最低、右端抬到最高
    expect(panAnchors(-90).left.y - panAnchors(90).left.y).toBeCloseTo(2 * SCALE.ARM, 9);
    expect(panAnchors(90).right.y - panAnchors(-90).right.y).toBeCloseTo(2 * SCALE.ARM, 9);
    // 跨度在 0° 取最大值、在 ±90° 收成 0：横梁从「最长」转到「立起来」
    expect(panAnchors(0).right.x - panAnchors(0).left.x).toBeCloseTo(2 * SCALE.ARM, 9);
    expect(panAnchors(90).right.x - panAnchors(90).left.x).toBeCloseTo(0, 9);
    expect(panAnchors(-90).right.x - panAnchors(-90).left.x).toBeCloseTo(0, 9);
  });

  it('边界：±90° 时两挂点都落在支点的竖直线上', () => {
    for (const theta of [-90, 90]) {
      const { left, right } = panAnchors(theta);
      expect(left.x).toBeCloseTo(SCALE.PIVOT_X, 9);
      expect(right.x).toBeCloseTo(SCALE.PIVOT_X, 9);
      expect(left.y - SCALE.PIVOT_Y).toBeCloseTo(
        -SCALE.ARM * Math.sin((theta * Math.PI) / 180),
        9,
      );
    }
    // 正负 90° 互为上下：左端在 +90° 时被抬到最高，-90° 时压到最低
    expect(panAnchors(-90).left.y).toBeGreaterThan(panAnchors(90).left.y);
  });

  it('纯函数：同一输入两次求值完全相同（逐位相同，不是「接近」）', () => {
    for (const theta of [SCALE.TILT, 0, 3.7, -12.25]) {
      const first = panAnchors(theta);
      const second = panAnchors(theta);
      // toEqual 对 NaN/±0 也做区分；这里再显式比对一遍浮点串，
      // 保证「同一帧两次渲染得到同一个属性串」——抽帧对照依赖这一点。
      expect(second).toEqual(first);
      expect(second.left.x.toFixed(2)).toBe(first.left.x.toFixed(2));
      expect(second.left.y.toFixed(2)).toBe(first.left.y.toFixed(2));
      expect(second.right.x.toFixed(2)).toBe(first.right.x.toFixed(2));
      expect(second.right.y.toFixed(2)).toBe(first.right.y.toFixed(2));
    }
  });

  it('纯函数：与调用顺序无关（打乱顺序逐项求值结果不变）', () => {
    const thetas = [SCALE.TILT, 0, 12.5, -30, 45];
    const forward = thetas.map((theta) => panAnchors(theta));
    const backward = [...thetas].reverse().map((theta) => panAnchors(theta)).reverse();
    expect(backward).toEqual(forward);
  });
});

describe('PATH_LENGTH：描边动画的路径长度', () => {
  it('与旧实现 drawPath 的显式长度参数相同', () => {
    // 立柱 M444 372 L444 96：|372 - 96| = 276
    expect(PATH_LENGTH.pillar).toBe(276);
    // 底座 M364 404 L524 404：|524 - 364| = 160
    expect(PATH_LENGTH.base).toBe(160);
    // 斜撑 M444 368 L364 404：Δ(80, 36) → hypot = 87.7268…，而旧实现给的是 88。
    // 差的这 0.27px 是**旧实现自己的**：88 意味着描边在这条路径上永远画不满
    // （dasharray 固定 88、dashoffset 从 88 走到 0），画满与否是像素级差异。
    // 因此这里照抄 88，**不按几何修正**——「顺手算准」会改画面。
    expect(PATH_LENGTH.legL).toBe(88);
    expect(PATH_LENGTH.legR).toBe(88);
    expect(PATH_LENGTH.legL).toBe(PATH_LENGTH.legR);
    expect(Math.hypot(444 - 364, 368 - 404)).toBeCloseTo(87.7268, 4);
    // 两条斜撑共用同一个长度：旧实现两处都写 88，不是各算各的
    expect(PATH_LENGTH.legL).toBe(PATH_LENGTH.legR);
  });
});

describe('rightRectStroke：右盘描边的浓度', () => {
  it('glow 0 → 28%，glow 1 → 90%，与旧实现的表达式逐字符相同', () => {
    expect(rightRectStroke(0)).toBe(
      'color-mix(in srgb, var(--a2v-accent-deep) 28%, transparent)',
    );
    expect(rightRectStroke(1)).toBe(
      'color-mix(in srgb, var(--a2v-accent-deep) 90%, transparent)',
    );
    // 0.5 → Math.round((0.28 + 0.31) * 100) = 59
    expect(rightRectStroke(0.5)).toBe(
      'color-mix(in srgb, var(--a2v-accent-deep) 59%, transparent)',
    );
  });

  it('先乘 100 再取整：写错成 toFixed 会得到「0.90%」这种几乎全透明的值', () => {
    // 这条是回归防线：曾经出现过 `(0.28 + 0.62 * glow).toFixed(2)` 的写法，
    // 结果里的百分数少乘了 100，描边浓度从 90% 掉到 0.9%。
    expect(rightRectStroke(1)).toContain('90%');
    expect(rightRectStroke(1)).not.toContain('0.90%');
  });

  it('浓度随 glow 单调不减，且整数百分比不会超过 90%', () => {
    let previous = -1;
    for (let glow = 0; glow <= 1.0001; glow += 0.05) {
      const percent = Number(/ (\d+)%/.exec(rightRectStroke(glow))![1]);
      expect(percent).toBeGreaterThanOrEqual(previous);
      expect(percent).toBeGreaterThanOrEqual(28);
      expect(percent).toBeLessThanOrEqual(90);
      previous = percent;
    }
  });

  it('纯函数：同一输入两次求值完全相同', () => {
    expect(rightRectStroke(0.37)).toBe(rightRectStroke(0.37));
    expect(rightRectStroke(0)).toBe(rightRectStroke(0));
  });
});
