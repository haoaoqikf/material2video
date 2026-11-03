## MODIFIED Requirements

### Requirement: 色板与版式参数

`tokens.json` SHALL 提供 C 夜曲的色板、纵向分区、字号与字距；具体取值与用法见 `styles/vibe-night/GUIDE.md` 与 `tokens.json`。颜色语义 SHALL 全片一致，每种颜色只表达一个含义。字幕安全区 SHALL 只由场景上下文 `subtitleSafeArea` 提供，tokens SHALL NOT 复制一份几何。

#### Scenario: 场景读取参数

- **WHEN** 场景导入 `m2v/style` 的 `tokens`
- **THEN** 可用 tokens 取得色板、分区与字号，且对象只读

### Requirement: 可复用组件

风格包 SHALL 提供 GUIDE 列出的星点底、光点、彗尾、辉光文字、章节标、点阵片名卡、闪、暗一下与数轴组件；具体参数见 `styles/vibe-night/GUIDE.md`。组件 SHALL 使用受控帧号与固定种子，SHALL NOT 使用挂钟、`Math.random`、CSS 动画或组件计时器；资产与字体就绪前 SHALL NOT 开始绘制，场景 SHALL 在就绪后调用 `ready()`。组件 SHALL NOT 自动修改作品画面，必须由作品显式导入。

#### Scenario: 确定性绘制

- **WHEN** 同一作品帧被两次独立录制
- **THEN** 同一帧画面一致，不因运行时刻或随机数变化

#### Scenario: 未显式导入

- **WHEN** 作品声明了风格但场景没有导入任何组件
- **THEN** 画面与未选择风格时相同，不发生自动换肤
