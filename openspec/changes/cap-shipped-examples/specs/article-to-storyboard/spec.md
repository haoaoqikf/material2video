## ADDED Requirements

### Requirement: 固定仓库示例集合
仓库 SHALL 仅分发 `buffer-smoothing`、`darts-trial-and-error` 与 `keynote-baseline` 三个示例。`examples/` 中的示例目录数量 MUST 不超过三个，维护者 SHALL 仅修改该固定集合，不得新增、删除或替换示例。

#### Scenario: 检查分发示例
- **WHEN** 仓库检查示例目录
- **THEN** 目录集合恰为上述三个 slug，且每个示例分镜通过严格校验

#### Scenario: 新增或替换示例
- **WHEN** 提交加入第四个示例、移除固定示例或以其他目录替换
- **THEN** 自动化检查失败
