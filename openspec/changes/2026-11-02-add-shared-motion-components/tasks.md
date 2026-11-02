## 1. 依赖与可行性

- [x] 1.1 新增 `@remotion/paths@4.0.526`、`@remotion/animation-utils@4.0.526`、`roughjs@4.6.6`，精确锁定并同步 `pnpm-lock.yaml`。
- [x] 1.2 做 code scene 构建 spike：从 `m2v/code-scene` 使用最小 paths/styles 封装，确认 esbuild IIFE、`pnpm -C web build`、pure-time 正倒序 PSNR 通过；记录 `animation-utils` 降级结论。
- [x] 1.3 确认未放宽 `build-code-scene.mjs` 的 approved 白名单，作品/风格包不直接 import `@remotion/*`。

## 2. 共享模块与 L1

- [x] 2.1 新建 `web/src/code-scene/motion-components/`：`paths.ts`、`styles.ts`、`index.ts`。
- [x] 2.2 实现 `FadeIn`、`SlideIn`、`ZoomIn`、`Blur`、`Glow`、`DrawLine`，只接收 `progress`/`easing`。
- [x] 2.3 从 `sdk.tsx` 导出；补 Vitest 纯函数/静态标记测试。

## 3. 现有实现替换

- [x] 3.1 `hand-drawn-line`、`ChartLine`、`ChartArrow` 使用 `evolvePath`/path helpers；保留 dashed 语义。
- [x] 3.2 `hero-number`、`rule-card`、`parallax-band`、`chapter-text`、`archiveGradient` 使用 `makeTransform`/`interpolateStyles`；`bilingual-title` 的百分比居中（`translate(-50%, -50%)`）无法由 `makeTransform` 表达，保留原字符串。
- [x] 3.3 `counter`、`counter-row`、`instinct-gauge` 接入 `rollNumber`；修正 `ParallaxBand` 平移未乘 progress。
- [x] 3.4 `callout` 使用共享 `Callout`/`DrawLine`；清理未使用 `useId`。
- [x] 3.5 评估可选替换：`signal-line`/`number-line`/`node-link`/`sequence-links`/`screen-subtitle` 无直接等价物或实现很短，本轮保留原实现。

## 4. L2 组件

- [x] 4.1 实现 `RollingNumber`、`Typewriter`、`BarGrowth`，复用 `rollNumber`/`growSeries`。
- [x] 4.2 实现 `MarkerHighlight`（roughjs + paths，显式 box/path、固定 seed）。
- [x] 4.3 实现共享 `Callout`（paths 引线 + 文本布局），并让 vibe-fable 组件复用。
- [x] 4.4 补 Vitest 测试：端点、同一 progress 重复求值、seed、无时间源。

## 5. 契约测试与文档

- [x] 5.1 新增 `tests/common/test_motion_components.py`：实现指纹、`source_policy.scan`、SDK 导出。
- [x] 5.2 `tests/types/general/test_code_scenes.py` 增加 slow 构建/pure-time 用例，证明新组件经 `m2v/code-scene` 可用。
- [x] 5.3 更新 README、ARCHITECTURE、web/README 许可表、skill reference 与 guidance routes。
- [x] 5.4 评估 gallery：本轮由 Vitest 静态测试与代表帧覆盖，未新增 gallery demo。

## 6. 验证与归档

- [x] 6.1 `pnpm -C web test`、`pnpm -C web build`。
- [x] 6.2 `uv run pytest`、`uv run pytest -m "not slow"`、slow code scene build/pure-time。
- [x] 6.3 `sync_docs.py --check`、`openspec validate --strict`、`openspec validate --specs`。
- [x] 6.4 对 dark-proof sample / vibe-fable pigeon / doc-archive film 做代表帧复核。
- [ ] 6.5 检查暂存内容，提交实施结果；同步主规格并归档变更。
