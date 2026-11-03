## 1. 规格合并

- [x] 1.1 新建 `font-pipeline`，合并三份字体规格的 8 条要求。
- [x] 1.2 新建 `shared-motion`，合并两份动效规格的 15 条要求。
- [x] 1.3 为两个新能力编写 Purpose。
- [x] 1.4 为五份旧能力写 REMOVED Requirements 与迁移说明。

## 2. 验证

- [x] 2.1 `openspec validate merge-font-and-motion-specs --strict` 通过。
- [x] 2.2 归档后 `openspec validate --specs --strict` 通过。
- [x] 2.3 `grep` 确认旧能力不再出现在 `openspec/specs/`。
- [x] 2.4 `uv run pytest -q` 默认层通过。

## 3. 归档与提交

- [x] 3.1 同步主规格并归档变更。
- [x] 3.2 检查暂存内容，只包含本变更的规格与归档材料，提交 Git。
