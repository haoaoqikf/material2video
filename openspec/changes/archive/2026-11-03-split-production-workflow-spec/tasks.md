## 1. 规格增量

- [x] 1.1 在 `production-status-ledger` 加入作品入口、准备、预演与可选评审状态查询要求。
- [x] 1.2 在 `single-pass-delivery` 加入场景门/粗片缓存复用与单次完整生成边界要求。
- [x] 1.3 在 `checkpoint-based-visual-acceptance` 加入三阶段门、动态核心过程证据与采样连续性要求。
- [x] 1.4 在 `independent-subagent-review` 加入审查覆盖、全片导演审查独立性与视觉复核证据绑定要求。
- [x] 1.5 在 `explainer-mechanism-review` 加入对象/事件共同编排与完整可见过程要求。
- [x] 1.6 在 `stage-guidance-routing` 加入制作指导权威分层要求。
- [x] 1.7 从 `video-production-workflow` 删除上述 12 条要求。

## 2. 验证

- [x] 2.1 `openspec validate split-production-workflow-spec --strict` 通过。
- [x] 2.2 归档后 `openspec validate --specs --strict` 通过。
- [x] 2.3 目标规格均存在迁移后的同名要求，制作流程不再包含它们。
- [x] 2.4 `uv run pytest -q` 默认层通过。
- [x] 2.5 相对链接与锚点检查通过。

## 3. 归档与提交

- [x] 3.1 同步主规格并归档变更。
- [x] 3.2 检查暂存内容，只包含本变更的规格与归档材料，提交 Git。
