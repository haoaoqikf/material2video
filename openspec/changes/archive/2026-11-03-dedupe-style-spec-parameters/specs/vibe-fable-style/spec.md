## MODIFIED Requirements

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
