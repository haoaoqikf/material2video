## 1. 目录与项目标识

- [x] 1.1 用 `git mv` 将 `examples/five-life-choices` 更名为 `examples/compound-interest`，保留文件历史。
- [x] 1.2 将 `project.json` 的项目 ID 改为 `compound-interest`，并把 `videos/examples/five-life-choices` 迁移为 `videos/examples/compound-interest`。
- [x] 1.3 更新固定示例名单、根 README、示例文档、Skill 参考、测试与 OpenSpec 主规格中的旧名称；归档变更不改写。

## 2. 重新绑定与验证

- [x] 2.1 按新项目 ID 执行 `fetch`、`validate`、`prepare`、`render` 与 `qa`，确认30秒/900帧、画幅、响度与同步仍通过。
- [x] 2.2 复核新成片与旧版画面一致，记录新 SHA-256、preparedFingerprint 与输出路径；更新 VERIFICATION。
- [x] 2.3 运行示例专属测试、严格示例集合、文档链接与前端全量测试，确认另外两个示例未回归。
- [x] 2.4 检查暂存内容仅含本次改名与配套文档，提交并记录 commit。
- [ ] 2.5 按归档流程同步主规格、移入 `openspec/changes/archive/` 并提交归档结果。
