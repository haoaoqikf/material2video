## Context

字体与动效能力各自被拆成多份规格，但共享同一条运行时链路和验证方式。合并后一个能力一个 Purpose，读者不需要在相邻规格之间跳转。

## 决策

1. **原样合并**：所有 Requirement、Scenario 与阈值保持原文，只在新能力中按来源顺序排列。
2. **新 Purpose**：`font-pipeline` 与 `shared-motion` 各写一段 Purpose，说明范围与不变量，不留 TBD。
3. **删除旧能力**：使用 `retire_capabilities: true`，归档时删除五份旧主规格；旧名称不再作为当前权威。
4. **不改变代码**：字体恢复脚本、`m2v/code-scene` 导出与组件行为不变。

## 风险与边界

- 合并后规格较长，但减少了跨规格跳转与重复 Purpose；这是有意的权衡。
- 旧能力名称会从 `openspec/specs/` 消失；归档变更保留完整迁移记录。
- 不处理动效原语与组件内部的重复要求；它们在合并后仍可后续细化。

## 验证

1. `openspec validate merge-font-and-motion-specs --strict` 通过。
2. 归档后 `openspec validate --specs --strict` 通过。
3. `grep` 确认旧能力不再出现在 `openspec/specs/`。
4. `uv run pytest -q` 默认层通过。
