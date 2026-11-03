## Context

`video-production-workflow` 的 85 条要求中，部分与 `production-status-ledger`、`single-pass-delivery`、`checkpoint-based-visual-acceptance`、`independent-subagent-review`、`explainer-mechanism-review`、`stage-guidance-routing` 描述同一行为。目标规格已经存在，但文本经过改写，无法用逐字去重判断；本次按“归属明确且目标规格已有对应能力”筛选 12 条迁移。

## 迁移清单

| 来源要求 | 目标能力 |
|---|---|
| 制作状态必须可查询 | `production-status-ledger` |
| 场景门与粗片必须复用片段缓存 | `single-pass-delivery` |
| 单次完整生成必须明确合成与返工边界 | `single-pass-delivery` |
| 三阶段必须接入检查点门 | `checkpoint-based-visual-acceptance` |
| 动态核心事件必须具备足够的过程证据 | `checkpoint-based-visual-acceptance` |
| 动态事件必须核对采样连续性与文字竞争 | `checkpoint-based-visual-acceptance` |
| 审查执行必须具有真实阶段与全片覆盖证据 | `independent-subagent-review` |
| 全片导演审查必须独立于逐场实现与技术验收 | `independent-subagent-review` |
| 自主视觉复核证据绑定 | `independent-subagent-review` |
| 讲解片必须共同编排对象与可见事件 | `explainer-mechanism-review` |
| 讲解片必须验证完整可见过程 | `explainer-mechanism-review` |
| 制作指导必须按权威分层组织 | `stage-guidance-routing` |

## 决策

1. **原样迁移**：要求正文与场景保持原文，只把 `文章类型/文章作品` 改成 `general`，避免迁移时改变行为。
2. **不合并相近要求**：目标规格已有相近要求时，新增要求保留来源的独有细节，不删目标正文；后续若发现重复，再单独合并。
3. **只迁第一组**：其余 73 条继续留在 `video-production-workflow`。本次不建立空的“已拆分”假象，避免为了数量拆散仍在制作流程中耦合的要求。
4. **归档后检查**：确认删除的要求在目标规格中存在同名要求，且没有其他文档引用旧位置。

## 风险与边界

- 迁移是文本搬移，不改命令、材料、渲染或审核人数。
- 目标规格新增要求后可能出现相近条款；这是可接受的中间状态，优先保证行为不丢失。
- 不处理 `visual-creative-direction` 等 reference 文档与规格的重复；那属于文档层，已在其他批次处理。

## 验证

1. `openspec validate split-production-workflow-spec --strict` 通过。
2. 归档后 `openspec validate --specs --strict` 通过。
3. 目标规格均包含迁移后的同名要求，`video-production-workflow` 不再包含它们。
4. `uv run pytest -q` 默认层通过。
5. 链接/锚点检查通过。
