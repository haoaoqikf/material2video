## Why

风格的规范、组件与规范示例分散在两条目录树，查找和维护需要跨目录。将示例归入所属风格，同时保留独立作品的依赖与安全边界，使目录归属与使用方式一致。

## What Changes

- **BREAKING**：五个规范示例统一从 `styles/examples/<style>/<slug>/` 移至 `styles/<style>/examples/<slug>/`，不提供旧路径别名。
- 风格指纹排除直属 `examples/` 整个子树，清单与共享组件不能引用该子树；其余共享文件仍完整参与指纹。
- 构建器区分共享风格代码和嵌套示例作品，保持跨作品、未登记资产与越界导入的拒绝行为。
- 同步当前文档、测试、命令与媒体忽略规则；保留历史归档与历史证据原貌。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `style-registry`：同目录示例、指纹排除及双向导入隔离。
- `article-workspace`、`article-explainer`、`modular-video-production`：规范示例路径更新。
- `count-ledger-style`、`deep-journey-style`、`doc-archive-style`、`vibe-night-style`、`vibe-fable-style`：所属示例路径更新。
- `example-media-recovery`：新位置的媒体恢复与忽略规则。

## Impact

涉及风格加载器、代码场景构建器、命令、固定测试清单、五份示例、Git 忽略与当前文档；不新增视频类型、清单字段或外部依赖，不改变成片视觉内容。旧准备与生成证据不冒充新路径下已验证结果，迁移后重新校验与准备。
