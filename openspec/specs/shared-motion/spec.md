# shared-motion Specification

## Purpose

为通用作品提供以 `progress` 为唯一时间输入的共享动效原语与组件，覆盖数值映射、入场、数据、文本、路径、图表、时间轴与波形，并保持逐帧确定性与缓存失效语义。

## Requirements

### Requirement: 共享动效原语以进度为唯一时间输入

系统 SHALL 提供以下共享原语，供作品 `scenes/` 导入：数字滚动、数据曲线与柱状生长、列表滚屏、主体状态插值、签名粒子。

每个原语 MUST 只接受 `progress`（0–1）作为时间输入，MUST NOT 读取挂钟时间、帧号、上一帧状态或外部计时器。相同 `progress` 与相同参数 MUST 产生相同画面。

原语 MUST NOT 内置视觉主题；颜色、字体、线宽、粒子参数 MUST 由作品传入。缓动曲线 MUST 由作品显式传入，MUST NOT 使用缺省恒等或任何内置曲线。缓动 SHALL 由表达目标决定，允许显式选择 linear 或其他曲线；不得按通用入场／离场方向、风格清单或例外理由限制选择。原语 MUST NOT 被用于关闭信息推进、母题可信度或版式重复问题，也不提供绕过对应复核的默认表现。

#### Scenario: 同一进度重复求值
- **WHEN** 同一原语以相同参数和 `progress` 求值两次
- **THEN** 两次输出一致，不受调用时刻或调用顺序影响

#### Scenario: 未传入缓动
- **WHEN** 作品调用空间原语但没有传入 `easing`
- **THEN** 调用在类型检查或运行时明确失败，不静默回落到线性

#### Scenario: 场景没有传入主题
- **WHEN** 作品只传入默认参数和显式缓动
- **THEN** 原语输出中性几何，不引入预设配色、字体或后期效果

### Requirement: 原语必须支持确定性录制

原语 MUST 在 60 fps 与任意采样帧率下按 `progress` 求值，MUST NOT 依赖逐帧累积状态。包含随机性的原语 MUST 由显式种子决定；未提供种子时 MUST 使用固定默认种子。

原语 MUST NOT 要求播放视频、试听或读取外部资源；其输出 MUST 限于场景画布内的绘制。

#### Scenario: 跳帧采样
- **WHEN** 录制从 0.2 直接跳到 0.8 而不经过中间帧
- **THEN** 该次采样与逐帧播放到同一进度时的输出一致

#### Scenario: 粒子重录
- **WHEN** 同一作品以相同参数重新录制
- **THEN** 粒子位置、数量与形态一致，不因录制次数变化

### Requirement: 原语变更必须使引用作品缓存失效

原语属于共享渲染资产。修改原语实现或默认参数 MUST 使引用它的作品片段缓存失效，并要求重新准备与复查受影响场景；MUST NOT 静默复用旧片段，也不得以"原语未变而场景未变"为由保留旧缓存。

#### Scenario: 修改原语后复用旧片段
- **WHEN** 原语实现变化而作品场景源码未变
- **THEN** 引用该原语的片段判定过期，重新录制后重新完成完整预演

### Requirement: 共享命名曲线库

系统 SHALL 在 `web/src/code-scene/motion.ts` 提供一组只依赖 `progress` 的命名缓动曲线，并从 `m2v/code-scene` 导出。曲线 MUST 为纯函数，输入 0–1、输出可插值数值；MUST NOT 读取时间、随机源或外部状态。

曲线库 SHALL 至少覆盖：线性、缓入、缓出、缓入缓出、指数缓出、回弹落定和五阶缓入缓出。命名 SHALL 表达方向与强度，不表达具体品牌或主题。相机与原语 SHALL 共用同一套命名，不得各自维护重复曲线。

#### Scenario: 曲线端点
- **WHEN** 任一命名曲线以 0 或 1 求值
- **THEN** 输出分别为 0 和 1；回弹曲线在结束前可以超出 0–1，但最终收敛到 1

#### Scenario: 相机和原语共用曲线
- **WHEN** 镜头与原语都使用缓出曲线
- **THEN** 二者引用同一个命名与实现，不出现两套近似但不一致的曲线

### Requirement: 轨迹、爆散与字幕原语

系统 SHALL 在 `web/src/code-scene/` 提供以下纯数值原语，并从 `m2v/code-scene` 导出：

