## Why

文章与主题的 v6 混合媒体讲解已覆盖当前通用创作需求。并存的 general-plan 编排与 article-narrative 类型增加了入口和契约歧义，现用讲解能力统一替换通用类型。

## What Changes

- **BREAKING**：article-narrative 类型改为 general，中文名称为“通用”；辅助命令改为 m2v general。
- **BREAKING**：删除旧 general-plan 编排、完整片段嵌入和作品 React 代码场景能力，不提供兼容入口或迁移工具。
- 保留 v6 storyboard 的完整制作链路，类型列表只保留金融、住宅、通用。
- 删除用户确认的旧本地通用作品，将原文章作品移入 videos/general，保留材料并使旧验收依据失效。

## Capabilities

### Modified Capabilities
- `general-video-composition`：以 v6 多幕讲解替换旧编排契约。
- `code-driven-scenes`：移除作品代码场景契约。
- `modular-video-production`：统一类型身份与辅助命令。

- `article-explainer`、`article-media-assets`、`article-workspace`、`video-production-workflow`：更新通用身份、命令与独立讲解边界。
- `assistant-voice-selection`、`remotion-renderer`：删除嵌入选音及代码场景渲染契约。

## Impact

影响 CLI、类型实现、渲染构建、固定示例、测试与当前制作文档。历史 OpenSpec 归档保持不变；作品和媒体不纳入 Git。
