# react-code-scenes Specification

## Purpose

规范五类视频共用的本地 React 代码场景、逐帧录制、纯时间采集与共享绘制组件，使画面由受控时间确定、资源来源可追溯、片段缓存可复用，并通过实际媒体复核视觉效果。

## Requirements

### Requirement: 本地代码场景

本要求只约束作品实际采用的本地实现和默认工程模板。主项目 MUST NOT 提供强制运行时SDK；构建器 MUST 从作品自身安装和锁文件解析依赖，MUST NOT 读取主项目源码或全局依赖登记。参考未被采用时 MUST NOT 成为构建或指纹输入。

系统 MUST 接受 scenes 下 TSX 默认导出的 React 组件及 JSON 对象参数，提供 fps、时长、实际 width/height、字幕安全区、本幕旁白时间窗及录制进度；MUST NOT 提供 theme。场景 MUST 控制完整画布，作品绘制标题、内容及不透明背景，本地合成层仅合成片段与字幕。系统 MUST 拒绝路径越界、未批准依赖和远程模块，不安装作品依赖。场景 MUST 支持无旁白，声音由统一音轨处理。

#### Scenario: 有效入口
- **WHEN** 录制有效横屏或竖屏入口
- **THEN** 作品本地模块 与录制 viewport 均采用实际画幅，无固定标题及内容框

#### Scenario: 无效导入
- **WHEN** 代码越过作品边界或引用未批准包及远程模块
- **THEN** 构建失败并指出原因

### Requirement: 逐帧录制及复用

本要求只约束作品实际采用的本地实现和默认工程模板。主项目 MUST NOT 提供强制运行时SDK；构建器 MUST 从作品自身安装和锁文件解析依赖，MUST NOT 读取主项目源码或全局依赖登记。参考未被采用时 MUST NOT 成为构建或指纹输入。

系统 MUST 等待字体、组件及显式资源就绪后录制；超时、外网请求或运行异常 MUST 失败且不保存有效准备。录制 MUST 按顺序在第 n/fps 秒完成动画更新和绘制后逐帧采集，截图与磁盘等待 MUST NOT 推进动画；系统 MUST 同步上下文、动画库、三维绘制、CSS 动画和本地视频。录制 MUST 标准化为实际画幅、精确帧数、作品实际30或60 fps的无声视频，并恢复落盘目录继承权限。缓存 MUST 绑定源码、资源、参数、时间窗、依赖、实现、帧率、画幅、字幕安全区配置及素材导入映射和摘要。完整预演及正式导出 MUST 复用同一已验收片段，不在导出执行作品代码；自由动画不承诺逐像素复现。

#### Scenario: 输入变化
- **WHEN** 仅改变画幅、安全区配置、登记媒体内容或作品帧率
- **THEN** 旧缓存及准备失效，重新录制并要求完整预演

#### Scenario: 两种帧率的场景缓存隔离
- **WHEN** 相同代码、帧预算与素材分别按30 fps和60 fps录制
- **THEN** 相同时间点画面保持相同，片长保持相同，帧数按帧率变化，缓存互不复用

#### Scenario: 运行失败
- **WHEN** 代码异常、请求外网或未及时 ready
- **THEN** prepare 失败且不发布有效准备记录

#### Scenario: 正式导出
- **WHEN** 输入完全一致且片段完整，或当前准备和预演有效后正式导出
- **THEN** 复用相同片段，不重新录制，片段可按目录继承权限直接打开

#### Scenario: 片段可直接打开
- **WHEN** 录制片段从临时目录落盘
- **THEN** 恢复目标目录继承权限，用户可直接播放

#### Scenario: 采集变慢
- **WHEN** 截图或磁盘写入延迟
- **THEN** 下一帧仍对应下一固定时间点，不跳过运动状态或补重复帧

#### Scenario: 精确采集
- **WHEN** 顺序录制 N 帧并编码
- **THEN** 采集和解码均为 N 帧，缺帧或推进异常明确失败，不发布缓存；旧实时缓存不能复用

