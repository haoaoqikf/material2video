## Why

`vibe-night-style`、`vibe-fable-style` 与 `dark-proof-style` 的规格重复维护色板取值、分区、字号和组件清单；同样的值也在各自 `styles/<id>/GUIDE.md` 与 `tokens.json` 中存在。三处各自维护会漂移，且规格无法判断哪一处是参数权威。

## What Changes

- 三个风格规格只保留语义、确定性与可验证不变量；具体色值、分区、字号和组件参数引用 `styles/<id>/GUIDE.md` 与 `tokens.json`。
- `vibe-night` 的「色板与版式参数」「可复用组件」改为引用 GUIDE/tokens，保留颜色语义、只读 tokens、确定性与不自动换肤要求。
- `vibe-fable` 的「色板、场景配色与版式参数」「可复用组件」同样处理。
- `dark-proof` 的「色板语义与字阶」「可复用组件」同样处理；运动语法的阈值仍保留在规格中，因为它们是可测试条件。
- `doc-archive`、`count-ledger`、`deep-journey` 的规格已以示例行为为主，本次不改。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `vibe-night-style`: 色板/版式与组件参数改为 GUIDE/tokens 引用。
- `vibe-fable-style`: 色板/场景配色与组件参数改为 GUIDE/tokens 引用。
- `dark-proof-style`: 色板/字阶与组件参数改为 GUIDE/tokens 引用。

## Impact

- 受影响规格：`openspec/specs/vibe-night-style/spec.md`、`vibe-fable-style/spec.md`、`dark-proof-style/spec.md`。
- 受影响文档：三个 `styles/<id>/GUIDE.md` 作为参数与用法的唯一来源，不需要复制规格内容。
- 行为不变：颜色语义、确定性、组件边界与示例验收条件保持。
- 不涉及代码、命令、材料或渲染。
