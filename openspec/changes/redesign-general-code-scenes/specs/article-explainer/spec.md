## RENAMED Requirements

- FROM: `### Requirement: v7 混合媒体分镜`
- TO: `### Requirement: v8 横竖屏代码分镜`

## MODIFIED Requirements

### Requirement: v8 横竖屏代码分镜
系统 MUST 只接受 version/schemaVersion 均为 8 的 general 分镜，30 fps，支持 1920×1080 横屏与 1080×1920 竖屏；width/height 均省略 MUST 默认横屏，半指定、非整数及其他尺寸 MUST 拒绝。全片 MUST 使用同一画幅，不自动裁切或重新排版。每幕 MUST 声明唯一 ID、template: code、本地 content.entry、可选 title/JSON 对象 props 及旁白数组；title 只作元数据。场景及旁白 ID MUST 全片唯一。原文输入 MUST 绑定非空源文并审查，主题输入 MUST 声明非空主题与逐幕关键词且不要求原文审查。代码幕 MUST 允许无旁白，未知字段及旧准备 MUST 拒绝。

#### Scenario: 默认与显式尺寸
- **WHEN** 尺寸均省略、显式横屏或显式竖屏
- **THEN** 分别按 1920×1080、1920×1080、1080×1920 规范化并贯穿制作

#### Scenario: 非法尺寸
- **WHEN** 只提供一边尺寸，或尺寸为布尔值、字符串、方屏或其他组合
- **THEN** 校验拒绝并定位字段

#### Scenario: 主题输入
- **WHEN** topic 作品的代码幕旁白为空且声明有效关键词与 durationFrames
- **THEN** 按声明长度准备镜头，不要求原文审查；缺少关键词则拒绝

#### Scenario: 旧分镜
- **WHEN** 输入 v7 或更早分镜
- **THEN** 要求重新编排 v8，不自动迁移

#### Scenario: 非法绑定
- **WHEN** 旧展示元素尝试用 segmentId 绑定旁白
- **THEN** 按未知字段拒绝；v8 代码改用实际 segmentWindows

#### Scenario: 代码模板
- **WHEN** 输入有效 code 场景
- **THEN** 本地录制片段参与统一音轨、字幕和转场合成

### Requirement: 默认旁白画面字幕
general MUST 无需额外配置即可从旁白原文和真实配音帧边界生成字幕，并烧录至预演和成片；外置字幕不代替画面交付。字幕 MUST 开始帧显示、结束帧隐藏，无讲话的停顿与阅读尾段不显示。两种画幅 MUST 使用各自的字幕几何和换行宽度，字幕样式 MUST 独立于作品背景保持可读，SDK 与合成层 MUST 共用安全区。作品重要文字与主体 MUST 避让安全区，背景可延伸至该区。系统 MUST NOT 宣称能够自动识别录制片段内全部正文或主体遮挡。

#### Scenario: 横竖屏字幕
- **WHEN** 分别准备有旁白的横屏和竖屏作品
- **THEN** 两者均烧录同步字幕，容器和换行在对应画布内，安全区与 SDK 一致

#### Scenario: 字幕边界和静音区间
- **WHEN** 播放至开始帧、结束帧或无讲话区间
- **THEN** 仅在对应讲话边界内显示字幕

#### Scenario: 未配置字幕选项
- **WHEN** 有旁白作品未声明字幕配置并完成制作
- **THEN** 预演和成片均包含自动烧录的字幕

#### Scenario: 深浅主题与嵌入
- **WHEN** 代码自行绘制深浅背景，或输入旧主题/完整嵌入材料
- **THEN** 有效代码场景字幕保持可读；旧主题和嵌入被拒绝

### Requirement: 讲解评审及版本绑定
系统 MUST 保留 article 输入语义审查和当前指纹完整预演，topic 输入不要求源文审查；人工画面评审 MUST 为可选工具，MUST NOT 阻断导出。源文、分镜、画幅、代码、资源、媒体记录、音轨或渲染实现变化 MUST 使依赖的准备与预演失效；可选评审不得沿用过期依据。正式输出 MUST 技术验收后替换并保留溯源，旧嵌入材料 MUST 拒绝。

#### Scenario: 输入未评审
- **WHEN** article 输入没有当前有效审查
- **THEN** 准备拒绝并提示审查

#### Scenario: 材料变化
- **WHEN** 已准备作品从横屏改为竖屏
- **THEN** 旧准备和预演失效，必须重新设计、准备和完整预演

#### Scenario: 自动预演门禁
- **WHEN** 当前完整预演缺失、限帧、过期或摘要/完整帧数不匹配
- **THEN** 正式导出拒绝且不覆盖已有有效成片；仅缺少可选视觉记录不阻断

#### Scenario: 完整嵌入
- **WHEN** 尝试引用完整作品作为场景
- **THEN** 拒绝旧嵌入契约，要求 v8 本地代码重新制作

### Requirement: 固定示例的内容驱动演示
仓库 MUST 仅保留三个现有示例：buffer-smoothing 和 keynote-baseline 使用 1920×1080，darts-trial-and-error 使用 1080×1920，均为 v8、30 fps 全画布代码场景。每片 MUST 保留论点、适用边界、120～180 秒实际时长、配音和烧录字幕；核心演示 MUST 按真实旁白时间窗推进，示意数据明确标注。合计 MUST 覆盖批准的 Motion、ECharts、GSAP、Three.js、React Three Fiber 与 Drei，MUST NOT 再要求旧模板覆盖。示例说明 MUST 记录论点、旁白、画面与组件对应关系和视觉设计依据，生成媒体不入库。

#### Scenario: 三片完整制作
- **WHEN** 三个固定示例完成准备、完整预演与导出
- **THEN** 两横一竖，实际时长符合要求，核心动画解释原论点且字幕和旁白同步

#### Scenario: 覆盖检查
- **WHEN** 检查三个固定示例的分镜及源码
- **THEN** 全部为 code 且两横一竖，合计覆盖批准组件，核心演示按旁白推进，不要求旧模板覆盖

## REMOVED Requirements

### Requirement: 六种受控画面
**Reason**: 通用画面统一使用全画布代码场景，不保留固定布局。
**Migration**: 按 v8 重写本地 TSX；图片视频经已导入媒体接口使用，无自动迁移。

### Requirement: 视觉主题
**Reason**: 配色、构图与动效改由作品设计决定，删除主题选择与节奏覆盖。
**Migration**: 删除 visual.theme，按 v8 重建设计和时间轴，不保留主题别名。

### Requirement: 主题字段的完整性
**Reason**: 不再存在运行时主题清单。
**Migration**: 旧主题配置拒绝，使用作品代码表达视觉设计。
