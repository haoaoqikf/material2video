---
name: material2video
description: 使用统一 m2v 研究、试制、设计、制作与验收五类视频。
---

# Material2Video 制作调度

以实际视觉效果、表达清晰度和完整作品体验判断进展。遵守[项目约定](../../../AGENTS.md)与[架构边界](../../../ARCHITECTURE.md)，事实、来源、许可及用户硬约束保持可追溯。

## 先定位任务

读取 project.json 确认类型与内容根。创作或实质性视听修订前完整阅读[创作总纲与灵感](references/visual-expression-inspiration.md)，已读不重读。风格自由，以所选方向的世界级完成度为目标；优先复用、采用和改造成熟方案，只自研必要缺口。

<!-- generated:type-catalog:start -->
| 类型 | 创作指导 |
|---|---|
| `text-motion` | [制作流程](references/production-workflow.md)：研究、设计、制作与验收。 |
| `data-evolution` | [制作流程](references/production-workflow.md)：研究、设计、制作与验收。 |
| `principle-metaphor` | [制作流程](references/production-workflow.md)：研究、设计、制作与验收。 |
| `spatial-3d` | [制作流程](references/production-workflow.md)：研究、设计、制作与验收。 |
| `documentary-edit` | [制作流程](references/production-workflow.md)：研究、设计、制作与验收。 |
<!-- generated:type-catalog:end -->

## 三阶段

| 阶段 | 主指南 | 重点 |
|---|---|---|
| 研究与创意试制 | [研究与试制](references/stage-research.md) | 深入研究具体标杆，转化、试制并对照目标 |
| 正式设计 | [完整设计与预演](references/stage-design.md) | 将有效创意组织成完整作品 |
| 制作与验收 | [制作迭代与验收交付](references/stage-production.md) | 实现品质，验证整片并交付 |

新作从[研究与试制](references/stage-research.md)开始；修订先读[修订入口](references/video-revision.md)，复用有效研究和基线。按[具体标杆与拆解](references/reference-video-analysis.md)转化当前内容，比较同场景设计后集中打磨。先看图片按[原生样品](references/design-samples.md)交付通过的同源静帧、参考和覆盖范围。

## 评审与完成

按[审核策略](references/review-contract.md)：关键帧独立盲审及同轮实际参考对照，关键片段默认独立过程对照、取消例行盲审，当前完整候选由新代理终审。观察按[世界级标准](references/visual-review-rubric.md#世界级品质与风格开放)，每项和整体明确通过或不通过，证据不足不可采用。总代理实际查看、初筛、检查报告充分性并负责选案和当前版本交付。技术通过或自审不替代独立通过。

固定保留 RESEARCH.md、DESIGN.md 及每个 design/scenes/<scene-id>.md；[场景默认四问](references/scene-design.md#场景模板)，复杂机制按需深化。问题唯一归 outputs/visual-notes.md，参数留在分镜／代码，原报告只引用。阶段由助手判断，工具不自动认证审美。

[原生样品](references/design-samples.md)支持纯静态不编码视频；适用动态另验完整过程。60 秒及以下不另出试制片段，关键帧来自全片工程且审核不免。预演、粗片、精制使用同一问题驱动循环；有效来源和证据按影响复用。机器字段按需读[工具协议](references/review-protocol.md)，执行读[隔离方法](references/subagent-review.md)。

## 条件阅读

营销号口播、知识解说、人物故事等按[营销号口播剪辑指南](references/documentary-social-video.md)制作。口播配实拍或外部素材归 `documentary-edit`。开工先查[默认音色](references/documentary-social-video.md#7-配音字幕与声音)与[资料画面标注](references/documentary-social-video.md#真实来源与采用边界)，再登记音色、编写分镜及画面文字。

[阅读路由](references/guidance-routes.json)维护触发条件与唯一权威。素材检索读[素材台账](references/material-sourcing.md)，运动实现读[运行契约](references/code-scene-runtime.md#运动实现约定)。改材料后重新 prepare，修复先按帧/信号核对局部效果再汇总全片。命令以[README](../../../README.md)和实际帮助为准。
