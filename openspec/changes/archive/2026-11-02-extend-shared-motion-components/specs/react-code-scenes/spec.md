## MODIFIED Requirements

### Requirement: 共享动效组件兼容代码场景

代码场景 SHALL 通过 `m2v/code-scene` 使用共享组件，包括 L1/L2 动效、文本排版（`AutoFitText`、`TextBlock`）、路径形变与遮罩（`PathMorph`、`MaskReveal`）、圆弧进度（`ArcGauge`、`ProgressRing`）、种子噪声（`NoiseDrift`）、纯时间图表（`LinePlot`、`AreaPlot`、`Sparkline`、`Axis`）、时间轴与章节轨（`Timeline`、`ChapterTrack`）、象形图（`Pictogram`、`IconGrid`）与波形（`Waveform`）。

共享组件 MUST 只依赖显式 `progress`/`easing`/`seed`，MUST NOT 依赖 Remotion composition context；`sequential` 与 `pure-time` MUST 使用同一套组件。文本测量 MUST 在字体就绪后完成，MUST NOT 引入挂钟或计时器。作品与风格组件的直接 import 白名单 MUST NOT 因本能力放宽；`@remotion/layout-utils`、`@remotion/noise`、`d3-scale`、`d3-shape` 等新库只能由共享运行时封装后导出。

#### Scenario: 顺序录制
- **WHEN** 未声明 pure-time 的场景使用共享组件
- **THEN** 组件按连续帧推进，不启动自身计时器

#### Scenario: 纯时间录制
- **WHEN** 声明 pure-time 的场景使用共享组件
- **THEN** 场景通过静态源码闸门，正倒序 PSNR ≥ 60 dB

#### Scenario: 文本与图表
- **WHEN** pure-time 场景使用 `TextBlock`、`LinePlot` 与 `Axis`
- **THEN** 字体测量与图表几何在任意 seek 下得到同一帧一致的结果

#### Scenario: 构建边界
- **WHEN** 场景从 `m2v/code-scene` 导入共享组件
- **THEN** esbuild 构建成功；作品源码不直接导入 `@remotion/*`、`d3-scale`、`d3-shape` 或 `@remotion/noise`
