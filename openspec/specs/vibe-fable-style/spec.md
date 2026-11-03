# B 寓言风格包 Specification

## Purpose

把已登记参考项目的 B 寓言外观转成仓库内可安装、可验证的风格包，使通用作品能复用同一套扁平插画舞台、三层视差、本能读数仪表、对照计数与规则卡，而不是每次手工复刻；同时为每个正式风格提供可校验的规范示例，证明风格包能落到成片上。风格包只提供表现层，不改变视频类型、制作门或验收条件。

## Requirements

### Requirement: B 寓言风格包可用

仓库 SHALL 提供 `styles/vibe-fable/`，清单 SHALL 声明 `types: ["general"]` 与 `frames: [{"width":1920,"height":1080}]`，并提供非空 `GUIDE.md` 与 `tokens.json`。作品通过 `project.json` 的 `style.id: "vibe-fable"` 选择后，`m2v validate` 与 `m2v prepare` SHALL 记录其 id、version 与内容指纹；包内容变化 SHALL 使旧准备失效。

#### Scenario: 选择风格并准备

- **WHEN** 一个 general 横屏作品声明 `style.id: "vibe-fable"` 并执行 `prepare`
- **THEN** 准备产物记录风格身份与指纹，`m2v status` 显示所选风格与准备有效性

#### Scenario: 不兼容选择

- **WHEN** 非 general 作品、竖屏作品或未知风格 id 选择该包
- **THEN** 校验明确失败并指出类型或画幅不匹配，不回退到无风格

### Requirement: 旁白要求与字体来源

`vibe-fable` SHALL 声明 `requires.narration = "none"`；含旁白的作品选择该包时 `validate` 与 `prepare` SHALL 明确失败。本包 SHALL NOT 携带字体资产，画面使用宿主已注册的 `M2V Sans` 与 `M2V Inter`；包内 SHALL NOT 新增字体恢复步骤或绕过全局字体注册。

#### Scenario: 有旁白作品误选

- **WHEN** 任一幕含 `narrationSegments` 的作品选择 `vibe-fable`
- **THEN** `validate` 与 `prepare` 明确失败，不静默改用共享字幕层

#### Scenario: 字体来源

- **WHEN** 检查风格包清单与资产
- **THEN** 清单不含 `assets`，场景通过宿主的全局字体渲染，不出现包内字体文件

### Requirement: 色板、场景配色与版式参数

`tokens.json` SHALL 提供暖白文字、规则句金、「超常」红、卡片纸与深棕卡片字，以及五个场景配色；具体取值与用法见 `styles/vibe-fable/GUIDE.md` 与 `tokens.json`。颜色语义 SHALL 全片一致，红色只表达「超常」。版式参数 SHALL 由 GUIDE 与 `tokens.json` 提供。字幕安全区 SHALL 只由场景上下文 `subtitleSafeArea` 提供，tokens SHALL NOT 复制一份几何。

#### Scenario: 场景读取配色

- **WHEN** 场景导入 `m2v/style` 的 `tokens` 并请求已登记的场景名
- **THEN** 得到该场景的天空、地面与点缀色；请求未登记的场景名时组件明确抛错，不静默回退

### Requirement: 可复用组件

风格包 SHALL 提供 GUIDE 列出的舞台、三层视差、本能读数仪表、场景说明、顶部结论行、对照计数、引线标注、规则卡、片名卡与屏幕字幕组件；具体参数见 `styles/vibe-fable/GUIDE.md`。组件 SHALL 使用受控帧号与固定种子，SHALL NOT 使用挂钟、`Math.random`、CSS 动画或组件计时器。组件 SHALL NOT 自动修改作品画面，必须由作品显式导入。角色画法 SHALL 由作品自行实现，包内 SHALL NOT 提供通用角色组件。

#### Scenario: 确定性绘制

- **WHEN** 同一作品帧被两次独立录制
- **THEN** 同一帧画面一致，不因运行时刻或随机数变化

#### Scenario: 未显式导入

- **WHEN** 作品声明了风格但场景没有导入任何组件
- **THEN** 画面与未选择风格时相同，不发生自动换肤

### Requirement: 风格示例必须可校验并与包分离

仓库 SHALL 在目录 `styles/<style-id>/examples/<slug>/` 为每个正式风格提供规范示例；完整名单、通用校验、素材留证与生成媒体不入库要求见 `article-explainer` 的「随附风格示例集合」。示例 SHALL 声明其演示的 `style.id` 并通过 v8 契约校验；其旁白与文字模式 SHALL 与所属风格契约一致：`vibe-night` / `vibe-fable` / `dark-proof` 无旁白并使用屏幕字幕，`doc-archive` / `count-ledger` 无旁白且文字画在场景内，`deep-journey` 保留旁白与共享字幕。风格发现 SHALL 只读取 styles 的直接子目录，SHALL NOT 把示例目录当作风格包。示例 SHALL NOT 改变其他风格的示例集合，也 SHALL NOT 改变任何风格包的指纹。

#### Scenario: 示例不被当作风格包

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** 返回六个风格包，各风格的 `examples/` 及其子目录不出现在清单中

#### Scenario: 示例改动不使作品准备失效

