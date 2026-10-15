## Why

文章讲解与素材剪辑入口分离，文章缺少视频镜头和提示音，素材搜索绑定单一图库。需要统一制作入口并允许助手全网获取媒体。

## What Changes

- 新增 v6 分镜，拒绝 v5 及更早版本；支持原文或主题、图片视频混排和最长 600 秒。
- 新增带来源留证的媒体导入、内置提示音及本地音效定位混音。
- 停止新建 stock-montage，删除旧制作链，不提供兼容和迁移。

## Capabilities

### New Capabilities
- `article-media-assets`: 全网搜索助手与本地媒体导入的交接及可核验素材。
- `article-sound-effects`: 可重复的内置音效、定位及混音。

### Modified Capabilities
- `article-explainer`: v6 混合分镜、主题输入、六模板与扩展时长。
- `stock-montage-video`: 移除独立类型及旧制作链。
- `remotion-renderer`: 契约页版本升到 6。
- `video-production-workflow`: 文章类型改为 v6 混合媒体。
- `assistant-voice-selection`: 音色门禁的适用范围随素材剪辑类型删除而收敛。
- `financial-timeseries-video`: 统一入口的评审范围随素材剪辑类型删除而收敛。

## Impact

影响文章契约、时间轴、CLI、React 画面、预演、类型目录、制作指导和测试；复用 ffmpeg 与现有下载设施，不新增服务依赖。
