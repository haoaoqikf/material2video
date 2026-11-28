## MODIFIED Requirements

### Requirement: 新版创作辅助命令

系统 MUST 提供 `m2v author` 的输入审查、候选稿及媒体操作，以及 `m2v data financial-plan` 的金融计划编排。系统 MUST 拒绝 `m2v author sounds`、`m2v general`、`m2v financial`、`m2v styles`、`m2v migrate` 和 `m2v relocate`。

#### Scenario: 旧命令
- **WHEN** 运行任一已移除命令
- **THEN** 参数解析失败，且不修改作品。
