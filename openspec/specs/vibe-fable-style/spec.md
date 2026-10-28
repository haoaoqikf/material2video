# B 寓言风格包 Specification

## Purpose

把已登记参考项目的 B 寓言外观转成仓库内可安装、可验证的风格包，使通用作品能复用同一套扁平插画舞台、三层视差、本能读数仪表、对照计数与规则卡，而不是每次手工复刻；同时以两个可校验的风格示例证明风格包能落到成片上。风格包只提供表现层，不改变视频类型、制作门或验收条件。

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

`tokens.json` SHALL 提供暖白文字 `#FFFAEB`、规则句金 `#EEC672`、「超常」红 `#FC593F`、卡片纸 `#D4CABA` 与深棕卡片字 `#3A2A22`；SHALL 提供五个场景配色（海滩、荒漠、书桌、芦苇荡、夜空），各含天空双色渐变、地面色与点缀色。颜色语义 SHALL 全片一致，红色只表达「超常」。版式 SHALL 提供本能读数仪表的 `45, 35, 345×205` 位置与尺寸、场景说明、顶部结论行与对照计数的纵向位置。字幕安全区 SHALL 只由场景上下文 `subtitleSafeArea` 提供，tokens SHALL NOT 复制一份几何。

#### Scenario: 场景读取配色

- **WHEN** 场景导入 `m2v/style` 的 `tokens` 并请求已登记的场景名
- **THEN** 得到该场景的天空、地面与点缀色；请求未登记的场景名时组件明确抛错，不静默回退

### Requirement: 可复用组件

风格包 SHALL 提供舞台、三层视差、本能读数仪表、场景说明、顶部结论行、对照计数、引线标注、规则卡、片名卡与屏幕字幕组件。组件 SHALL 使用受控帧号与固定种子，SHALL NOT 使用挂钟、`Math.random`、CSS 动画或组件计时器。组件 SHALL NOT 自动修改作品画面，必须由作品显式导入。角色画法 SHALL 由作品自行实现，包内 SHALL NOT 提供通用角色组件。

#### Scenario: 确定性绘制

- **WHEN** 同一作品帧被两次独立录制
- **THEN** 同一帧画面一致，不因运行时刻或随机数变化

#### Scenario: 未显式导入

- **WHEN** 作品声明了风格但场景没有导入任何组件
- **THEN** 画面与未选择风格时相同，不发生自动换肤

### Requirement: 风格示例必须可校验并与包分离

仓库 SHALL 在保留目录 `styles/examples/<style-id>/<slug>/` 提供两个风格示例：`vibe-night/fold` 与 `vibe-fable/pigeon`。示例 SHALL 声明其演示的 `style.id`、使用无旁白屏幕字幕并通过 v8 契约校验；SHALL NOT 占用 `examples/` 的固定名额或改变其集合。风格发现 SHALL 跳过保留目录，SHALL NOT 把示例目录当作风格包。

#### Scenario: 示例不被当作风格包

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** 只返回 `vibe-fable` 与 `vibe-night`，`styles/examples/` 及其子目录不出现在清单中

#### Scenario: 示例改动不使作品准备失效

- **WHEN** 修改某个风格示例的文件
- **THEN** 使用该风格的作品准备指纹不变，只有该示例自身的准备需要重做

#### Scenario: 示例可校验

- **WHEN** 对 `styles/examples/vibe-night/fold` 或 `styles/examples/vibe-fable/pigeon` 运行 `m2v validate`
- **THEN** 校验通过；示例的屏幕字幕都在字幕安全区内、无旁白且引用存在的场景入口