- `samplePath`：按弧长把单子路径 SVG path 采样为等距点；多子路径 MUST 明确失败，不把不连续段当作一条轨迹；
- `sampleTrail`：沿点列按 `progress` 与尾迹长度采样位置、切线、年龄与透明度；
- `burstField`：按显式种子、原点、方向、速度、阻力、重力、寿命与 `progress` 计算粒子位置、尺寸与透明度；
- `expandingRings`：每个环独立出生、半径与透明度，按 `progress` 与错峰求值；
- `dissolvePair`：返回互补的旧层与新层不透明度；
- `staggerReveal`：返回每个字符的 0–1 进度，步长压缩在窗口内；
- 字幕原语：激活窗口查询、两行切分、窗口包络与关键词切分。

所有原语 MUST 只接受显式 `progress`/0–1 进度、显式种子与显式缓动，MUST NOT 读取挂钟、帧号、上一帧状态、DOM、外部资源或计时器。相同参数与进度 MUST 产生相同输出。端点 MUST 透明或零值，不留下上一帧残影。原语 MUST NOT 内置颜色、字体、线宽、题材或事件时刻。

路径采样与锥形笔触 MAY 复用 MIT 许可的 `svg-path-properties` 与 `perfect-freehand`；引入第三方纯函数 MUST 在 `m2v/code-scene` 内封装，风格组件与作品 MUST NOT 直接导入。新增动效或可视化组件前 MUST 先检索并评估外部成熟方案，只有在无法满足逐帧确定性、许可、包体或风格边界时才允许自研，并在设计记录中写明结论。

#### Scenario: 同一进度重复求值

- **WHEN** 任一新增原语以相同参数与 `progress` 求值两次
- **THEN** 两次输出一致，不受调用时刻、调用顺序或已播放帧数影响

#### Scenario: 跳帧与端点

- **WHEN** 录制从 0.2 直接跳到 0.8，或求值 `progress` 为 0 与 1
- **THEN** 跳帧结果与逐帧求值一致，粒子、环与尾迹在端点为透明或零值

#### Scenario: 多子路径

- **WHEN** 把含多个 `M` 子路径的图标传给 `samplePath`
- **THEN** 调用明确失败并提示单子路径限制，不返回跨子路径的连续点列

#### Scenario: 未检索直接手写

- **WHEN** 新增的动效或可视化组件没有外部方案检索记录，或选型理由未写入设计记录
- **THEN** 审查判定不符合协作约定，须补检索与记录后再实施

### Requirement: 共享动效组件复用现有原语

共享 L2 组件 SHALL 复用 `primitives.ts` 与 `motion.ts`：`RollingNumber` 使用 `rollNumber`，`BarGrowth` 使用 `growSeries`，L1/L2 的缓动使用 `motion.ts` 的命名曲线或显式 `easing`。MUST NOT 复制一套近似的数字滚动、生长比例或缓动实现。

`primitives.ts` 的五项原语 MUST 继续存在并从 `m2v/code-scene` 导出；本能力 MUST NOT 删除或替换它们。

#### Scenario: 数字滚动
- **WHEN** `RollingNumber` 以 `from`、`to`、`progress` 求值
- **THEN** 其数值与文本来自 `rollNumber`，不再手写取整公式

#### Scenario: 柱状生长
- **WHEN** `BarGrowth` 以进度求值
- **THEN** 各柱比例来自 `growSeries`，不复制 stagger 计算

#### Scenario: 缓动来源
- **WHEN** 共享组件需要缓动
- **THEN** 使用调用方显式传入的 easing 或 `motion.ts` 命名曲线，不内置另一套近似曲线

### Requirement: 整屏粒子、环境微尘与节拍原语

系统 SHALL 在 `web/src/code-scene/` 提供以下纯数值原语，并从 `m2v/code-scene` 导出：

- `explosionField`：按 `progress`、显式 seed、原点、最终位移 `reach`、寿命、阻力、重力、深度范围、bokeh/streak/dust 比例求值分层粒子；返回位置、速度、年龄、尺寸、透明度、深度、模糊、角度、streak 与层名。
- `moteField`：按 `progress`、seed、画布尺寸、漂移与周期求值持续环境微尘。
- `impactEnvelope`：按 `progress` 返回闪光与环包络，端点为 0。
- `beatPhase` / `beatPulse`：按 `progress`、`durationSeconds`、BPM 与显式相位求值节拍相位与脉冲。

所有原语 MUST 只接受 0–1 `progress` 与显式参数，MUST NOT 读取帧号、挂钟、`Math.random`、上一帧状态或 DOM。相同参数与进度 MUST 产生相同输出；`explosionField` 与 `impactEnvelope` 的端点 MUST 透明或零值。`reach` MUST 表示最终最大位移，MUST NOT 因内部阻力把实际半径压缩到参数的固定小比例。粒子 MUST 按显式 seed 决定形态；改变 seed MUST 改变形态。

