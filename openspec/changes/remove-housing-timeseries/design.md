## Context

住宅类型分别在 Python 注册与目录、Remotion composition、制作路由和文档中登记，并与金融共享无声生命周期及渲染管线。移除动机与边界见 proposal.md。

## Goals / Non-Goals

**Goals:** 从可发现入口和执行路径中彻底移除住宅，清理现行契约，同时保持金融和 general 的现有行为。

**Non-Goals:** 不添加地图视频能力，不重构保留类型，不提供旧住宅材料兼容、迁移或回退层，不改写已归档历史。

## Decisions

- 从 catalog 和行为注册两端移除住宅，并删除专用 Python 模块与 TSX 画面，而非隐藏列表项；由统一注册表的未知类型错误拒绝旧请求。
- 保留金融仍使用的 SilentTypeSpec、SilentRenderSpec 及共享渲染管线；删除住宅退出后无引用的正数校验函数和进度选项，避免遗留死分支。
- 用目录同步脚本重建类型清单；手工更新现行文档、制作路由和跨类型测试。共享测试改用保留的金融类型，继续覆盖原有通用能力。
- 主规格以完整 MODIFIED requirement 保留原场景，住宅独立规格用 REMOVED requirements 退役。历史 archive 不变，防止改写既往实现记录。
- 删除本地作品前，以 PowerShell Resolve-Path 核对目标恰为当前仓库 videos/housing-timeseries 且位于 videos 内；原生 Remove-Item 删除整个目录，不触及其他类型。

## Risks / Trade-offs

- [误删共享代码] → 引用检索、金融与 general 回归、前端构建及独立代码审查。
- [旧作品仍能执行] → 测试初始化及旧清单生命周期均明确拒绝，不产生输出。
- [当前文档残留失效链接] → 导航校验、目录投影检查和全局住宅引用检查。
- [本地作品不可从 Git 恢复] → 用户已明确授权全部删除；验证绝对目标，删除后核对目录不存在。

## Migration Plan

先完成契约和任务记录，再删除专用实现与作品，同步文档并验证。实现提交后同步主规格并归档，单独提交归档结果；代码可用 Git 回退，已忽略作品的删除不提供恢复。
