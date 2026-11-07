---
name: material2video
description: 使用统一 m2v 制作入口创作或修订五类视频。用于准备类型材料、编排、局部修改、预演、评审、渲染与排查不一致问题。
---

# Material2Video 制作调度

## 全程底线

遵循用户目标与[项目约定](../../../AGENTS.md)、[OpenSpec 工作流](../../../AGENTS.md#openspec-工作流)和[架构边界](../../../ARCHITECTURE.md)，事实、来源和许可可追溯；不把未来能力、技术通过、候选交付或自审写成独立制作通过。只处理当前范围，作品与媒体不入库。
制作采用现有合同、审核轮次与失败闭环；[检查点契约](references/checkpoint-gates.md)是风险、人数、证据和完成条件的唯一依据，适用专项必须展开。

## 先定位任务

读取作品 `project.json` 确认类型；新作品先确定类型与内容根。先定位任务与阶段，再读取下一份主指南；不递归读完所有链接。

视频创作或视觉表达修订前必须完整阅读[视频视觉与表达参考](references/visual-expression-inspiration.md)，同一任务已完整阅读则不重复。阅读后采用自选，可以不用其中风格、自创或搜索其他风格；不要求选择理由或不采用说明。

<!-- generated:type-catalog:start -->
| 类型 | 创作指导 |
|---|---|
| `text-motion` | [制作流程](references/production-workflow.md#阶段阅读入口)：统一分镜制作与验收。 |
| `data-evolution` | [制作流程](references/production-workflow.md#阶段阅读入口)：统一分镜制作与验收。 |
| `principle-metaphor` | [制作流程](references/production-workflow.md#阶段阅读入口)：统一分镜制作与验收。 |
| `spatial-3d` | [制作流程](references/production-workflow.md#阶段阅读入口)：统一分镜制作与验收。 |
| `documentary-edit` | [制作流程](references/production-workflow.md#阶段阅读入口)：统一分镜制作与验收。 |
<!-- generated:type-catalog:end -->

- **新制作**：从[方案确定](references/stage-plan.md)开始。
- **修订**：先读[修订入口](references/video-revision.md)，定位影响阶段、保留基线，再进入对应阶段；不重开无关选案。
- **评审**：完整试制固定在扩展前进入[制作与迭代](references/stage-iterate.md)评审；G5 全片粗片为内部检查，试制检查是否值得继续，终审检查整片是否兑现；当前候选独立终审进入[最终验收](references/stage-final.md)。再读适用隔离要求；新上下文只收评审包。
- **排查**：先读[制作与迭代](references/stage-iterate.md)，只展开相关技术契约；不要用排错代替制作复核。

## 当前阶段重点

| 阶段 | 下一份主指南 | 首要问题 |
|---|---|---|
| 方案确定 | [方案](references/stage-plan.md) | 让谁理解什么，靠什么对象与机制 |
| 制作与迭代 | [制作与迭代](references/stage-iterate.md) | 核心关系成立了吗，问题是否复查关闭 |
| 最终验收 | [验收](references/stage-final.md) | 当前候选证据齐全、问题关闭了吗 |

创作从主题与用户目标出发，自主选择文字、图形、素材、静止或运动。必要设计记录见[方案指南](references/stage-plan.md#设计记录)，技术 QA 不替代实际表达判断。

## 条件参考

[阅读路由](references/guidance-routes.json)登记所有任务、阶段、条件参考与权威归属。首次采用技术、出现风险或使用外部参考时，读取相应专项。灵感文档按上方要求必读，其中风格与讲解方法采用自选；强制技术和验收要求不因阅读顺序而降低。
选择素材先读[按用途排序来源](references/visual-material-selection.md#按用途排序素材来源)；当前代理支持生图时，定制插画、海报等静态任务优先考虑 AI 图片，真实证据与准确机制分别优先原件和代码。检索、生成、评估或整理素材时读[素材检索与台账](references/material-sourcing.md)：生成记录、候选评估卡、许可判断与台账工具按该页执行；导入契约仍以既有参考页为准。
运动方法见[运动设计](../motion-design/SKILL.md)及[视频适配](../motion-design/ADAPTATION.md)，创作建议按需选用，帧驱动与采集模式边界仍须遵守。实际表达与问题处理按既有复核契约，不以风格或方法符合性验收。
修改材料后重新 prepare；按[返工循环](references/production-workflow.md#检查与返工循环)先实际查看局部修复效果，汇总后再生成下一全片候选。preview 只检查局部，不替代最终全片复核。命令与能力见[README](../../../README.md)，不凭旧提示猜参数。