### Requirement: 已导入媒体解析
代码场景 MUST 能按素材 ID 获取本地地址、类型、实测宽高、视频时长、色彩空间、alpha 标记与登记许可；未知 ID MUST 明确失败。接口 MUST 仅暴露已登记且摘要有效的素材，MUST NOT 允许借直接文件地址绕过留证。媒体比例 MUST 不受画幅限制，裁切、布局和播放由作品代码控制。视频原声 MUST NOT 隐式进入母版。

#### Scenario: 图片及视频
- **WHEN** 代码解析已导入的横图或视频用于竖屏作品
- **THEN** 返回有效本地地址、实测元数据、色彩空间、alpha 与许可，不因素材比例拒绝；成片声音仅来自统一音轨

#### Scenario: 非法素材
- **WHEN** 素材未登记、ID 不存在、摘要不符或试图访问边界外文件
- **THEN** 准备或资源解析明确失败，不静默替换

#### Scenario: 电影级资产元数据
- **WHEN** 作品解析 hero 纹理
- **THEN** 返回色彩空间、alpha 与许可；作品可据色彩空间设置 sRGB/线性，并在片尾署名

### Requirement: 电影级镜头与后期接口

本要求只约束作品实际采用的本地实现和默认工程模板。主项目 MUST NOT 提供强制运行时SDK；构建器 MUST 从作品自身安装和锁文件解析依赖，MUST NOT 读取主项目源码或全局依赖登记。参考未被采用时 MUST NOT 成为构建或指纹输入。

系统 MUST 在 作品本地模块 提供电影级共享接口：`PostFX`（Bloom、DOF、grain、vignette、chromatic aberration、LUT）、`CameraRig`（CatmullRom/Bezier 路径、缓动、FOV、滚转、曝光、焦点拉移、穿球与背景裁切检查）、`LookProvider`，以及星空、粒子带、大气、环、日面、日冕、日珥、奥尔特云与彗星组件。MUST 提供按镜头选择的采集质量（默认1倍/1子帧，可按look配置重点镜头1–2倍/1–4子帧）。

后期 MUST 只作用于代码场景 canvas，MUST NOT 覆盖或改变共享字幕 DOM 层。全部后期与粒子参数 MUST 由 `elapsedSeconds` 或帧号驱动，MUST NOT 使用挂钟、`Math.random`、CSS animation、组件计时器或未受控的异步状态；粒子噪声 MUST 使用「帧号 + shot id」的确定性种子。源码闸门 MUST 继续拒绝禁用写法。

系统 MUST 批准并按作品需要本地声明 `postprocessing` 与 `@react-three/postprocessing`，并把依赖、shots、look、后期参数纳入代码片段缓存键。缺少依赖或版本不匹配时 MUST 在打包/准备前明确失败，MUST NOT 输出无后期或部分后期的画面。作品不声明 shots/look 时 MUST 保持当前 作品本地模块 行为与画质。

#### Scenario: 确定性后期
- **WHEN** 同一帧连续渲染两次并比对
- **THEN** 两次画面相似度 ≥ 60dB；若 Bloom、DOF、grain 或粒子因时间/随机源变化而不同，判定失败并定位到该帧

#### Scenario: 缺少后期依赖
- **WHEN** 作品引用了 PostFX 但前端依赖未安装或版本不匹配
- **THEN** 打包或准备前失败并指出依赖，不产出缺少后期的片段

#### Scenario: 标准作品不受影响
- **WHEN** 作品的场景未声明 shots/look 且未引用 PostFX
- **THEN** 作品本地模块默认画面行为保持不变，采集配置绑定统一契约并使旧片段缓存失效

#### Scenario: 后期不覆盖字幕
- **WHEN** 代码场景使用 Bloom、DOF 或 LUT 渲染
- **THEN** 共享字幕层仍按原有几何与样式绘制，不被后期模糊、变色或裁切

