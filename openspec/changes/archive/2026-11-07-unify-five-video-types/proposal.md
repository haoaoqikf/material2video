## Why

现有 `general`、三个专项类型和六个风格包把画面来源、作品身份与表现样式混在不同层次，初始化、制作与示例因此存在多套契约。将视频按主要画面来源归为五类，使作者只选择视频类型，仍能使用已有金融、建筑、汽车和代码场景能力。

## What Changes

- **BREAKING** 仅保留 `text-motion`、`data-evolution`、`principle-metaphor`、`spatial-3d`、`documentary-edit` 五个视频类型；移除类别层、旧类型名和旧路径迁移入口。
- **BREAKING** 作品升级到 `project.json` v2 与统一 `storyboard.json` v9；五类共用代码场景准备、预演、渲染和制作证据链，旧材料与准备记录明确拒绝。
- 金融数据与投资计算、建筑步骤、汽车模型镜头成为新版分镜可引用的专用数据源及共享场景能力；不再作为视频类型。
- **BREAKING** 删除风格包、风格选择与 `m2v/style`，可复用组件进入共享 SDK；七个示例迁至 `examples/<type>/<slug>/` 且保持可运行。
- **BREAKING** `m2v general` 改为 `m2v author`，`m2v financial plan` 改为 `m2v data financial-plan`，删除 `m2v styles` 和旧格式迁移命令。

## Capabilities

### New Capabilities

- `five-video-types`: 五类身份、统一材料和旧版本拒绝。
- `typed-scene-sources`: 金融、建筑、汽车等结构化输入进入同一分镜与场景运行时。

### Modified Capabilities

- `modular-video-production`: 统一作品入口、规范路径、准备与交付。
- `react-code-scenes`: 统一场景 SDK、来源注入与作品边界。
- `article-explainer`: 分镜 v9 与五类共享的讲解能力。
- `example-media-recovery`: 独立示例目录与七例可恢复、可运行。
- `style-registry`: 删除风格层的全部要求。

## Impact

影响 Python 类型目录、作品契约、CLI、准备与渲染，Web composition 与代码场景打包器，七个示例、字体目标、测试、OpenSpec 主规格和制作文档。现有 v1/v8 作品需要按新契约重新编排；不提供自动迁移。
