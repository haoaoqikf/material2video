# shared-motion-components Specification

## Purpose
TBD - created by archiving change 2026-11-02-add-shared-motion-components. Update Purpose after archive.

## Requirements

### Requirement: 共享动效组件以进度为唯一时间输入

系统 SHALL 从 `m2v/code-scene` 提供共享 L1 组件：`FadeIn`、`SlideIn`、`ZoomIn`、`Blur`、`Glow`、`DrawLine`；以及 L2 组件：`RollingNumber`、`Typewriter`、`MarkerHighlight`、`BarGrowth`、`Callout`。

每个组件 MUST 只接受 `progress`（0–1）、显式 `easing`、几何与样式参数作为动画输入，MUST NOT 读取挂钟时间、帧号、上一帧状态、计时器、rAF、CSS 动画或 Remotion context。相同 `progress` 与相同参数 MUST 产生相同输出。随机性 MUST 只来自显式 `seed`，未提供时 MUST 使用固定默认种子。

#### Scenario: 同一进度重复求值
- **WHEN** 同一组件以相同参数和 `progress` 求值两次
- **THEN** 两次输出一致，不受调用时刻、调用顺序或录制模式影响

#### Scenario: pure-time 场景使用
- **WHEN** 一个声明 `capture.mode: "pure-time"` 的场景使用共享组件
- **THEN** 正序、倒序与并行块采集得到同一帧一致的结果，不因时间源失败

#### Scenario: 显式种子
- **WHEN** `MarkerHighlight` 以相同 `seed` 和 `progress` 重录
- **THEN** 草图几何一致，不使用隐式随机源

### Requirement: 共享动效组件提供明确的使用边界

系统 SHALL 用 `@remotion/paths` 处理 SVG 路径生长、沿线取点与切线，用 `@remotion/animation-utils` 处理 CSS 数值、颜色与 transform 插值，用 `roughjs` 生成手绘高亮几何。MUST NOT 把 `@remotion/paths` 用于 Canvas 点列、把 `@remotion/animation-utils` 用于 SVG 数值属性或 Three.js 数值、或用 `roughjs` 草图化作品已有艺术路径。

本轮 SHALL NOT 引入 `@remotion/shapes` 与 `@remotion/motion-blur`；`motion-blur` 只适用于 Remotion composition，code scene 的运动模糊继续使用既有子帧方案。

#### Scenario: SVG 路径生长
- **WHEN** 组件或风格包需要按进度画出一条 SVG 路径
- **THEN** 使用共享 paths 封装的 `evolvePath` 结果，不手写 `pathLength` + `strokeDashoffset`

#### Scenario: Canvas 绘制
- **WHEN** 需要 Canvas 点列、粒子、辉光或量测
- **THEN** 继续使用 Painter/primitives，不引入 paths/animation-utils

### Requirement: 现有风格组件复用共享动效组件

现有风格组件 MUST 在保持公开名称与 props 兼容的前提下复用共享实现：描线与图表生长使用 paths；transform/filter/颜色使用 animation-utils；数字滚动使用 `rollNumber`；引线使用共享 `Callout`/`DrawLine`。作品与风格组件 MUST 通过 `m2v/code-scene` 使用这些能力，MUST NOT 直接 import `@remotion/*` 或 `roughjs`。

#### Scenario: 风格组件内部替换
- **WHEN** `HandDrawnLine`、`ChartLine`、`ChartArrow`、`HeroNumber` 或 `Callout` 的内部实现被替换
- **THEN** 对作品暴露的 props 与视觉语义不变，现有示例继续编译和使用

#### Scenario: 直接外部依赖
- **WHEN** 作品或风格组件直接 import `@remotion/paths`、`@remotion/animation-utils` 或 `roughjs`
- **THEN** 构建或契约测试拒绝该 import，要求改用 `m2v/code-scene`

### Requirement: 共享动效组件必须可测试

共享组件 SHALL 有纯函数/静态标记测试，覆盖进度端点、重复求值、显式缓动与固定种子；SHALL 进入代码场景实现指纹，并以契约测试检查确定性源码闸门与 SDK 导出。

#### Scenario: 修改共享组件
- **WHEN** 共享组件实现或默认参数变化
- **THEN** 引用它的代码场景准备指纹失效，CLI 不再复用旧片段

#### Scenario: 源码闸门
- **WHEN** 共享组件源码引入挂钟、随机源、计时器或 CSS 动画
- **THEN** 契约测试失败并指出文件