#### Scenario: 镜头校验
- **WHEN** shots 的时间窗越界、重叠或与旁白段不匹配
- **THEN** 准备失败并指出具体 shot 与时间窗

### Requirement: 绘制层必须按采集像素密度分配

绘制层的画布后备缓冲 MUST 按当前采集像素密度分配，并按同一密度换算绘制坐标。像素密度取自录制配置；未声明时按 1 倍处理。后备缓冲不足 MUST 明确失败，MUST NOT 以放大低分辨率画布代替。

#### Scenario: 二倍原生采集

- **WHEN** 以 2 倍像素密度采集使用绘制层的场景
- **THEN** 画布后备缓冲达到逻辑尺寸的两倍，绘制内容按同一比例换算，不触发像素不足失败

#### Scenario: 像素不足

- **WHEN** 绘制层未按采集密度分配后备缓冲
- **THEN** 采集失败并指出画布尺寸不足，不静默放大输出

### Requirement: 绘制层进入实现指纹并受确定性检查覆盖

本要求只约束作品实际采用的本地实现和默认工程模板。主项目 MUST NOT 提供强制运行时SDK；构建器 MUST 从作品自身安装和锁文件解析依赖，MUST NOT 读取主项目源码或全局依赖登记。参考未被采用时 MUST NOT 成为构建或指纹输入。

作品实际采用的本地绘制层文件 SHALL 计入相应代码场景的输入指纹，其变化 MUST 使既有准备与片段缓存失效。绘制层的确定性 MUST 由源码检查覆盖；当生产链路的检查范围不包含该目录时，SHALL 由自动化测试对其执行同一检查，MUST NOT 因未进入生产扫描而免检。

绘制层的文本 SHALL 经现有字体缺字检查覆盖：绘制层 MUST NOT 内嵌面向观众的中文文案，文案 MUST 通过作品参数或文字计划传入，使字体体检能够发现缺字。

#### Scenario: 修改绘制层

- **WHEN** 作品内实际采用的本地绘制层实现发生变化
- **THEN** 引用该层的作品准备记录失效并需要重新准备，旧片段缓存不复用

#### Scenario: 检查范围不含该目录

- **WHEN** 生产链路的确定性检查范围不覆盖绘制层目录
- **THEN** 自动化测试对同一目录执行相同检查，违规写法使测试失败

#### Scenario: 内嵌文案

- **WHEN** 绘制层把面向观众的文案写在内嵌字符串里
- **THEN** 判为违规：文案须由作品传入，否则字体缺字检查无法发现

### Requirement: 确定性绘制组合与数值关键帧
代码场景 MUST 提供离屏分组绘制与数值关键帧求值能力。离屏分组 MUST 将子绘制作为整体应用透明度、变换与混合，并支持嵌套及缓冲复用；数值关键帧 MUST 对严格递增的有限数值时间点进行确定性求值，支持线性、保持和平滑插值，并在首尾之外保持端点值。

#### Scenario: 对重叠图形整体应用透明度
- **WHEN** 场景将多个重叠图形放入离屏分组并应用整体透明度
- **THEN** 重叠部分按整体合成语义呈现，嵌套分组可正常合成，缓冲可安全复用

#### Scenario: 对不等间隔关键帧求值
- **WHEN** 场景使用不等间隔的有限关键帧查询中间时刻
- **THEN** 相同输入得到相同数值，并按指定插值方式求值；无效排序或非有限值被拒绝

### Requirement: 模拟演示必须可回放且可复算
开发货架中的模拟演示 MUST 使用固定种子或等价的确定性预计算状态，使任意时间点可独立读取，累计结果与显示曲线来自同一组模拟数据。

#### Scenario: 重复读取模拟时刻
- **WHEN** 使用同一种子重复生成模拟，或以任意顺序查询时间点
- **THEN** 相同时间点状态一致，累计值与曲线数据一致

### Requirement: 可选全局时间与场景时间轴注入

