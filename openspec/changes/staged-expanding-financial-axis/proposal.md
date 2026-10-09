## Why

固定完整年份横轴使长跨度视频的早期曲线挤在左侧，难以观察早期价格变化。分阶段扩展横轴可以先展示早期走势，再逐步容纳历史，同时保留完整终幕。

## What Changes

- 横轴左边界固定，右边界按自动生成的约六个年度阶段平滑扩展，历史点持续保留。
- 扩展使用 15 帧 smoothstep，与曲线、网格、刻度共享日期映射；终幕四秒保持完整范围。
- **BREAKING**：动画计划升级 v6，dateScale 使用 staged-expanding；旧 v5 必须通过 migrate-line 显式备份迁移，旧评审失效。
- 更新完整预演评审、校验、制作参考文档及相关测试。不增加事件、K 线或播放暂停。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`：分阶段横轴、v6 材料契约、显式迁移与预演验收。

## Impact

涉及 Python 金融计划生成、校验、迁移与评审，React 金融 composition、README 与 Skill 参考文档。保持价格 v3、请求 v1、现有纵轴和三段日期时间轴，不增加依赖。真实作品与媒体不入库，三个既有示例集合不变。
