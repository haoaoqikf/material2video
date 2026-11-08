## Why

现有 DESIGN.md 同时承担总设计、逐场概述与制作历史，难以承载对象配合、次级运动、光影和声音的细致编排。五维要求虽已写入流程，设计到实现、实际证据与评审之间仍缺少清楚的逐场对应。

## What Changes

- 五类继续共用三阶段；采用全片 DESIGN.md 与 design/scenes/<scene-id>.md 分层设计，研究、问题和原始报告各归其位。
- 场景文档覆盖十二方面，按镜头/节拍联动五维，支持先假设、试制反馈、再更新有效设计；复杂度决定深度，不要求空表或逐场审批。
- 明确场景身份、分镜、实现、声音事件、跨场出口/入口及证据对应；执行参数保留单一来源。
- **BREAKING（制作指导）**：取消全片 DESIGN.md 中重复的详细逐场表和所有场景必须填写全部指标的要求；指标按实际采用机制选择。调整与此冲突的 cut、静止和角色说明。
- 增加技能脚本级离线结构检查，复用现有 Markdown 路径检查；不新增 m2v 命令、渲染字段或审美算法。
- 七部示例同步场景索引及文档；在当前作品中选代表性场景和相邻衔接实作验证，不重制所有历史作品或补造旧通过。

## Capabilities

### New Capabilities

- `scene-design-documents`: 分层设计职责、逐场对应和轻量结构校验。

### Modified Capabilities

- `video-production-workflow`: 渐进设计、试制反馈与五维对应，替换统一指标门槛。
- `stage-guidance-routing`: 场景设计唯一权威和条件阅读入口。
- `reference-style-transfer`: 研究、总设计、场景转化及参考证据的分工。

- `media-bound-production-review`、`independent-subagent-review`、`single-pass-delivery`: 同步适用指标与场景职责，保持评审策略。

## Impact

影响 material2video Skill、文档校验脚本、相关测试、README/ARCHITECTURE/AGENTS、七部示例和当前作品的设计材料。无新运行时依赖；project v2、storyboard v9、准备指纹、媒体评审格式与审核人数/轮次策略保持。作品内容与生成媒体按忽略规则保存。