代码场景 MAY 在 `content.props.capture` 声明 `timebase` 为 `local` 或 `global`（默认 `local`）。声明 `global` 时，录制配置 SHALL 注入 `timeline`，至少包含 `sceneStartFrame`、`sceneEndFrame` 与 `durationInFrames`；录制上下文 SHALL 提供 `globalFrame` 与 `globalSeconds`。`globalFrame` SHALL 等于 `sceneStartFrame + 幕内帧号`，子帧 SHALL 保留分数；`globalSeconds` SHALL 等于 `sceneStartFrame / fps + elapsedSeconds`。

未声明 `global` 时，录制配置 SHALL 逐字节保持既有形状，`globalSeconds` SHALL 等于 `elapsedSeconds`。既有片段缓存键 SHALL NOT 因本能力改变；声明 `global` 后，`sceneStartFrame` SHALL 进入缓存键，使前幕时长变化时正确失效。

#### Scenario: 声明全局时间

- **WHEN** 一幕声明 `capture.timebase: "global"` 且位于全片第 468 帧
- **THEN** 录制上下文在该幕第 0 帧报告 `globalFrame = 468`，第 n 帧报告 `globalFrame = 468 + n`，子帧保留小数

#### Scenario: 未声明全局时间

- **WHEN** 幕没有声明 `capture.timebase: "global"`
- **THEN** 录制配置与既有版本一致，`globalSeconds === elapsedSeconds`，旧片段缓存可继续复用

#### Scenario: 前幕时长变化

- **WHEN** 使用全局时间的幕因前幕时长变化而移动到新的全片起点
- **THEN** 该幕片段缓存失效并重新录制，全局状态按新起点求值

### Requirement: 可选纯时间采集

代码场景 MAY 在 `content.props.capture` 声明 `mode: "pure-time"`。pure 场景 MUST 只由 `elapsedSeconds`、`globalSeconds`、`props` 与 `eventFrames` 推导画面，MUST NOT 依赖计时器、随机源、CSS 动效、`useFrame`、ECharts 动画或自走媒体播放。`pure-time` SHALL 隐含 `timebase: "global"`。`jobs` SHALL 为 1–4，`blockFrames` SHALL 默认等于 fps，`verifyFrames` SHALL 为 2–4。

pure 模式 SHALL 支持绝对 seek：允许跳帧与倒序，并 SHALL 在挂载前把块首帧写入录制页，使页面从块首时间开始。片段 SHALL 按 `blockFrames` 对齐并可按块并行采集；块可复用缓存。未声明 pure 的场景 MUST 保持既有顺序采集、配置与缓存键。

pure 场景 MUST 通过静态源码闸门与动态探针：探针帧正序与倒序截图 PSNR ≥ 60 dB，相邻块边界见证帧一致。任一失败 SHALL 明确拒绝 pure 模式并指出场景与帧号，MUST NOT 静默回退顺序采集或发布未验证片段。

#### Scenario: 直接取任意帧

- **WHEN** pure 场景请求第 1200–1500 帧窗口
- **THEN** 采集直接从第 1200 帧开始，不推进第 0–1199 帧；帧内容与顺序采集的同一帧等价

#### Scenario: 未声明 pure

- **WHEN** 场景没有声明 `capture.mode: "pure-time"`
- **THEN** 仍按连续帧顺序采集，配置与片段缓存键保持既有形状

#### Scenario: 伪纯场景

- **WHEN** pure 场景使用计时器、随机源或自走动画，导致倒序探针与正序结果不一致
- **THEN** 采集失败并指出场景与帧号，不写 receipt、不发布缓存

#### Scenario: 分块并行

- **WHEN** pure 场景声明 `jobs: 2` 并请求完整区间
- **THEN** 各块独立采集后无损拼接，总帧数、尺寸、帧率与单进程结果一致

#### Scenario: 块级复用

- **WHEN** 先预览某窗口、再渲染全片
- **THEN** 已对齐的块被复用，只采集缺口；预演窗口按块起点回放，不出现错位

