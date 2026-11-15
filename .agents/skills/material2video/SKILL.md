---
name: material2video
description: 使用统一 m2v 研究、试制、设计、制作与验收五类视频。
---

# Material2Video 制作调度

以实际视觉效果、表达清晰度和完整作品体验判断进展。遵守[项目约定](../../../AGENTS.md)与[架构边界](../../../ARCHITECTURE.md)，事实、来源、许可及用户硬约束保持可追溯。

## 先定位任务

读取 project.json 确认类型与内容根。创作或实质性视听修订前完整阅读[创作总纲与灵感](references/visual-expression-inspiration.md)，已读不重读。自选风格与方法，用实际研究、试制与参考对照验证所选视觉目标。

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

原创高难度作品优先向第一阶段投入探索资源。60%/25%/15% 仅为起始实验建议，按关键未知及实现成本调整，机器等待时间单列，不设预算调度器。

新作从研究与试制开始；修订先读[修订入口](references/video-revision.md)，沿有效基线进入受影响活动。有效试制继续完善，不重复制作同用途样片。成片目标时长不超过 60 秒的作品完成研究与拆解后直接制作全片，不单独制作试制样片，完整成片仍须技术 QA 与独立终审，详见[研究与试制](references/stage-research.md)。完整设计前即可评审局部媒体，无需全片机器合同。

按[具体标杆与深入拆解](references/reference-video-analysis.md)研究品质与本片转化，比较同一关键场景的设计后集中打磨，按[研究与试制](references/stage-research.md)判定淘汰、打磨或采用。先看图片时按[网页原生样品](references/design-samples.md)迭代，独立评审及交付检查通过后展示同源静帧、参考和覆盖范围。局部修改复用有效研究。

## 评审与完成

仅保留技术 QA 与[独立视觉评审](references/review-contract.md)。试制与终审使用独立子代理；全片预演和粗片查看是内部制作活动。评审以有序帧、帧差/场景切分、主体区域量测和音频信号量测为证据，不要求播放或试听；技术通过、渲染成功或自审不能替代独立通过。观察与失败闭环见[视觉复核](references/visual-review-rubric.md)和[隔离执行](references/subagent-review.md)。

同轮对照提供实际参考媒体与中性采用特征。缺目标或过程时保持对应项未验证，审美和研究深度由人判断。

研究记于 RESEARCH.md，总设计和索引归 DESIGN.md，详细编排按[场景设计](references/scene-design.md)归 design/scenes/<scene-id>.md，明确关键关系与观察预期，试制后区分计划和实际结果并回写，唯一问题和复查记录放在 outputs/visual-notes.md；只链接原始报告，不复制全文。状态工具只展示证据，阶段由助手依据指南判断。

## 条件阅读

营销号口播、知识解说、人物故事等按[营销号口播剪辑指南](references/documentary-social-video.md)制作。口播配实拍或外部素材归 `documentary-edit`。开工先查[默认音色](references/documentary-social-video.md#7-配音字幕与声音)与[资料画面标注](references/documentary-social-video.md#真实来源与采用边界)，再登记音色、编写分镜及画面文字。

[阅读路由](references/guidance-routes.json)维护触发条件与唯一权威。素材检索读[素材台账](references/material-sourcing.md)，运动实现读[运行契约](references/code-scene-runtime.md#运动实现约定)。改材料后重新 prepare，修复先按帧/信号核对局部效果再汇总全片。命令以[README](../../../README.md)和实际帮助为准。
