## Why

`video-production-workflow` 目前有 85 条要求、约 1791 行，同时定义制作过程、门、评审、状态、单次生成和讲解机制。对应的能力规格已经存在，但同一行为仍由两份规格描述，维护者难以判断哪份是权威。本次先把 12 条归属明确的要求迁入对应能力规格，制作流程只保留过程、记录与回退。

## What Changes

- 将状态查询要求迁入 `production-status-ledger`。
- 将场景门/粗片缓存复用与单次完整生成要求迁入 `single-pass-delivery`。
- 将三阶段门、动态核心过程证据、动态采样要求迁入 `checkpoint-based-visual-acceptance`。
- 将审查执行覆盖证据、全片导演审查独立性、视觉复核证据绑定要求迁入 `independent-subagent-review`。
- 将讲解片对象/事件编排与完整可见过程要求迁入 `explainer-mechanism-review`。
- 将制作指导权威分层要求迁入 `stage-guidance-routing`。
- `video-production-workflow` 删除上述 12 条要求，保留其余制作过程、设计、返工与交付要求。
- 本次只迁移归属明确、目标规格已有对应能力的要求；其余要求保留在制作流程，后续按同一方式分批迁移。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `video-production-workflow`: 移除 12 条已归属其他能力的要求。
- `production-status-ledger`: 新增作品入口、准备、预演与可选评审状态查询要求。
- `single-pass-delivery`: 新增场景门/粗片缓存复用与单次完整生成边界要求。
- `checkpoint-based-visual-acceptance`: 新增三阶段门映射、动态核心过程证据与采样连续性要求。
- `independent-subagent-review`: 新增审查覆盖证据、全片导演审查独立性与视觉复核证据绑定要求。
- `explainer-mechanism-review`: 新增讲解片对象/事件共同编排与完整可见过程要求。
- `stage-guidance-routing`: 新增制作指导权威分层要求。

## Impact

- 受影响规格：`openspec/specs/video-production-workflow/spec.md` 与上述六个能力规格。
- 行为不变：要求文本原样迁移，仅修正 `文章类型/文章作品` 为 `general`。
- 不涉及代码、命令、材料、渲染或审核人数。
- 归档后 `video-production-workflow` 仍保留其余制作过程要求；迁移清单作为后续拆分的基线。
