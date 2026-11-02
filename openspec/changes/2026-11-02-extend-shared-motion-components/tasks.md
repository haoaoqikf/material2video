## 1. 依赖与边界

- [x] 1.1 新增 `@remotion/layout-utils@4.0.526`、`@remotion/noise@4.0.526`、`d3-scale@4.0.2`、`d3-shape@3.2.0` 与对应类型，精确锁定。
- [x] 1.2 确认新库不进入 `build-code-scene.mjs` 的 approved 白名单，作品仍只能通过 `m2v/code-scene` 使用。

## 2. 路径与样式封装

- [x] 2.1 `paths.ts` 补齐 `interpolatePath`、`warpPath`、`getBoundingBox`、`normalizePath`、`reversePath`、`scalePath`、`translatePath`、`centerPath`、`getSubpaths`、`getInstructionIndexAtLength`。
- [x] 2.2 `styles.ts` 补齐 `skew`/`perspective`/`matrix`/`rotate3d` 等 transform 函数。

## 3. 文本排版

- [x] 3.1 实现 `AutoFitText`（`fitText`）与 `TextBlock`（CJK 断行、逐字显影）。
- [x] 3.2 字体就绪后重测；Node/SSR 回退不抛错；导出 `wrapText`/`tokenizeForWrap` 供测试。

## 4. 图形与图表

- [x] 4.1 实现 `PathMorph`、`MaskReveal`（wipe/iris/自定义 clip）。
- [x] 4.2 实现 `ArcGauge`、`ProgressRing` 与整圆路径。
- [x] 4.3 实现 `NoiseDrift`/`noiseAt`/`noiseDrift`（显式 seed）。
- [x] 4.4 实现 `LinePlot`、`AreaPlot`、`Sparkline`、`Axis`（纯时间安全）。
- [x] 4.5 实现 `Timeline`、`ChapterTrack`、`Pictogram`、`IconGrid`、`Waveform`、`resamplePeaks`。

## 5. 测试

- [x] 5.1 Vitest：文本断行/端点、路径形变/包围盒、圆弧、噪声确定性、图表生长/裁切/刻度、遮罩、时间轴、象形图、波形。
- [x] 5.2 `tests/common/test_motion_components.py`：实现指纹、源码闸门、SDK 导出、依赖版本与白名单。
- [x] 5.3 `tests/types/general/test_code_scenes.py`：新增使用全部扩展组件的 `pure-time` 用例。

## 6. 文档与归档

- [x] 6.1 更新 README、ARCHITECTURE、web README 许可表、skill reference 与 guidance routes。
- [x] 6.2 新增 OpenSpec 提案、设计、规格与任务。
- [x] 6.3 `pnpm -C web test/build`、`uv run pytest`、`-m "not slow"`、目标 slow 用例、`sync_docs.py --check`、`openspec validate --strict`。
- [ ] 6.4 检查暂存内容，提交实施结果；同步主规格并归档变更。
