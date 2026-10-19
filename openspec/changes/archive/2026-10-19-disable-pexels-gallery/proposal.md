## Why
当前仅 Pixabay 配置了凭据，默认 Pexels 导致素材检索失败。固定关闭 Pexels，避免助手选错来源。

## What Changes
- **BREAKING**：通用素材搜索仅启用 Pixabay，并作为默认来源；显式 Pexels 请求提示停用。
- 配置 Pexels 密钥不会重新启用；公开媒体直链导入保持可用。
- 同步帮助、制作指导与回归测试。

## Capabilities
### New Capabilities
无。
### Modified Capabilities
- `article-media-assets`：图库入口固定使用 Pixabay。

## Impact
通用素材搜索入口、相关测试和文档；不修改密钥、媒体导入与渲染契约。
