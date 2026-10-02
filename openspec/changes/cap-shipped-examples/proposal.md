## Why

仓库中的示例逐渐增多且职责重叠，维护成本和规范引用面随之扩大。固定三个代表性示例能保留关键制作路径，同时让后续维护范围明确。

## What Changes

- 固定随仓库发布的示例为 `buffer-smoothing`、`darts-trial-and-error`、`keynote-baseline`，删除其他示例。
- 明确 `examples/` 最多三个目录，集合固定，只允许修改这三例。
- 更新测试、制作文档和当前规格中的示例引用。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `article-to-storyboard`：规定仓库分发示例集合及其维护上限。

## Impact

影响 `examples/`、测试夹具、README、项目 Skill、项目规划及 OpenSpec 当前规格；无运行时 API 变化。
