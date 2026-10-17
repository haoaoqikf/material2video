## MODIFIED Requirements

### Requirement: v8 横竖屏代码分镜
系统 MUST 只接受 version/schemaVersion 均为 8 的 general 分镜，60 fps，支持 1920×1080 横屏与 1080×1920 竖屏；width/height 均省略 MUST 默认横屏，半指定、非整数及其他尺寸 MUST 拒绝。全片 MUST 使用同一画幅，不自动裁切或重新排版。每幕 MUST 声明唯一 ID、template: code、本地 content.entry、可选 title/JSON 对象 props 及旁白数组；title 只作元数据。场景及旁白 ID MUST 全片唯一。原文输入 MUST 绑定非空源文并审查，主题输入 MUST 声明非空主题与逐幕关键词且不要求原文审查。代码幕 MUST 允许无旁白，未知字段及旧准备 MUST 拒绝。

每幕 MAY 声明 `leadInFrames`、`tailFrames`（0–1800 帧）与 `readingHoldFrames`（0–360 帧）；`content.props` MAY 声明 `shots` 与 `look` 对象，旁白段 MAY 声明 `claims` 字符串数组。未声明时 MUST 保持当前时间轴、阅读停留与画面行为。字段类型、范围或时间窗非法时 MUST 拒绝并定位到具体幕、镜头或旁白段。镜头时间窗 MUST 落在所属幕内且不得重叠；`tier` 只能是 hero、major 或 minor；cinematic 作品的 hero 镜头 MUST 不少于 3 个。

#### Scenario: 默认与显式尺寸
- **WHEN** 尺寸均省略、显式横屏或显式竖屏
- **THEN** 分别按 1920×1080、1920×1080、1080×1920 规范化并贯穿制作

#### Scenario: 非法尺寸
- **WHEN** 只提供一边尺寸，或尺寸为布尔值、字符串、方屏或其他组合
- **THEN** 校验拒绝并定位字段

#### Scenario: 旧分镜
- **WHEN** 输入 v7 或更早分镜
- **THEN** 要求重新编排 v8，不自动迁移

#### Scenario: 主题输入
- **WHEN** topic 作品的代码幕旁白为空且声明有效关键词与 durationFrames
- **THEN** 按声明长度准备镜头，不要求原文审查；缺少关键词则拒绝

#### Scenario: 非法绑定
- **WHEN** 旧展示元素尝试用 segmentId 绑定旁白
- **THEN** 按未知字段拒绝；v8 代码改用实际 segmentWindows

#### Scenario: 代码模板
- **WHEN** 输入有效 code 场景
- **THEN** 本地录制片段参与统一音轨、字幕和转场合成

#### Scenario: 静音前后段
- **WHEN** 某幕声明有效的 leadInFrames 或 tailFrames
- **THEN** 旁白前后出现对应静音，时间轴与字幕整体后移，不截断或重叠旁白；未声明时行为与当前一致

#### Scenario: 非法电影字段
- **WHEN** shots 的时间窗越界或重叠、tier 非法，或 look/claims 字段类型错误
- **THEN** 校验拒绝并指出具体幕、镜头或旁白段

### Requirement: 实际语音时间与十分钟上限
系统 MUST 复用项目 TTS 配置与缓存，根据每段实际音频计算展示和字幕时间；每幕结束保留默认 24 帧阅读时间，可由 `readingHoldFrames` 覆盖。`leadInFrames` 与 `tailFrames` MUST 在旁白前后增加静音，不截断、不重叠旁白。默认硬切，可选 fade/crossfade 并按声明帧数重叠，旁白不得重叠。默认目标 60 秒，全片 MUST 不超过 36000 帧；无旁白幕 MUST 支持声明固定帧数或均分目标剩余时长，超限要求调整文本或语速，不截断声音。

#### Scenario: 时长边界
- **WHEN** 准备结果为 36000 帧或 36001 帧
- **THEN** 前者通过，后者拒绝

#### Scenario: 无旁白镜头分配
- **WHEN** 某幕声明 `durationFrames`，另一幕没有旁白也没有声明帧数
- **THEN** 前者按声明帧数、后者按目标剩余时长分配，两者都不截断口播

#### Scenario: 淡化
- **WHEN** 两幕使用淡化衔接
- **THEN** 画面淡化期间两幕旁白不重叠，前幕保持完整阅读尾段

#### Scenario: 自定义阅读停留
- **WHEN** 某幕声明 `readingHoldFrames` 为 90
- **THEN** 该幕旁白结束后保留 90 帧阅读时间，其余幕仍取默认 24 帧或各自声明值

#### Scenario: 片头片尾留白
- **WHEN** 首幕声明 `leadInFrames` 且末幕声明 `tailFrames`
- **THEN** 成片在首句旁白前和末句旁白后保留对应静音，总帧数包含这两段留白

### Requirement: 固定示例的内容驱动演示
仓库 MUST 仅分发 buffer-smoothing、darts-trial-and-error、solar-system-journey 三个固定示例；前后两者使用 1920×1080，试错使用 1080×1920，均为 v8、60 fps。缓冲与试错实际时长 MUST 为 120～180 秒，太阳系之旅 MUST 为 55～65 秒，均含中文旁白和烧录字幕。核心演示 MUST 按实际旁白时间窗推进，合计覆盖 Motion、ECharts、GSAP、Three.js、React Three Fiber 与 Drei。示例 MUST 提供可编辑材料、设计说明、素材来源和旁白与画面的对应关系，生成媒体 MUST NOT 入库。

太阳系之旅 MUST 使用 cinematic 档位：9 个章节、9 段旁白、约 60 秒目标；MUST 提供 3 个 hero 镜头（地球、土星、奥尔特云）、4K look-dev 静帧、20–30 秒有声样片、hero 实看记录、配乐与音效，以及 cinematic 母版与 H.264 交付。缓冲与试错 MUST 保持 standard 档位，作为现有快速链路的回归。

#### Scenario: 三片完整制作
- **WHEN** 使用三个固定示例通过统一入口完成准备、完整预演与导出
- **THEN** 成片具有对应画幅、60 fps、实际配音和烧录字幕，保存到各自 videos/examples/<slug>/outputs，时长满足各自范围

#### Scenario: 覆盖检查
- **WHEN** 检查固定示例分镜与源码
- **THEN** 只有三个指定示例，合计覆盖批准组件，核心代码场景包含按时间窗推进的旁白，并明确标注示意内容

#### Scenario: 太阳系向外旅行
- **WHEN** 播放太阳系之旅
- **THEN** 成片时长为 55～65 秒，按太阳、内行星、地月、小行星带、木星、土星、冰巨星、柯伊伯带、边缘九个章节向外推进；地球、土星与奥尔特云为 hero 镜头；全片在同一个完整三维太阳系模型中保留太阳、行星、卫星和轨道，不再每段返回同一总览机位；标注大小距离非同比例，并区分日球层顶与推测性奥尔特云

#### Scenario: 写实画面验收
- **WHEN** 完成太阳系示例的交付验证
- **THEN** 提供 3 个 hero 的 4K 静帧与 20–30 秒有声样片，实际观看并记录时间码、问题与复查；提供配乐/音效、QA 报告、cinematic 母版与兼容交付；不将艺术示意表述为实拍或精确历算

#### Scenario: 标准档回归
- **WHEN** 缓冲或试错完成准备、完整预演与导出
- **THEN** 不因 cinematic 字段或后期依赖改变时间轴、编码参数或现有画面行为
