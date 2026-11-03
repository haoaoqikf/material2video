## 1. 规格增量

- [x] 1.1 `vibe-night-style`：色板/版式与组件参数改为 GUIDE/tokens 引用，保留语义与场景。
- [x] 1.2 `vibe-fable-style`：场景配色与组件参数改为 GUIDE/tokens 引用，保留语义与场景。
- [x] 1.3 `dark-proof-style`：色板/字阶与组件参数改为 GUIDE/tokens 引用，保留运动阈值与场景。

## 2. 验证

- [x] 2.1 `openspec validate dedupe-style-spec-parameters --strict` 通过。
- [x] 2.2 归档后 `openspec validate --specs --strict` 通过。
- [x] 2.3 `uv run m2v styles --json` 返回六个包，版本与指纹不变。
- [x] 2.4 `uv run pytest -q` 默认层通过。

## 3. 归档与提交

- [x] 3.1 同步主规格并归档变更。
- [x] 3.2 检查暂存内容，只包含本变更的规格与归档材料，提交 Git。
