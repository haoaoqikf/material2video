## Why

当前作品和视频产物混放在 `videos/<slug>/`，无法从目录层次快速区分视频类型。统一按类型归档作品与产物，并提供逐作品迁移能力，可让仓库内和外部内容根采用一致、可维护的布局。

## What Changes

- **BREAKING**：作品规范目录改为 `videos/<type>/<slug>/`，作品的 `outputs/` 保持原有内部结构。
- `m2v init` 按类型创建分层目录；作品路径和文章工作流解析支持该结构。
- 增加逐作品目录迁移，完整备份后移动源文件和产物；目标冲突时保留目标文件、报告并保留冲突源文件。
- 更新路径忽略规则、当前能力文档和工作流参考。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `article-workspace`：工作区作品目录增加视频类型层，并定义迁移行为。
- `modular-video-production`：初始化使用类型目录；支持现有统一契约作品的路径迁移。

## Impact

- 影响 `src/m2v/` 中统一 CLI、项目路径解析、文章工作流和作品迁移逻辑。
- 影响 `.gitignore`、README、material2video Skill 路径参考和 OpenSpec 主规格。
- 不新增依赖；已有旧路径内容由用户逐作品调用迁移命令移动。
