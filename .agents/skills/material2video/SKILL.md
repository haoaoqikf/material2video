---
name: material2video
description: 使用统一 m2v 制作入口创作或修订金融时间序列、通用讲解视频。用于准备类型材料、编排、局部修改、预演、评审、渲染与排查不一致问题。
---

# Material2Video 制作调度

## 全程底线

遵循用户目标与[项目约定](../../../AGENTS.md)、[OpenSpec 工作流](../../../AGENTS.md#openspec-工作流)和[架构边界](../../../ARCHITECTURE.md)，事实、来源和许可可追溯；不把未来能力、技术通过、候选交付或自审写成独立制作通过。只处理当前范围，作品与媒体不入库。
制作采用现有合同、审核轮次与失败闭环；[检查点契约](references/checkpoint-gates.md)是风险、人数、证据和完成条件的唯一依据，适用专项必须展开。

## 先定位任务

读取作品 `project.json` 确认类型；新作品先确定类型与内容根。先定位任务与阶段，再读取下一份主指南；不递归读完所有链接。

| 类型 | 创作指导 |
|---|---|
<!-- generated:type-catalog:start -->
| `financial-timeseries` | [金融时间序列视频](references/financial-timeseries-video.md)：核验行情口径、投资计算并通过完整候选自动验收。 |
| `general` | [制作流程](references/production-workflow.md#阶段阅读入口)：三阶段流程与[视觉导演指南](references/visual-creative-direction.md)。 |
<!-- generated:type-catalog:end -->

- **新制作 general**：从[方案确定](references/stage-plan.md)开始。
- **修订**：先读[修订入口](references/video-revision.md)，定位影响阶段、保留基线，再进入对应阶段；不重开无关选案。
- **评审**：核心风险按计划在扩展前进入[制作与迭代](references/stage-iterate.md)评审；G5 全片粗片为内部检查，低风险作品不派独立评审；当前候选独立终审进入[最终验收](references/stage-final.md)。再读适用隔离要求；新上下文只收评审包。
- **排查**：先读[制作与迭代](references/stage-iterate.md)，只展开相关技术契约；不要用排错代替制作复核。

## 当前阶段重点

| 阶段 | 下一份主指南 | 首要问题 |
|---|---|---|
| 方案确定 | [方案](references/stage-plan.md) | 让谁理解什么，靠什么对象与机制 |
| 制作与迭代 | [制作与迭代](references/stage-iterate.md) | 核心关系成立了吗，问题是否复查关闭 |
| 最终验收 | [验收](references/stage-final.md) | 当前候选证据齐全、问题关闭了吗 |

讲解片优先考虑对象追踪、尺度变化、过程结果联动、回场，按需选用；纯文字与合理延迟揭示不机械否决。技术 QA 不替代实际表达判断。

## 条件参考

[阅读路由](references/guidance-routes.json)登记所有任务、阶段、条件参考与权威归属。首次采用技术、出现风险或用户要求参考风格时，必须读取相应专项；优先级只控制阅读顺序，不降低强制规则效力。
修改材料后重新 prepare；按[返工循环](references/production-workflow.md#检查与返工循环)先实际查看局部修复效果，汇总后再生成下一全片候选。preview 只检查局部，不替代最终全片复核。命令与能力见[README](../../../README.md)，不凭旧提示猜参数。
