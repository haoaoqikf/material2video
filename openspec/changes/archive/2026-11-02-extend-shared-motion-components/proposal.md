## Why

共享 L1/L2 组件覆盖了入场、数字、柱、高亮与引线，但制作中仍反复缺三类能力：文本无法按宽度适配与中文换行；概念图形只能"生长"不能"变形"或"揭示"；`pure-time` 场景禁用 ECharts 后缺少可用的折线、面积与坐标轴。风格包里还各自实现圆环、时间轴、波形与连线，重复代码没有收敛。

上一轮调研确认：`@remotion/paths` 已内含形变与几何变换能力但只封装了 5 个；`@remotion/layout-utils`、`@remotion/noise`、`d3-scale`、`d3-shape` 满足纯函数、许可与体积约束；时间驱动成品组件（NumberFlow、CountUp、RoughNotation、Lottie）不满足 `progress` 单一输入契约。

## What Changes

- 新增依赖：`@remotion/layout-utils@4.0.526`、`@remotion/noise@4.0.526`、`d3-scale@4.0.2`、`d3-shape@3.2.0`；全部精确锁定，且不加入代码场景 approved 白名单。
- 扩展 `paths.ts`：补齐 `interpolatePath`、`warpPath`、`getBoundingBox`、`normalizePath`、`reversePath`、`scalePath`、`translatePath`、`centerPath`、`getSubpaths` 与 `getInstructionIndexAtLength` 封装。
- 扩展 `styles.ts`：补齐 `skew`/`perspective`/`matrix`/`rotate3d` 等 transform 函数。
- 新增共享组件：
  - 文本：`AutoFitText`、`TextBlock`（CJK 断行、字体就绪后重测）
  - 图形：`PathMorph`、`MaskReveal`、`ArcGauge`、`ProgressRing`、`NoiseDrift`/`noiseAt`/`noiseDrift`
  - 图表：`LinePlot`、`AreaPlot`、`Sparkline`、`Axis`
  - 结构：`Timeline`、`ChapterTrack`、`Pictogram`、`IconGrid`
  - 波形：`Waveform`、`resamplePeaks`
- 补充 Vitest 纯函数/静态标记测试、Python 契约测试与 `pure-time` 慢测；更新 README、ARCHITECTURE、web README 许可表、skill reference 与 guidance routes。
- 本轮不迁移作品与风格示例，也不引入按需子路径导出；依赖保持小体积、可摇树，等真实作品迁移后再评估拆包。

## Capabilities

### New Capabilities

无新增 capability；以下能力归入既有 `shared-motion-components`。

### Modified Capabilities

- `shared-motion-components`：扩展文本排版、图形变换、图表、时间轴、象形图与波形的 API、纯帧契约与依赖边界。
- `react-code-scenes`：扩展组件进入代码场景；`pure-time` 下文本测量、噪声与图表仍可复现；新库不进入作品直接 import 白名单。

## Impact

- 前端依赖：`web/package.json`、`web/pnpm-lock.yaml`。
- 共享运行时：`web/src/code-scene/motion-components/`、`sdk.tsx`。
- 测试：`web/src/code-scene/motion-components/*.test.ts(x)`、`tests/common/test_motion_components.py`、`tests/types/general/test_code_scenes.py`。
- 文档：`README.md`、`ARCHITECTURE.md`、`web/README.md`、`.agents/skills/material2video/references/`。
- 实现指纹变化，所有引用代码场景的作品需要重新 prepare；本轮不重制既有成片。
