## Purpose

把《复利》的可数物证与状态机外观转成仓库内可安装、可验证的风格包，使通用作品能复用同一套近黑底、米白/金/暗金三态语义、可数圆片、世界坐标相机与数字排版，而不是每次手工复刻；同时保留原作品的数学口径与逐场编排作为该风格的规范示例。

## ADDED Requirements

### Requirement: 可数物证风格包可用

仓库 SHALL 提供 `styles/count-ledger/`，清单 SHALL 声明 `types: ["general"]`、`frames: [{"width":1920,"height":1080}]` 与 `requires.narration = "none"`，并提供非空 `GUIDE.md` 与 `tokens.json`。作品通过 `project.json` 的 `style.id: "count-ledger"` 选择后，`m2v validate` 与 `m2v prepare` SHALL 记录其 id、version 与内容指纹；包内容变化 SHALL 使旧准备失效。包 SHALL NOT 登记 `assets`，SHALL 使用宿主已注册字体。

#### Scenario: 选择风格并准备

- **WHEN** 一个无旁白的 general 横屏作品声明 `style.id: "count-ledger"` 并执行 `prepare`
- **THEN** 准备产物记录风格身份与指纹，`m2v status` 显示所选风格与准备有效性

#### Scenario: 不兼容选择

- **WHEN** 非 general 作品、竖屏作品、有旁白作品或未知风格 id 选择该包
- **THEN** 校验明确失败并指出类型、画幅或旁白不匹配，不回退到无风格

### Requirement: 色板、状态语义与数字版式

`tokens.json` SHALL 提供近黑底、米白资本、金色新生成、暗金已离开与次要文字色，并说明颜色只表达项目定义的状态而非固定材质。SHALL 提供数字排版阶、等宽数字规则、圆片直径/间距基准与相机缩放基准。字幕安全区 SHALL 只由场景上下文 `subtitleSafeArea` 提供，tokens SHALL NOT 复制一份几何。风格包 SHALL NOT 硬编码金额、年份、收益率或分段时长。

#### Scenario: 场景读取参数

- **WHEN** 场景导入 `m2v/style` 的 `tokens`
- **THEN** 可用 tokens 取得颜色、数字字号与圆片基准，且对象只读

#### Scenario: 状态色语义一致

- **WHEN** 同一圆片从“新生成”变为“已并入”或“已离开”
- **THEN** 画面使用 tokens 对应的三种状态色，不自行发明第四种状态色

### Requirement: 可复用组件

风格包 SHALL 提供圆片、圆片行/列/网格布局、状态混色、数值文字、世界坐标相机插值与投影辅助等组件。组件 SHALL 使用受控帧号与固定种子，SHALL NOT 使用挂钟、`Math.random`、CSS 动画或组件计时器。组件 SHALL NOT 自动修改作品画面，必须由作品显式导入。组件 SHALL 只接收数量、位置、状态、进度与文字等 props，SHALL NOT 内置复利模型、年份读数、取出组/丘的题材坐标或事件音时序。

#### Scenario: 确定性绘制

- **WHEN** 同一作品帧被两次独立录制
- **THEN** 同一帧画面一致，不因运行时刻或随机数变化

#### Scenario: 包内无题材数据

- **WHEN** 检查 `styles/count-ledger/` 的源码与 tokens
- **THEN** 不出现复利本金/收益率/30 年模型、S1–S6 段时间、取出组/丘坐标或 25 个事件音映射

### Requirement: 风格示例作品（视频专属，不属于包）

仓库 SHALL 在 `styles/examples/count-ledger/compound-interest/` 提供规范示例，声明 `style.id: "count-ledger"`。该作品 SHALL 保持 29 秒/870 帧、30 fps、无旁白、8 秒进入的无旋律环境床与同步事件音、1 枚圆片=1,000 元的资金状态机、收益再投入与累计总额比较；详细行为引用既有 `compound-interest-explainer-video`，本规格不复制其数学细节。示例 SHALL 通过 v8 校验与 `prepare`，生成媒体 SHALL NOT 入库。复利数学、分镜、圆片坐标与声音配方属于作品，SHALL NOT 进入风格包。

#### Scenario: 示例可校验

- **WHEN** 对 `styles/examples/count-ledger/compound-interest/` 运行 `m2v validate` 与 `prepare`
- **THEN** 校验通过，实际时长 29 秒、870 帧、30 fps、无旁白，事件音与画面事件对应

#### Scenario: 示例不被当作风格包

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** `styles/examples/count-ledger/compound-interest` 不出现在风格清单中，也不能按风格 id 加载
