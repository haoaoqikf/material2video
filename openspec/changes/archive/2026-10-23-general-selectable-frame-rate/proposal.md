## Why
通用讲解的慢速运动无需始终付出60帧采集成本。默认30帧并保留显式60帧，使作者按内容选择且保持已有作品速度。
## What Changes
- general默认30 fps，允许整数30/60；金融和住宅保持60。
- 统一解析作品与分镜声明，按实际帧率贯通准备、录制、缓存、声音、预演和验收。
- 保留现有显式60帧作品与三个示例，不新增迁移或渲染覆盖参数。
## Capabilities
### New Capabilities
无。
### Modified Capabilities
- `video-frame-rate`：按类型默认值和作品声明选择帧率。
- `article-explainer`：通用分镜校验及秒数预算按实际帧率。
- `react-code-scenes`：按作品帧率录制并隔离缓存。
- `video-production-workflow`：通用制作默认30 fps。
- `reference-media-acquisition`：编排输出按作品fps计算，保留60帧分析。
## Impact
影响共享配置、作品加载、通用时间轴和录制、前端默认元数据、制作契约与测试。不改金融住宅业务或作品内容。并行修改基线存于系统临时目录；提交仅包含本任务差量。
