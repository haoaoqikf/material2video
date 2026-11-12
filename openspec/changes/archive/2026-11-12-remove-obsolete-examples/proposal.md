## Why

用户要求彻底删除两部指定示例及其关联代码和文档；现行固定示例集合、测试登记与制作手册仍依赖这两部作品，需要一并清理，避免失效入口和孤立测试。

## What Changes

- **BREAKING** 删除 `examples/principle-metaphor/pigeon` 与 `examples/text-motion/fold` 的完整本地目录，包括源码、材料、依赖、媒体及产物。
- 删除专属布局生成器测试，清理示例登记、文档导航、制作手册及历史材料中的专属内容。
- 固定示例集合收敛为五部，图文动效类型继续支持初始化与制作，但不再附带该类型示例。
- 保留其他作品使用的通用运行时、绘制工具、字体及声音能力。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `standalone-video-projects`：随附示例由七部减少为五部，删除的作品不再属于仓库分发范围。
- `five-video-types`、`example-media-recovery`、`article-workspace`、`video-frame-rate`：同步示例数量与目录要求，保留五类身份、恢复、路径和帧率行为。
- `article-sound-effects`：将已删除作品的专属场景改为中性事件示范，声音能力不变。

## Impact

影响两个示例目录、测试清单与专属测试、核心文档、制作参考、现行规格及关联历史材料；不改变五类视频目录、工程与分镜格式、通用渲染接口，不引入依赖。
