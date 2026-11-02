## Context

当前 L1/L2 能力分散在共享纯函数、Painter 与六个风格包中。共享层 `primitives.ts` 有 `rollNumber`/`growSeries` 等，但没有组件；风格包里有 `HandDrawnLine`/`ChartLine`/`HeroNumber`/`Callout` 等局部实现，写法重复，且部分组件未被示例使用。代码场景的 `sequential` 与 `pure-time` 对时间源有不同约束，新增组件必须同时满足两者。

## Goals / Non-Goals

**Goals:**

- 新增一套只依赖 `progress`/`easing` 的共享 L1/L2 组件。
- 用 `@remotion/paths` 替换 SVG 路径生长手写逻辑。
- 用 `@remotion/animation-utils` 替换 CSS transform/颜色/数值拼接。
- 用 `roughjs` 生成 MarkerHighlight 草图几何，seed 可复现。
- 保持现有组件 props 兼容，保留路径、排版、颜色与节奏。
- 给出“何时用哪个库/能力”的文档与测试。

**Non-Goals:**

- 不替换 Painter/PainterCanvas/bloom/量测代理。
- 不删除 `primitives.ts` 五项原语；新组件复用它们。
- 不引入时间驱动的成品组件（NumberFlow、CountUp、Typewriter 库、RoughNotation）。
- 本轮不引入 `@remotion/shapes`、`@remotion/motion-blur`。
- 不重新生成全部示例成片；只做代表帧复核。

## Decisions

### 1. 依赖与版本

- `@remotion/paths@4.0.526`：无依赖、纯函数，安全进入 code scene。
- `@remotion/animation-utils@4.0.526`：依赖 `remotion@4.0.526`；先做 code scene 构建 spike，确认不会被 `approved` 白名单或 IIFE 打包阻断。
- `roughjs@4.6.6`：仅 MarkerHighlight 使用，显式 `seed`。
- 不加入 `build-code-scene.mjs` 的 `approved` 白名单；作品/风格包只能 import `m2v/code-scene` 的封装。

### 2. 模块位置

新增 `web/src/code-scene/motion-components/`，避免与 `motion.ts` 文件命名冲突；从 `sdk.tsx` 统一导出。目录自动进入代码场景实现指纹。

### 3. 纯帧契约

所有组件只接收 `progress`、`easing`、几何与样式参数；不读挂钟/timer/rAF/上一帧/Remotion context；随机只来自显式 seed。DOM 组件保留 `data-m2v-role`/`data-m2v-state`。

### 4. 使用边界

- `@remotion/paths` 只用于 SVG path；Canvas 继续用 Painter。
- `@remotion/animation-utils` 只用于 CSS 样式；SVG 数值属性/Canvas/Three 继续用现有数值原语。
- `roughjs` 只用于手绘高亮几何；不草图化作品已有艺术路径。
- `@remotion/shapes`/`motion-blur` 暂不引入。

### 5. 替换策略

先替换生产使用、低风险的路径/transform，再替换未使用组件并顺手修正 `ParallaxBand` 平移未乘 progress 的问题。保持组件 props；`dashed` 的“不生长”语义默认保留，`DrawLine` 提供 `growDashed` 开关。`makeTransform` 对百分比居中支持有限，能保留原字符串的地方保留。

### 6. L1/L2 API

L1：`FadeIn`、`SlideIn`、`ZoomIn`、`Blur`、`Glow`、`DrawLine`。
L2：`RollingNumber`、`Typewriter`、`MarkerHighlight`、`BarGrowth`、`Callout`。
L2 复用 `rollNumber`/`growSeries`；`MarkerHighlight` v1 接受显式 `box`/`path`，不做自动 DOM 测量。

## Risks / Trade-offs

- `animation-utils` 依赖 `remotion` 可能导致 code scene 体积/运行时问题；spike 失败时降级为只用 `@remotion/paths`，L1 用现有纯函数包装。
- `roughjs` 静态导出增加所有 code scene 体积；若不可接受，MarkerHighlight 回退轻量 SVG 草图或仅限需要草图风格。
- `evolvePath` 的 dash 单位与 `pathLength=1` 不同；代表帧复核，虚线变体单独处理。
- 新文件进入实现指纹，所有 code scene 作品失效；风格组件改动改变风格指纹；本轮不重新生成全部成片。
- 前端无 jsdom；组件测试用 `renderToStaticMarkup`，不依赖布局/DOM 测量。
