## 1. 退役

- [x] 1.1 `protein-explainer-video` 的全部要求写入 REMOVED。
- [x] 1.2 `two-dimensional-foil-video` 的全部要求写入 REMOVED。
- [x] 1.3 `early-investing-compound-video` 的全部要求写入 REMOVED。

## 2. 验证

- [x] 2.1 `openspec validate retire-unmaintained-work-specs --strict` 通过。
- [x] 2.2 归档后 `openspec validate --specs --strict` 通过。
- [x] 2.3 `grep` 确认三个能力不再出现在 `openspec/specs/`。
- [x] 2.4 `uv run pytest -q` 默认层通过。

## 3. 归档与提交

- [x] 3.1 同步主规格并归档变更。
- [x] 3.2 检查暂存内容，只包含本变更的规格与归档材料，提交 Git。
