## Why

字体能力被拆成 `font-assets`、`font-coverage`、`font-subsetting` 三份规格，动效能力被拆成 `scene-motion-primitives` 与 `shared-motion-components` 两份规格。它们共享同一条恢复、确定性与缓存失效链路，分开维护会产生重复的 Purpose、验证和交叉引用。

## What Changes

- 新建 `font-pipeline` 能力，合并三份字体规格的 8 条要求；删除原字体能力。
- 新建 `shared-motion` 能力，合并两份动效规格的 15 条要求；删除原动效能力。
- 新能力的 Purpose 由本次变更提供，不再留 TBD。
- 行为不变：要求正文原样迁移，只合并相邻能力。

## Capabilities

### New Capabilities

- `font-pipeline`: 字体登记、恢复、缺字检查与按作品子集化的统一能力。
- `shared-motion`: 共享动效原语与组件的统一能力。

### Modified Capabilities

无；原能力通过归档删除。

## Impact

- 受影响规格：新增 `font-pipeline`、`shared-motion`；删除 `font-assets`、`font-coverage`、`font-subsetting`、`scene-motion-primitives`、`shared-motion-components`。
- 不涉及代码、命令、字体文件、渲染或示例；`m2v` 与构建行为不变。
