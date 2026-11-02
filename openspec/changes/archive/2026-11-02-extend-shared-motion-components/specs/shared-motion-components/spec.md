## ADDED Requirements

### Requirement: 文本排版组件

系统 SHALL 从 `m2v/code-scene` 提供 `AutoFitText` 与 `TextBlock`。两者 MUST 只按传入的文本、宽度、字号、字体与 `progress` 计算，MUST NOT 读取挂钟、帧号或上一帧状态。

文本测量 MUST 只在浏览器进行；字体未就绪时 MAY 回退到调用方字号或原始分行，但字体就绪后 MUST 重测一次。CJK 换行 MUST NOT 依赖按空格切词：中文按字形单元断行，收尾标点 MUST NOT 出现在行首，超长西文单词 MUST 被硬断。Node/SSR 环境下 MUST NOT 抛出测量错误。

#### Scenario: 中文多行标题
- **WHEN** `TextBlock` 以 `maxWidth` 和中文文本渲染
- **THEN** 每一行不超过 `maxWidth`，句号、逗号等收尾标点不出现在行首

#### Scenario: 字体延迟
- **WHEN** 组件首次渲染时字体尚未加载
- **THEN** 先使用回退字号，`document.fonts.ready` 后重新测量并更新字号/分行

#### Scenario: Node 渲染
- **WHEN** 在无 DOM 的环境执行静态标记测试
- **THEN** 组件回退到调用方字号或按换行符分行，不抛错

### Requirement: 图形变换、遮罩与仪表

系统 SHALL 从 `m2v/code-scene` 提供 `PathMorph`、`MaskReveal`、`ArcGauge`、`ProgressRing` 与 `NoiseDrift`（含 `noiseAt`、`noiseDrift`）。

`PathMorph` MUST 通过 `interpolatePath` 做逐点插值，MUST NOT 承诺拓扑匹配。`MaskReveal` MUST 输出静态 `clip-path`，MUST NOT 使用 CSS transition 或动画。噪声 MUST 只由显式 seed 与坐标求值；未提供 seed 时 MUST 使用固定默认值。所有组件 MUST 只由 `progress` 与显式 `easing` 驱动。

#### Scenario: 路径形变
- **WHEN** 同一组 `from`/`to` 与 `progress` 重复求值
- **THEN** 得到相同路径；进度 0 与 1 分别接近两个端点

#### Scenario: 遮罩揭示
- **WHEN** `MaskReveal` 以 `wipe` 或 `iris` 模式接收进度
- **THEN** 输出对应的静态 `clip-path`，不启动浏览器动画

#### Scenario: 噪声可复现
- **WHEN** `NoiseDrift` 或 `noiseDrift` 以相同 seed 和进度重录
- **THEN** 位移、旋转与缩放完全一致

### Requirement: 纯时间安全图表

系统 SHALL 从 `m2v/code-scene` 提供 `LinePlot`、`AreaPlot`、`Sparkline` 与 `Axis`。它们 MUST 只做数值映射与静态 SVG，MUST NOT 使用 ECharts、`Chart`、`useFrame`、计时器或自走动画。折线 MUST 按进度生长，面积 MUST 按进度从左向右揭示。坐标轴与标注 MUST 由调用方组合，组件不自动排版。

#### Scenario: pure-time 场景使用图表
- **WHEN** 声明 `capture.mode: "pure-time"` 的场景使用 `LinePlot` 与 `Axis`
- **THEN** 通过纯时间静态闸门，正序与倒序采集同一帧 PSNR ≥ 60 dB

#### Scenario: ECharts 仍被禁止
- **WHEN** pure-time 场景改为使用 ECharts 或 `Chart`
- **THEN** 静态闸门拒绝，提示改用共享图表组件

### Requirement: 结构与波形组件

系统 SHALL 从 `m2v/code-scene` 提供 `Timeline`、`ChapterTrack`、`Pictogram`、`IconGrid`、`Waveform` 与 `resamplePeaks`。事件与单位填充 MUST 只由数值、`progress` 与显式 seed（如适用）决定。标签密集时组件 MUST NOT 自动避让或截断，由调用方负责。

#### Scenario: 单位填充
- **WHEN** `Pictogram` 接收总格数、填充值与进度
- **THEN** 整格与部分格按数值比例显示，部分格以透明度表示

#### Scenario: 波形重采样
- **WHEN** `Waveform` 接收任意长度的采样数组
- **THEN** 固定柱数的峰值由 `resamplePeaks` 按桶取绝对值最大值得到

## MODIFIED Requirements

### Requirement: 共享动效组件提供明确的使用边界

系统 SHALL 用 `@remotion/paths` 处理 SVG 路径生长、形变、沿线取点与几何变换，用 `@remotion/animation-utils` 处理 CSS 数值、颜色与 transform 插值，用 `@remotion/layout-utils` 做文本测量与单行适配，用 `@remotion/noise` 生成种子噪声，用 `d3-scale`/`d3-shape` 计算图表的比例尺与曲线，用 `roughjs` 生成手绘高亮几何。MUST NOT 把 `@remotion/paths` 用于 Canvas 点列、把 `@remotion/animation-utils` 用于 SVG 数值属性或 Three.js 数值、把 `@remotion/layout-utils` 的多行切词用于中文、或用 `roughjs` 草图化作品已有艺术路径。

系统 SHALL NOT 引入 `@remotion/shapes`、`@remotion/lottie`、`@remotion/transitions` 与 `@remotion/motion-blur`：`lottie` 的许可与 `useCurrentFrame` 驱动方式不适用于 code scene；`transitions` 与 `motion-blur` 只适用于 Remotion composition，code scene 的运动模糊继续使用既有子帧方案；标准形状暂用现有 SVG。

#### Scenario: SVG 路径生长
- **WHEN** 组件或风格包需要按进度画出一条 SVG 路径
- **THEN** 使用共享 paths 封装的 `evolvePath` 结果，不手写 `pathLength` + `strokeDashoffset`

#### Scenario: 文本测量
- **WHEN** 需要按宽度自动定字号或换行
- **THEN** 使用 `AutoFitText`/`TextBlock`；中文多行不得直接使用 `fillTextBox`/`fitTextOnNLines`

#### Scenario: 图表几何
- **WHEN** 需要纯时间安全的折线或面积
- **THEN** 使用共享图表组件，不直接 import `d3-scale`/`d3-shape`

#### Scenario: Canvas 绘制
- **WHEN** 需要 Canvas 点列、粒子、辉光或量测
- **THEN** 继续使用 Painter/primitives，不引入 paths/animation-utils
