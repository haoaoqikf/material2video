## MODIFIED Requirements

### Requirement: 共享动效组件兼容代码场景

本要求只约束作品实际采用的本地实现和默认工程模板。主项目 MUST NOT 提供强制运行时SDK；构建器 MUST 从作品自身安装和锁文件解析依赖，MUST NOT 读取主项目源码或全局依赖登记。参考未被采用时 MUST NOT 成为构建或指纹输入。

代码场景 SHALL 通过 作品本地模块 使用已采用的本地组件，包括 L1/L2 动效、文本排版（`AutoFitText`、`TextBlock`）、路径形变与遮罩（`PathMorph`、`MaskReveal`）、圆弧进度（`ArcGauge`、`ProgressRing`）、种子噪声（`NoiseDrift`）、纯时间图表（`LinePlot`、`AreaPlot`、`Sparkline`、`Axis`）、时间轴与章节轨（`Timeline`、`ChapterTrack`）。

已采用的本地组件 MUST 只依赖显式 `progress`/`easing`/`seed`，MUST NOT 依赖 Remotion composition context；`sequential` 与 `pure-time` MUST 使用同一套组件。文本测量 MUST 在字体就绪后完成，MUST NOT 引入挂钟或计时器。作品 MUST 将实际直接采用的第三方库声明并锁定在本地；允许直接导入或本地封装，MUST NOT 要求经过主项目导出。

#### Scenario: 顺序录制
- **WHEN** 未声明 pure-time 的场景使用已采用的本地组件
- **THEN** 组件按连续帧推进，不启动自身计时器

#### Scenario: 纯时间录制
- **WHEN** 声明 pure-time 的场景使用已采用的本地组件
- **THEN** 场景通过静态源码闸门，正倒序 PSNR ≥ 60 dB

#### Scenario: 文本与图表
- **WHEN** pure-time 场景使用 `TextBlock`、`LinePlot` 与 `Axis`
- **THEN** 字体测量与图表几何在任意 seek 下得到同一帧一致的结果

#### Scenario: 构建边界
- **WHEN** 场景从 作品本地模块 导入已采用的本地组件
- **THEN** 本地构建成功；直接采用的第三方库在作品声明和锁定，不读取主项目包装
