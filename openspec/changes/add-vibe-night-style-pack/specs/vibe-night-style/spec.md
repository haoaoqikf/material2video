## Purpose

把已登记参考项目的 C 夜曲外观转成仓库内可安装、可验证的风格包，使通用作品能复用同一套色板、版式、组件与字体，而不是每次手工复刻。风格包只提供表现层，不改变视频类型、制作门或验收条件。

## ADDED Requirements

### Requirement: C 夜曲风格包可用

仓库 SHALL 提供 `styles/vibe-night/`，清单 SHALL 声明 `types: ["general"]` 与 `frames: [{"width":1920,"height":1080}]`，并提供非空 `GUIDE.md` 与 `tokens.json`。作品通过 `project.json` 的 `style.id: "vibe-night"` 选择后，`m2v validate` 与 `m2v prepare` SHALL 记录其 id、version 与内容指纹；包内容变化 SHALL 使旧准备失效。

#### Scenario: 选择风格并准备

- **WHEN** 一个 general 横屏作品声明 `style.id: "vibe-night"` 并执行 `prepare`
- **THEN** 准备产物记录风格身份与指纹，`m2v status` 显示所选风格与准备有效性

#### Scenario: 不兼容选择

- **WHEN** 非 general 作品、竖屏作品或未知风格 id 选择该包
- **THEN** 校验明确失败并指出类型或画幅不匹配，不回退到无风格

### Requirement: 色板与版式参数

`tokens.json` SHALL 提供 C 夜曲的底色 `#010104`、中央光池 `#0B1830`、主体字 `#F8F9F8`，以及金、冰蓝、玫红、紫的语义色；SHALL 提供主体区、字幕区与四角常驻区的纵向分区，以及主体字、小标、章节标的字号和字距。颜色语义 SHALL 全片一致，每种颜色只表达一个含义。

#### Scenario: 场景读取参数

- **WHEN** 场景导入 `m2v/style` 的 `tokens`
- **THEN** 可用 tokens 取得上述颜色、分区与字号，且对象只读

### Requirement: 可复用组件

风格包 SHALL 提供星点底、光点、彗尾、辉光文字、章节标、点阵片名卡、闪、暗一下与数轴组件。组件 SHALL 使用受控帧号与固定种子，SHALL NOT 使用挂钟、`Math.random`、CSS 动画或组件计时器；资产与字体就绪前 SHALL NOT 开始绘制，场景 SHALL 在就绪后调用 `ready()`。组件 SHALL NOT 自动修改作品画面，必须由作品显式导入。

#### Scenario: 确定性绘制

- **WHEN** 同一作品帧被两次独立录制
- **THEN** 同一帧画面一致，不因运行时刻或随机数变化

#### Scenario: 未显式导入

- **WHEN** 作品声明了风格但场景没有导入任何组件
- **THEN** 画面与未选择风格时相同，不发生自动换肤

### Requirement: 字体资产与许可

风格包 SHALL 随包提供宋体字体资产（Noto Serif SC 或等价 OFL 字体）与许可全文，并在清单 `assets` 中声明来源与许可。字体 SHALL 通过包内资产 URL 显式加载；常用字 SHALL 在字体字符映射中齐全，缺字 SHALL 视为试制未完成。字体加载 SHALL NOT 改写共享字幕层或全局字体清单。

#### Scenario: 字体缺字

- **WHEN** 画面用字在包内字体中没有字形
- **THEN** 试制验证失败并列出缺字，不以系统回退字体交付

### Requirement: 无旁白屏幕字幕约定

选择该风格的无旁白作品 SHALL 在 `content.props.screenSubtitles` 声明屏幕文字，每项含 `startFrame`、`endFrame` 与非空 `text`；作品 SHALL 在 `subtitleSafeArea` 内单行绘制、不换行、无底板，中文不超过 28 字。有旁白作品 SHALL NOT 读取该字段，继续使用共享字幕层。该约定 SHALL NOT 改变分镜 schema、共享字幕层或字幕自动校验。

#### Scenario: 无旁白作品显示屏幕文字

- **WHEN** 无旁白作品在时段内声明屏幕文字
- **THEN** 画面在字幕安全区内显示单行文字，共享字幕层为空，两者不重叠

#### Scenario: 有旁白作品

- **WHEN** 作品使用 TTS 旁白并声明了 `screenSubtitles`
- **THEN** 屏幕文字不参与渲染，字幕仍由共享层从旁白派生

### Requirement: 原创试制验收

风格包 SHALL 用一条 30–45 秒、不入库的原创作品试制，作品 SHALL 按[参考风格契约](../../.agents/skills/material2video/references/reference-style.md)记录八项指标、并排基准与独立冷审结论。试制 SHALL NOT 复制参考项目的 `engine/`、样片实现、GIF/JPG、角色或文案；样片只可作为并排基准，不进入成片或仓库。

#### Scenario: 验收证据

- **WHEN** 风格包完成试制
- **THEN** 作品 `outputs/style-reference.md` 含八项参考值、目标值、实际值与差值，并排图与冷审记录齐全；缺任一项视为未完成