### Requirement: 代码场景 SDK 导出纯动效与字幕模块

本要求只约束作品实际采用的本地实现和默认工程模板。主项目 MUST NOT 提供强制运行时SDK；构建器 MUST 从作品自身安装和锁文件解析依赖，MUST NOT 读取主项目源码或全局依赖登记。参考未被采用时 MUST NOT 成为构建或指纹输入。

作品采用相应能力时，本地模块 SHALL 提供 `random.ts`、`dynamics.ts` 与 `subtitles.ts` 中实际需要的公开符号，使作品与风格组件在不直接依赖第三方包的情况下使用固定种子、路径采样、光轨、爆散、扩散环、互补溶解、逐字错峰与字幕窗口工具。

第三方纯函数库（`svg-path-properties`、`perfect-freehand`）MAY 以显式命名导出。作品本地模块 MUST NOT 以 `export *` 暴露整个第三方包，以免重名与无意扩大 API。已采用模块 MUST 进入作品实际构建输入指纹，使其变化使引用作品的准备与片段缓存失效。

#### Scenario: 作品使用动效原语

- **WHEN** 场景从 作品本地模块 导入 `sampleTrail` 或 `staggerReveal`
- **THEN** 导入本地模块成功；该模块需要的第三方依赖已在作品package.json声明并由本地锁文件锁定

#### Scenario: 模块变化使缓存失效

- **WHEN** 修改 `dynamics.ts` 或 `subtitles.ts`
- **THEN** 引用作品的准备指纹与片段缓存失效，必须重新准备并复查

#### Scenario: 直接导入第三方包

- **WHEN** 风格组件或作品源码直接 `import` `svg-path-properties`、`perfect-freehand` 或其他新增第三方动效库
- **THEN** 依赖已在作品声明、固定版本且符合当前采集模式时构建成功；未声明或版本失配明确失败

### Requirement: 共享动效组件兼容代码场景

本要求只约束作品实际采用的本地实现和默认工程模板。主项目 MUST NOT 提供强制运行时SDK；构建器 MUST 从作品自身安装和锁文件解析依赖，MUST NOT 读取主项目源码或全局依赖登记。参考未被采用时 MUST NOT 成为构建或指纹输入。

代码场景 SHALL 通过 作品本地模块 使用已采用的本地组件，包括 L1/L2 动效、文本排版（`AutoFitText`、`TextBlock`）、路径形变与遮罩（`PathMorph`、`MaskReveal`）、圆弧进度（`ArcGauge`、`ProgressRing`）、种子噪声（`NoiseDrift`）、纯时间图表（`LinePlot`、`AreaPlot`、`Sparkline`、`Axis`）、时间轴与章节轨（`Timeline`、`ChapterTrack`）、象形图（`Pictogram`、`IconGrid`）与波形（`Waveform`）。

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

### Requirement: 透明整屏效果层由代码场景 SDK 导出

本要求只约束作品实际采用的本地实现和默认工程模板。主项目 MUST NOT 提供强制运行时SDK；构建器 MUST 从作品自身安装和锁文件解析依赖，MUST NOT 读取主项目源码或全局依赖登记。参考未被采用时 MUST NOT 成为构建或指纹输入。

采用整屏效果或节拍能力的作品 SHALL 在本地提供所需的 `ScreenBurstLayer` 或 `explosionField`/`moteField`/`beatPhase`/`beatPulse`，使作品可以在不直接导入第三方包的情况下绘制整屏粒子冲击与节拍脉冲。

`ScreenBurstLayer` MUST 使用透明 Canvas，内部缓冲按 `__M2V_CODE_CONFIG__.captureScale` 分配；MUST 在 React layout effect 中按当前帧同步重绘；MUST NOT 使用 `requestAnimationFrame`、`useFrame`、计时器或逐帧累积状态。MUST 支持字幕安全区下方的 alpha 淡出，MUST NOT 遮挡共享字幕层。

