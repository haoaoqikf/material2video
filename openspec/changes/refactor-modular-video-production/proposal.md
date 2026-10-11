## Why

文章规则与制作底座混合，金融另有打包与导出链路，新增专用视频会重复实现制作流程。以金融为优先方向，通过独立类型与统一制作底座支持更多专用视频，并建设可组合的通用视频。

## What Changes

- Python 迁入标准 src/a2v 包，分离 core、engine、types 和 cli；前端按类型分层。
- 新增版本化 project.json、PreparedVideo、类型注册、指纹绑定的准备及评审记录。
- **BREAKING**：统一 uv run a2v 入口，删除旧制作脚本入口，提供备份后显式迁移。
- 完整保留金融时间序列和文章 v4 能力及类型门禁。
- 新增 general 类型，组合受控图文、完整金融/文章片段和受约束的 React 代码场景；支持口播字幕、硬切、交叉淡化。
- 统一缓存、单浏览器渲染会话、原子输出、溯源和性能记录。

## Capabilities

### New Capabilities
- `modular-video-production`：作品契约、类型注册、统一命令、准备与评审版本绑定、显式迁移。
- `general-video-composition`：多场景时间轴、嵌入类型、代码场景、声音字幕与转场。

### Modified Capabilities
- `financial-timeseries-video`：通过统一入口制作，复用共享渲染底座。
- `video-production-workflow`：文章入口迁移至统一命令，保留既有门禁。

## Impact

影响 Python 实现与测试导入、前端 composition 注册及场景 API、构建脚本、三个固定示例、Skill 制作契约和核心文档。作品和媒体仍不入库；无行情/模型服务、云端队列、自动发布或第三方插件系统。
