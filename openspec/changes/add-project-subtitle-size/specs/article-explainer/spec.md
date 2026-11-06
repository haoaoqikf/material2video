## ADDED Requirements

### Requirement: 作品级共享字幕字号

general 作品 MAY 在 `project.json.output.subtitle` 声明且仅声明 `fontSize`，系统 MUST 只接受 24 至 56 的整数，MUST 拒绝空对象、未知子字段、布尔、非整数、null 与范围外值。其他视频类型声明 `output.subtitle`（包括 null）MUST 明确拒绝。未声明时 MUST 严格沿用所选画幅清单的完整默认字幕样式，不改变其他作品的字号、安全区、颜色或行高。

准备阶段 MUST 将解析后的唯一完整字幕样式同时写入 `prepared.props.subtitle` 与序列化的 `inputs.subtitle`；预演、正式合成、布局量测和字幕 QA MUST 消费该准备样式。浏览器量测 MUST 校验字幕层实际字号和安全区，并沿用溢出与遮挡判定。改变作品字号 MUST 使旧准备与候选失效，要求重新 prepare，MUST NOT 手工改写旧准备结果。

#### Scenario: 未设置时保持默认
- **WHEN** 横屏或竖屏 general 作品省略 `output.subtitle`
- **THEN** 准备样式与对应画幅清单完全相同，当前两画幅均为 40px

#### Scenario: 设置作品字号
- **WHEN** general 作品声明 `output.subtitle: {"fontSize": 52}` 并重新准备
- **THEN** props 和 inputs 中的字号均为 52，预演与正式合成按 52px 绘制，布局量测和 QA 使用同一准备样式，其他样式维持画幅清单值

#### Scenario: 非法声明
- **WHEN** 字幕配置含未知子字段、缺少 fontSize，字号为布尔、非整数或超出 24 至 56，或非 general 类型声明该字段
- **THEN** 项目加载与适用直接准备校验在生成前失败，并定位 `output.subtitle` 或其子字段

#### Scenario: 字号改变后旧准备失效
- **WHEN** 已准备作品改变、添加或移除 `output.subtitle.fontSize`
- **THEN** 旧准备被拒绝，必须重新准备并生成当前候选

#### Scenario: 实际字号与准备不符
- **WHEN** 共享字幕 DOM 的计算字号与 `prepared.props.subtitle.fontSize` 不同
- **THEN** 字幕量测拒绝预演及正式生成，并报告字号不符
