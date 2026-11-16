## Why

现有试制把静帧与完整过程绑定为一套双评，纯静态设计仍强制编码视频，且评审编排与制作记录存在重复成本。需要把世界级美术判断前移到关键帧，按实际机制验证过程，并保留研究、总设计和每个正式场景的完整责任链。

## What Changes

- 关键帧采用世界级、风格开放的独立盲审及同轮目标对照；采用结论明确为通过或不通过，证据不足不得放行。
- 强化总代理实际查看、送审筛选、报告充分性检查、选案与当前版本交付责任，不新增作者审批文档。
- **BREAKING** 媒体评审升级为 v3，显式区分关键帧、过程与终审用途；过程默认独立目标对照，无例行盲审，核心创意依赖时间展开时可说明依据后盲审。
- **BREAKING** 原生样品升级为 v2，支持纯静态采集，不编码视频；动态样品分别验证关键帧与完整过程，删除旧的静帧加过程一套双评契约，不提供兼容层或迁移。
- 自动生成请求、隔离包任务及结构化报告模板，自动派生同轮对照；真实观察与调用仍由独立代理完成，工具不伪造评审或判断审美。
- 固定保留 RESEARCH.md、DESIGN.md 和每个正式场景文档；默认四问，十二方面按机制深化，执行参数与原始证据各保留单一来源。
- 成熟外部方案优先采用、组合与改造；预演、粗片、精制使用同一问题驱动循环。60 秒及以下不另制试制片段，但关键帧及全片独立验收不降低。
- 压缩日常手册，评审政策、隔离协议与工具格式分层维护；同步五部示例与相关验证。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `media-bound-production-review`: v3 用途、过程审核、明确采用结论及自动编排。
- `native-design-samples`: v2 静态采集和分离的关键帧／过程交付证据。
- `independent-subagent-review`: 关键帧高标准独立观察、过程对照与总代理责任。
- `video-production-workflow`: 成熟方案优先、统一制作循环及短片关键帧验证。
- `scene-design-documents`: 固定分层文档、四问默认模板及按机制深化。
- `production-status-ledger`: 关键帧与过程证据分开投影，当前完整候选终审仍独立有效。
- `stage-guidance-routing`: 精简主线与按需技术协议阅读。
- `modular-video-production`: 同步评审 v3 的总模块版本要求。
- `compound-interest-explainer-video`: 示例关键帧双评及过程对照按当前审核职责执行。
- `solar-system-journey-video`: 示例交付证据采用分开的关键帧与过程职责。

## Impact

涉及 src/m2v/production、engine/design_sample.py、独立工程模板本地采集、CLI、相关 Python／浏览器测试、五部示例设计材料、README、ARCHITECTURE、AGENTS 及 material2video 指南。保留既有安全路径、来源摘要、隔离、失败闭环及终审资格边界；不改变视频类型、正式分镜或渲染画面契约，不新增运行时依赖，不对作品内容目录批量迁移。
