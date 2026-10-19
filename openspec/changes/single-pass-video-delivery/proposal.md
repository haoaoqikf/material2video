## Why
完整预演与正式导出使用相同规格重复编码，检查样片入口也隐式导出全篇，浪费制作时间。

## What Changes
- **BREAKING** 取消完整预演门禁，preview 只允许严格短于全片的时间窗口，默认前十秒。
- 三类型共享候选成片、验收与交付状态；有效完整文件复用，验收重试不重渲染。
- general 准备只编译时间轴，场景按检查或正式生成需求录制。
- 可选评审绑定候选摘要，检查与交付不再依赖旧预演记录。

## Capabilities
### New Capabilities
- `single-pass-delivery`: 一次全片生成、可重试验收、片段检查及候选版本绑定。
### Modified Capabilities
- `modular-video-production`: 更新统一入口、准备绑定及可靠交付规则。
- `article-explainer`: 更新讲解评审绑定及按需录制规则。
- `financial-timeseries-video`: 取消金融完整预演门禁并保留自动探针。
- `housing-timeseries`: 住宅一次全片生成及候选验收。
- `general-video-composition`: 通用准备只编译时间轴，检查与正式生成按需录制。

## Impact
统一 CLI、三种类型渲染器、general 录制/lookdev/QA、状态与清理、测试与制作文档。不增加依赖。