- **WHEN** 修改某个风格示例的文件
- **THEN** 使用该风格的作品准备指纹不变，只有该示例自身的准备需要重做

#### Scenario: 示例可校验

- **WHEN** 对 `styles/<style-id>/examples/<slug>/` 下的示例运行 `m2v validate`
- **THEN** 校验通过；`vibe-night/fold`、`vibe-fable/pigeon` 与 `dark-proof/sample` 的屏幕字幕在字幕安全区内、无旁白且引用存在的场景入口，其余示例按其风格声明的旁白与文字模式通过校验

### Requirement: 风格示例还原度验收

`styles/vibe-fable/examples/<slug>/` 下的每个风格示例 SHALL 按[参考风格契约](../../../.agents/skills/material2video/references/reference-style.md)记录八项指标，作为**证据格式**而非通过阈值：

- SHALL 产出 `outputs/style-reference.md`，逐项列出参考值、实际值与差值；八项指标准确对应契约定义的主体尺度、空场率、线宽、光源、背景质感、机位与运动、剪辑节奏、文字；
- SHALL 提供与参考样片的并排基准图，参考侧取自已登记样片的采样帧，本片侧取同叙事位置的成片帧；
- SHALL 由独立子代理执行冷审（按[独立子代理评审](../../../.agents/skills/material2video/references/subagent-review.md)隔离投喂），冷审结论 MUST 回应「是否同一部片的视觉系统」，并逐条列出差异项与风险；
- `m2v lookdev` 的代表帧 SHALL 覆盖每一幕，且 `lookdev.json` 与接触表 MUST 出自同一次运行。

本 Requirement SHALL NOT 规定数值下限或上限，也 SHALL NOT 要求冷审结论为「同族」；缺任一项材料视为未完成，齐全即视为过程完备。参考样片与采样帧只可作并排基准，MUST NOT 进入成片、评审包以外的地方或风格包资产。

#### Scenario: 材料齐全

- **WHEN** 风格示例产出 `style-reference.md`、并排基准图、独立冷审记录，且 `lookdev` 覆盖每幕
- **THEN** 该示例的还原度验收视为过程完备，无论冷审结论为何

#### Scenario: 缺少冷审

- **WHEN** 示例只有八项指标与并排图，没有独立子代理冷审记录
- **THEN** 还原度验收未完成，不以作者解释或指标齐全替代独立观察

#### Scenario: 代表帧与清单不同源

- **WHEN** `lookdev.json` 记录的帧与接触表所用帧不是同一次运行产生
- **THEN** 证据不可复算，还原度验收未完成，须重跑 lookdev

#### Scenario: 不把示例当交付作品

- **WHEN** 示例通过还原度验收
- **THEN** 它仍只是风格示例，不因此获得核心样片、粗片或终审记录，也不改变其非交付作品的状态

### Requirement: pigeon 示例使用全局行为轨迹与声音语义表

`styles/vibe-fable/examples/pigeon/` SHALL 用一条不依赖幕 ID 的全局时间状态轨迹驱动鸽子的位置、朝向、啄食、步态与转圈；每一幕 SHALL 只决定镜头取景与字幕，MUST NOT 用幕 ID 分支改变同一时刻的行为。示例 SHALL 通过 `content.props.capture.timebase: "global"` 获取全片时间，MUST NOT 在每幕重复手写 `clock.startSeconds`。

示例 SHALL 在作品内提供可核对的 `SOUND.md`，登记计时、食槽打开/接合、食物到达、转圈与揭示各自的 `assetId`、参数与听觉作用；`storyboard.json` 的音效 SHALL 引用语义 `eventId`，MUST NOT 用与画面脱钩的硬编码 `offsetFrames` 作为主要定位。

#### Scenario: 幕界连续

- **WHEN** 在相邻两幕的边界前后取帧
- **THEN** 鸽子位置、朝向与啄食姿态来自同一 `act(globalSeconds)`，不因换幕跳到另一套动作

#### Scenario: 声音语义可核对

- **WHEN** 检查 `SOUND.md`、`storyboard.json` 的 `events`/`effects` 与 `outputs/events.json`
- **THEN** 每个声音角色都有登记的 `assetId` 与对应 `eventId`，事件帧与音效起点一致

#### Scenario: 未声明全局时间

- **WHEN** 示例幕缺少 `capture.timebase: "global"`
- **THEN** 校验或准备明确失败，不允许回退到手写起点而静默产生跳变

### Requirement: 寓言示例使用有依据的尺度并可练习修改
pigeon 示例 SHALL 移除无事实依据的本能强度读数，保留有来源的喂食周期；SHALL 提供事件调时与相机取景的可复现练习，注明修改位置、预期变化、验证命令和恢复方式。调时练习 SHALL 保持已声明的实验事实，不把改变实验周期作为纯技术修改。

#### Scenario: 移动一次转圈事件
- **WHEN** 按练习调整非事实约束的转圈起点并重新准备
- **THEN** 对应动作和引用该事件的音效共同移动，喂食仍在第 15 秒与第 30 秒发生，未引用事件的字幕被明确列为单独检查项

#### Scenario: 调整机位
- **WHEN** 按练习改变一段取景
- **THEN** 角色和计时器保持同一全局状态，练习要求核对前后衔接与可读性，而非只核对代码运行