粒子 sprite MAY 预渲染并缓存；sprite 只承担柔光/虚化观感，颜色、数量、事件时刻 MUST 由调用方传入。新增模块 MUST 进入 `implementation_inputs()` 与源码确定性闸门。

#### Scenario: 逐帧采集

- **WHEN** 同一帧在 lookdev 与正式渲染中分别采集
- **THEN** Canvas 粒子层按同一 `frame`、seed 与 captureScale 重绘，不依赖上一帧或真实时间

#### Scenario: 字幕安全区

- **WHEN** 整屏冲击发生在字幕窗口内
- **THEN** 粒子在字幕安全区上方开始淡出，字幕文字保持可见

#### Scenario: 直接使用状态式引擎

- **WHEN** 作品或风格组件直接引入 `requestAnimationFrame` 驱动的粒子引擎
- **THEN** 源码闸门或审查明确失败，须改为 作品本地模块 的闭式效果层

### Requirement: 五类共用场景与结构化来源

本要求只约束作品实际采用的本地实现和默认工程模板。主项目 MUST NOT 提供强制运行时SDK；构建器 MUST 从作品自身安装和锁文件解析依赖，MUST NOT 读取主项目源码或全局依赖登记。参考未被采用时 MUST NOT 成为构建或指纹输入。

五类 MUST 经各作品自己的本地代码场景打包与逐帧采集链路进入单一成片 composition；场景 作品本地模块 MUST 按 ID 暴露已准备的结构化来源，并保留已导入媒体、帧驱动动效和安全边界。风格包导入 MUST 被拒绝。

#### Scenario: 结构化来源进入场景
- **WHEN** 数据演化或三维空间场景读取有效来源 ID
- **THEN** 收到已校验且与准备指纹绑定的结果

#### Scenario: 已删除风格导入
- **WHEN** 场景导入 `m2v/style` 或其子路径
- **THEN** 打包明确失败，不回退为未选风格

### Requirement: 可选二维绘制层与媒体复核
主项目 SHALL 提供可选择采用的二维Canvas绘制参考，采用后由作品本地提供和显式导入；不导入时既有画面 MUST 保持不变。绘制层 SHALL 提供由帧号或已受控时间驱动的绘制原语，覆盖光晕、光点、尾迹、线、折线、圆、椭圆、矩形、路径、文字、逐字绘制、排版测量与渐变。绘制原语 MUST NOT 内置颜色、字体或主题，MUST NOT 读取挂钟、随机源、上一帧状态或组件计时器。

绘制层 SHALL 提供确定性的相机求值原语 `cameraAt(keys, progress)`：输入按进度升序的关键帧（各含 `scale`、焦点 `x`/`y`）与 0–1 进度，返回 `{scale, focusX, focusY}`。`scale` MUST 在**对数空间**插值，使等距视觉推拉对应几何级数；焦点 MUST 按缩放反比加权插值，使推近时焦点更快贴到目标对象。求值 MUST 是纯函数：同一输入每次返回相同结果，进度 0 与 1 MUST 精确返回首末关键帧值，不含随机与时间源。相机原语 MUST NOT 改变绘制坐标系或替代调用方的变换；它只返回值，由调用方决定如何施加。

作品已采用的绘制层与组件 MUST 不再输出旧画面量测代理、状态探针或角色适配属性。实际构图、可读性与动态表现 MUST 由当前媒体证据复核；采集像素密度、文字排版、相机和帧驱动绘制行为保持。

#### Scenario: 未使用绘制层

- **WHEN** 作品不导入绘制层
- **THEN** 画面与引入绘制层之前一致，不新增元素或绘制调用

#### Scenario: 相机求值确定性

- **WHEN** 同一关键帧表与同一进度被求值两次，或进度取 0 与 1
- **THEN** 两次结果完全相同，且首末进度分别精确等于首个与末个关键帧的值

#### Scenario: 对数缩放插值

