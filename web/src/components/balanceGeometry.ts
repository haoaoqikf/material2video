/**
 * 天平幕的**纯计算**部分：几何、描边长度与一处颜色表达式。
 *
 * 为什么单独放一个文件：这些函数是「同一帧同一结果」这条硬约束里最容易被
 * 悄悄改坏的部分（倾角差一度、长度差一像素，画面就整体错开），因此它们需要
 * 能在 Node 里逐值断言。这个文件**不 import 任何东西**，测试只加载它，
 * 也就不会碰到 `window` / `document`——不需要 jsdom，也不需要装测试库。
 *
 * 取值全部照抄冻结资产 `.agents/skills/article2video/assets/figures.js`：
 *   - `SCALE`                第 339–344 行
 *   - `panAnchors`           第 347–361 行
 *   - `drawPath` 的长度参数  第 409–412 行
 *   - 右盘描边颜色           第 471–474 行
 * 一个数都没有重算、没有取整、没有「顺手改成常量表达式」。
 */

/**
 * 几何常量：位置全部由常量算出，不读取布局，因此逐帧稳定。
 *
 * 照抄 figures.js 第 339–344 行。这几个数是**画面本身**：改一个，
 * 横梁端点、吊盘挂点、立柱与底座的相对位置会同时错开，
 * 而 CSS 里的 `width: 888px; height: 430px` 与 viewBox 都是照着它们定的。
 */
export const SCALE = {
  PIVOT_X: 444,
  PIVOT_Y: 96,
  ARM: 300,
  TILT: -9,
} as const;

/** 一个挂点。与旧实现的返回结构同名同序（`left` / `right`）。 */
export interface PanAnchor {
  x: number;
  y: number;
}

export interface PanAnchors {
  left: PanAnchor;
  right: PanAnchor;
}

/**
 * 横梁倾角 → 两个吊盘挂点的坐标（吊盘始终垂直，靠平移跟随横梁端点）。
 *
 * 逐表达式照抄 figures.js 第 347–361 行，包括 `Math.PI / 180` 的写法：
 * 换成 `Math.PI * theta / 180` 或先算弧度再传进来，浮点结果会差最后几位，
 * 抽帧对照（PSNR ≥ 60 dB）会把这几位的差算进像素。
 *
 * 倾角符号决定「哪头下沉」，而这里不是笔误：左端取 `PIVOT_Y - ARM * sin`，
 * 而 `SCALE.TILT = -9` 是负角、`sin(-9°) < 0`，减一个负数等于加，
 * 于是左端 y 变大（在 SVG 里向下）**下沉**、右端抬起。整幕的意思
 * 「恐惧把左盘压下去」就压在这个符号上：把 `TILT` 改成 +9，天平会往反方向倒，
 * 而画面照常渲染、校验照常通过。测试用 `panAnchors(SCALE.TILT).left.y > PIVOT_Y`
 * 守住这一条。
 */
export function panAnchors(theta: number): PanAnchors {
  const rad = (theta * Math.PI) / 180;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  return {
    left: {
      x: SCALE.PIVOT_X - SCALE.ARM * cos,
      y: SCALE.PIVOT_Y - SCALE.ARM * sin,
    },
    right: {
      x: SCALE.PIVOT_X + SCALE.ARM * cos,
      y: SCALE.PIVOT_Y + SCALE.ARM * sin,
    },
  };
}

/**
 * 描边动画的路径长度（`api.drawPath(el, p, { length })` 的第三个参数）。
 *
 * 旧实现里这个值**没有显式给出**时是从元素的 `data-a2v-length` 或实测
 * `getTotalLength()` 拿的——那是一条隐藏在 DOM 里的输入。这里按几何算出来并
 * 显式写死：立柱 `M444 372 L444 96` 长 276、底座 `M364 404 L524 404` 长 160、
 * 两条斜撑各长 88（`4-4-4-8` 直角三角形，斜边恰好是整数）。
 *
 * 数值必须与 CSS/SVG 的 `d` 对上，改 `d` 而忘了这里，画出来的线会
 * 「提前画完」或「永远差一截」——两种都不报错。
 */
export const PATH_LENGTH = {
  pillar: 276,
  legL: 88,
  legR: 88,
  base: 160,
} as const;

/**
 * 右盘描边颜色：由本帧的 `glow` 混出强调色的百分比。
 *
 * 照抄 figures.js 第 471–474 行。三个看着可以简化、其实不能动的地方：
 *
 * 1. `(0.28 + 0.62 * glow)` 是**线性映射到 28%–90%**，不是取整后的档位。
 *    改成 `api.range(glow, 28, 100)`（另一处文字用的是这条）会让起始浓度
 *    从 28% 变成 0%——空盘描边在多数帧上是不可见的，而它正是「还没上场」的线索；
 * 2. `Math.round(... * 100)` **先乘 100 再取整**，所以要断言的字符串是
 *    `90%` 而不是 `0.9%`。写成 `(0.28 + 0.62 * glow).toFixed(2)` 会得到
 *    `0.90%`，颜色几乎完全透明；
 * 3. `transparent` 是**混色终点**而不是 `#000`：`color-mix` 里透明色的
 *    色相不参与结果，写成 `#000000` 在深色主题下会把描边压黑。
 *
 * 组件把返回值原样写进 `stroke` 属性（旧实现用 `setAttribute('stroke', …)`）：
 * 表现属性与行内样式的优先级低于样式表，所以预设层仍然能覆盖它——
 * 这正是「组件报告浓度、设计语言决定落点」的分工。
 */
export function rightRectStroke(glow: number): string {
  const mix = Math.round((0.28 + 0.62 * glow) * 100);
  return `color-mix(in srgb, var(--a2v-accent-deep) ${mix}%, transparent)`;
}
