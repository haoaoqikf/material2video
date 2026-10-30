## Why

用户明确要求彻底移除住宅时间序列视频类型及已有作品，减少当前产品和制作文档的维护范围。

## What Changes

- **BREAKING**：移除 `housing-timeseries` 注册、材料模板、Python 生命周期和前端 composition；旧类型不再接受初始化、校验、准备、预演、渲染和评审，不提供兼容层。
- 删除住宅专用测试和制作指南，更新共享测试、目录投影、制作导航及当前能力文档。
- 删除本地 `videos/housing-timeseries/` 全部作品与产物，确认绝对路径后执行，不影响其他作品。
- 退役住宅主规格，清理其他主规格中的住宅适用范围；已有归档记录保留为历史。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `housing-timeseries`：移除全部年度住房材料和动画要求，退役该能力。
- `modular-video-production`：正式类型仅保留金融和通用，明确拒绝已移除类型。
- `video-frame-rate`：固定 60 fps 专用范围仅保留金融。
- `video-production-workflow`：清除住宅适用范围，金融与 general 的流程不变。
- `keynote-design-system`：共享令牌的专用类型范围仅保留金融。
- `financial-timeseries-video`：共享完整候选场景不再列出住宅。
- `stage-guidance-routing`：制作导航不再包含住宅。

## Impact

影响 `src/m2v/`、`web/src/`、`tests/`、README、ARCHITECTURE、项目规划、制作 Skill 及 OpenSpec 当前规格。保留仍被金融使用的共享无声类型与渲染管线；删除住宅退出后无调用的专用辅助代码。无新增依赖，不重写历史归档，作品内容不加入 Git。