- **WHEN** 关键帧缩放为 1 与 4、进度取中点
- **THEN** 返回的缩放为 2 而非 2.5，推拉在视觉上等速

#### Scenario: 禁止的时间与随机源

- **WHEN** 绘制层实现中出现挂钟、随机数、计时器或未关闭的 CSS 动画
- **THEN** 确定性源码检查失败并指出文件与行号

#### Scenario: 媒体复核替代声明量测
- **WHEN** 绘制层或共享组件输出实际画面
- **THEN** 不生成隐藏角色标记或探针，独立评审通过媒体窗口观察实际效果。

### Requirement: 可扩展的作品依赖登记

本要求只约束作品实际采用的本地实现和默认工程模板。主项目 MUST NOT 提供强制运行时SDK；构建器 MUST 从作品自身安装和锁文件解析依赖，MUST NOT 读取主项目源码或全局依赖登记。参考未被采用时 MUST NOT 成为构建或指纹输入。

作品直接使用的第三方依赖 MUST 由可扩展登记声明固定版本、来源、许可及适配依据，系统 MUST 按登记校验实际安装版本后本地解析。MUST 允许为目标品质新增合适依赖或适配组件，不以硬编码名单永久限制实现；目录边界、外网限制、资源就绪与时钟检查继续适用，登记变化 MUST 进入源码及缓存绑定。

#### Scenario: 新登记依赖
- **WHEN** 一个已安装依赖经过选型和适配验证并加入登记
- **THEN** 作品 MUST 能导入它，无需修改打包器中的固定包名集合；未登记、版本失配或记录无效 MUST 明确失败。

#### Scenario: 自走组件适配
- **WHEN** 外部组件默认使用自主时钟或异步状态
- **THEN** 助手 MUST 通过受控时钟、时间定位或预计算验证接入，不能自动将其视作pure-time，也不能仅因默认自走就永久排除适配。

#### Scenario: CSS和外部资源进入正式录制
- **WHEN** 作品构建产生样式表或登记加载器的本地资源
- **THEN** 顺序缺口、纯时间并行块与样品网页 MUST 复制同一构建产物清单；编译输入摘要 MUST 对应实际读取字节，构建期间来源变化 MUST 拒绝绑定旧bundle为新来源。

### Requirement: 受控帧等待已登记异步绘制

场景上下文 SHALL 提供waitForFrame(task)登记PromiseLike异步绘制工作。宿主 MUST 在初始就绪及每次帧或子帧提交完成前，等待已登记工作、链式新增工作与最终浏览器绘制屏障；等待 MUST NOT 推进作品时间。非法任务、登记任务拒绝、未在既有deadline内完成或同一宿主重叠提交 MUST 明确失败，MUST NOT 把旧画面作为新帧发布。未登记异步工作不获得完成或确定性保证；既有源码限制与pure-time正反序检查 MUST 保持。

#### Scenario: 异步Canvas完成后采集

- **WHEN** 场景按当前帧生成Bitmap并登记绘制Promise
- **THEN** 对应帧只在Bitmap绘制完成及paint后采集，顺序与pure-time任意定位得到对应状态

#### Scenario: 初始及启动工作

- **WHEN** 场景在初始ready前或start触发的effect中登记绘制
- **THEN** 初始就绪或首帧提交等待这些工作，不因多个ready调用提前放行

#### Scenario: 异步工作失败

- **WHEN** 已登记任务拒绝或长期不完成
- **THEN** 异常或既有超时使采集失败，不发布有效采集、缓存或准备

#### Scenario: 非法任务与重叠提交

- **WHEN** 调用传入非PromiseLike，或上一帧提交尚未完成就请求下一次提交
- **THEN** 宿主明确拒绝，不能清除正在执行的帧或静默采集旧画面

#### Scenario: 同步场景

- **WHEN** 场景未登记异步绘制任务
- **THEN** 继续按既有受控时间、帧序和绘制行为采集；实现源码摘要变化仍按既有规则使旧缓存失效
