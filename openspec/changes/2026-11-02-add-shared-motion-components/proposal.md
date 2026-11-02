## Why

项目没有统一的共享 L1/L2 动效组件库：Fade/Slide/Zoom 多为作品内联手写，DrawLine 依赖各风格组件的 `strokeDashoffset`，MarkerHighlight 完全缺失，RollingNumber/BarGrowth 只有未被生产采用的纯函数，Callout 只有 `vibe-fable` 一个局部实现。代码场景同时存在 `sequential` 与 `pure-time` 两种录制模式，共享组件必须只依赖显式 `progress`/`easing`，不能自带时钟。

本变更用成熟、纯函数的 Remotion 官方包替换重复的路径生长与 CSS 插值逻辑，用 roughjs 生成 MarkerHighlight 草图几何，同时补齐一套作品可直接使用的 L1/L2 组件，并给出清晰的使用边界。

## What Changes

- 新增依赖：`@remotion/paths@4.0.526`、`@remotion/animation-utils@4.0.526`、`roughjs@4.6.6`；全部精确锁定。
- 新增共享模块 `web/src/code-scene/motion-components/`：
  - L1：`FadeIn`、`SlideIn`、`ZoomIn`、`Blur`、`Glow`、`DrawLine`
  - L2：`RollingNumber`、`Typewriter`、`MarkerHighlight`、`BarGrowth`、`Callout`
  - 底层：`paths.ts`（`@remotion/paths` 封装）、`styles.ts`（`@remotion/animation-utils` 封装）
- 从 `web/src/code-scene/sdk.tsx` 导出；作品与风格包只通过 `m2v/code-scene` 使用，不直接 import `@remotion/*`。
- 替换现有自研机制：dark-proof 的描线/图表生长/transform、vibe-fable 的卡片/视差/引线/数字滚动、doc-archive 的章节上浮/档案渐变等；保留路径数据、排版、颜色与节奏。
- 更新 README、ARCHITECTURE、skill reference、web README 许可表与测试。
- 本轮不引入 `@remotion/shapes`、`@remotion/motion-blur`；前者按需再评估，后者只适用于 Remotion composition。

## Capabilities

### New Capabilities

- `shared-motion-components`：共享 L1/L2 动效组件的 API、纯帧契约、使用边界与测试要求。

### Modified Capabilities

- `react-code-scenes`：共享动效组件进入代码场景；pure-time 兼容；SDK 导出与构建边界。
- `scene-motion-primitives`：新组件复用 `rollNumber`/`growSeries`/`motion.ts`；不替代原语。

## Impact

- 前端依赖：`web/package.json`、`web/pnpm-lock.yaml`。
- 共享运行时：`web/src/code-scene/motion-components/`、`sdk.tsx`。
- 风格组件：`styles/dark-proof/`、`styles/vibe-fable/`、`styles/doc-archive/` 的相关组件。
- 测试：`web/src/code-scene/motion-components/*.test.ts(x)`、`tests/common/test_motion_components.py`、`tests/types/general/test_code_scenes.py`。
- 文档：`README.md`、`ARCHITECTURE.md`、`web/README.md`、`.agents/skills/material2video/references/`。
- 实现指纹与风格指纹会变化，已有 code scene / 风格作品需要重新 prepare；本轮不重新生成全部成片。