`beatPhase`/`beatPulse` MUST 不内置主题、颜色或事件时刻；BPM 与 duration 由调用方传入。`moteField` MUST 只做低速连续漂移，MUST NOT 用作随机闪烁或事件替代。

#### Scenario: 整屏爆炸端点与跳帧

- **WHEN** 以 `progress` 0、1 与 0.2 直接跳到 0.8 求值 `explosionField`
- **THEN** 端点全部透明，跳帧结果与逐帧求值一致

#### Scenario: 实际位移

- **WHEN** 调用方给出 `reach=1000` 与正常阻力
- **THEN** 外层粒子的最大位移接近 1000 px，而不是被阻力压到约 245 px

#### Scenario: 节拍参数

- **WHEN** 用同一 `progress`、duration 与 BPM 求值 `beatPulse` 两次
- **THEN** 结果一致；拍点附近为脉冲峰值，衰减窗口后为 0，不读帧号

#### Scenario: 状态式粒子库

- **WHEN** 以需要从 0 重放的状态式粒子引擎实现整屏冲击
- **THEN** 任意帧 seek 与纯时间采集无法满足，审查判定不符合本原语契约，须改为闭式求值

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

系统 SHALL 用 `@remotion/paths` 处理 SVG 路径生长、形变、沿线取点与几何变换，用 `@remotion/animation-utils` 处理 CSS 数值、颜色与 transform 插值，用 `@remotion/layout-utils` 做文本测量与单行适配，用 `@remotion/noise` 生成种子噪声，用 `d3-scale`/`d3-shape` 计算图表的比例尺与曲线，用 `roughjs` 生成手绘高亮几何。MUST NOT 把 `@remotion/paths` 用于 Canvas 点列、把 `@remotion/animation-utils` 用于 SVG 数值属性或 Three.js 数值、把 `@remotion/layout-utils` 的多行切词用于中文、或用 `roughjs` 草图化作品已有艺术路径。

系统 SHALL NOT 引入 `@remotion/shapes`、`@remotion/lottie`、`@remotion/transitions` 与 `@remotion/motion-blur`：`lottie` 的许可与 `useCurrentFrame` 驱动方式不适用于 code scene；`transitions` 与 `motion-blur` 只适用于 Remotion composition，code scene 的运动模糊继续使用既有子帧方案；标准形状暂用现有 SVG。

#### Scenario: SVG 路径生长
- **WHEN** 组件或作品需要按进度画出一条 SVG 路径
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

### Requirement: 图表几何统一来源

共享图表与风格的点列曲线 MUST 复用成熟库支持的统一纯函数，支持直线、单调、阶梯及 Catmull-Rom 曲线；MUST 保留已有风格接口、曲线视觉语义与显式进度。金融类型的业务时间轴与刻度策略不属于该公共几何接口。

#### Scenario: 风格平滑曲线
- **WHEN** dark-proof 绘制既有平滑点列
- **THEN** 通过统一几何生成，保留端点与平滑语义，不再维护手写贝塞尔控制点算法

### Requirement: 运动实现约定必须保持时间与数据一致

运行契约 SHALL 说明秒数乘实际 fps 得到帧位置，毫秒先除以 1000；非整数帧按既有字段和事件精度处理，不引入新的统一取整或时长阈值。共享缓动 SHALL 显式传入、保持数值有效并复用已有实现；帧驱动、受控顺序采集、纯时间与并行边界仍按现有运行契约执行，不因动态风格改变。

需要准确比较的数据动画 SHALL 在稳定窗口恢复真实数值、比例和口径；数字和图形由同一数据或进度计算。声明接触关系的对象 SHALL 依据实际绘制几何保持依赖，腾空与再次接触按事件组织并核对完整窗口。不要求所有风格模拟真实物理，也不规定每场必须出现接触、次级动作或点缀。

#### Scenario: 弹性数据与稳定比较
- **WHEN** 柱体在过渡中回弹且与读数共同表达准确数据
- **THEN** 稳定比较窗口恢复真实比例与数值，图形和数字同步，不借过冲篡改结果

#### Scenario: 对象接触与分离
- **WHEN** 小球承托于变化中的柱顶，随后腾空并落回
- **THEN** 接触窗口随实际顶面求位置，分离窗口独立求值，再次接触时恢复依赖，并用完整窗口复核

#### Scenario: 显式线性或不同方向
- **WHEN** 作品按机械、节奏或其他表达目标选择 linear、加速入场或减速离场
- **THEN** 不要求例外理由；仍满足显式缓动、数值有效和当前采集模式的确定性要求
