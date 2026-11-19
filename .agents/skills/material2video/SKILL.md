---
name: material2video
description: 使用统一 m2v 研究、试制、设计、制作与验收五类视频。
---

# Material2Video 制作调度

以实际视觉效果、表达清晰度和完整作品体验判断进展。遵守[项目约定](../../../AGENTS.md)与[架构边界](../../../ARCHITECTURE.md)，事实、来源、许可及用户硬约束保持可追溯。

## 先定位任务

读取 project.json 确认类型与内容根。新作或实质性视听重设计进入[研究与创意试制](references/stage-research.md)，沿全片案例与组件调研及代表场景试制建立实际视觉方向。

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
| 研究与创意试制 | [研究与试制](references/stage-research.md) | 全片案例调研、全片组件选型、代表场景试制与对照 |
| 正式设计 | [完整设计与预演](references/stage-design.md) | 逐场落实已验证方案，按实现缺口补查组件 |
| 制作与验收 | [制作迭代与验收交付](references/stage-production.md) | 实现品质，验证整片并交付 |

新作从[研究与试制](references/stage-research.md)开始；修订先读[修订入口](references/video-revision.md)，复用有效研究和基线。按[具体标杆与拆解](references/reference-video-analysis.md)转化当前内容，比较同场景设计后集中打磨。先看图片按[原生样品](references/design-samples.md)交付通过的同源静帧、参考和覆盖范围。

## 评审与完成

按[审核策略](references/review-contract.md)执行关键帧、适用关键样片的独立评审与总代理整片证据复核。按[视觉复核](references/visual-review-rubric.md#世界级品质与风格开放)区分试制艺术方向与正式成片完成度，每项和整体明确通过或不通过。总代理按实际抽帧、时间轴和适用信号初筛、核对覆盖与选案。研究到交付均不要求播放视频观看或实际试听。

固定保留 RESEARCH.md、DESIGN.md 及每个 design/scenes/<scene-id>.md。总设计先定全片骨架，逐场按[四问模板](references/scene-design.md#场景模板)深化对象、节拍和光影。记录归属见[文档分工](references/scene-design.md#分工与对应)。

[逐场制作循环](references/scene-design.md#渐进设计与开发循环)统一片段粗排、关键过程、精修与接续检查。[原生样品](references/design-samples.md)支持静态和动态采集。[工具协议](references/review-protocol.md)说明字段与命令，[隔离方法](references/subagent-review.md)说明独立执行。

## 条件阅读

五类作品有自身旁白且需要选音时，按[配音指南](references/voice-and-rhythm.md#口播作品的固定默认音色)登记默认的「真人播客女」。

口播配实拍或外部素材归 `documentary-edit`。按[视觉素材选择](references/visual-material-selection.md#观点旁白与意境素材)逐段排镜，按[采用与署名](references/material-sourcing.md#5-采用政策与署名)处理「资料画面」和证据标识。

[阅读路由](references/guidance-routes.json)维护触发条件与唯一权威。素材检索读[素材台账](references/material-sourcing.md)，运动实现读[运行契约](references/code-scene-runtime.md#运动实现约定)。改材料后重新 prepare，修复先按帧/信号核对局部效果再汇总全片。命令以[README](../../../README.md)和实际帮助为准。
