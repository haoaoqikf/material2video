# 文章工作区输出路径

## MODIFIED Requirements

### Requirement: 产物归属作品目录

默认产物 MUST 位于对应作品目录下的 `outputs/` 子目录，而不是工作区根下的独立产物树。

#### Scenario: 正式作品默认输出

- **WHEN** 文章位于 `videos/demo/`
- **THEN** 默认媒体、预览、检查报告、字幕、溯源和成片写入 `videos/demo/outputs/`

#### Scenario: 示例作品默认输出

- **WHEN** 示例文章归属为 `examples/demo/`
- **THEN** 默认产物写入 `videos/examples/demo/outputs/`，并与正式作品隔离

#### Scenario: 外部内容根

- **WHEN** `--content-root` 或 `A2V_CONTENT_ROOT` 指向外部内容根
- **THEN** 使用该内容根下的 `videos/<slug>/outputs/` 同构路径

#### Scenario: 显式输出参数

- **WHEN** 用户传入 `--out` 或 `--out-dir`
- **THEN** 显式路径优先，继续保持原有兼容行为

### Requirement: 迁移保护

迁移已有产物时 MUST NOT 覆盖目标中的同名文件。

#### Scenario: 迁移目标存在冲突

- **WHEN** 目标路径中已有与源文件同名的文件
- **THEN** 迁移停止并报告冲突，不修改冲突文件
