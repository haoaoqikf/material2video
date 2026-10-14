## Why

单世界对象动画不适合当前道理讲解制作需求。改用语音同步的模板卡片，降低创作成本并提高信息可读性。

## What Changes

- **BREAKING**：article-narrative 只接受 v5 多幕讲解分镜，拒绝 v1～v4；旧作品重新编排。
- 提供观点、对比、步骤、因果图、图片五种模板，分离旁白与屏幕摘要。
- 复用 TTS 生成实际分段时间；全片含阅读停留与转场不超过 60 秒。
- 替换文章输入与视觉评审契约，保持统一制作入口、指纹绑定和 general 完整嵌入。

## Capabilities

### New Capabilities
- `article-explainer`: v5 材料、模板、时间轴、输入及画面评审和兼容边界。

### Modified Capabilities
- `storyboard-v3-contract`: 文章执行入口改用 v5。
- `single-scene-narrative`: 移除文章单世界要求。
- `article-input-review`: 非空正文与讲解语义审查替代标准字数和单世界审查。
- `video-production-workflow`: 文章使用讲解评审。

## Impact

文章适配器、初始化模板、React composition、契约页、通用嵌入、示例、测试与制作文档。共享旧动画模块仍供内部开发测试使用，不提供文章兼容入口。
