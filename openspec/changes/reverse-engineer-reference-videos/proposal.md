## Why

现有[参考风格契约](../../../.agents/skills/material2video/references/reference-style.md)只解决「外观如何对齐」：用 L1/L2/L3 分层和八项指标把参考做成可量的目标。它不回答更前面的问题——这条视频为什么让人愿意继续看、哪些导演能力可以被迁移。用户提供一条或多条「效果很好」的参考并要求学习时，当前流程容易退化成内容摘要、形容词评价或表面临摹。

需要把逆向拆解固化为可执行的分析契约：先解释观看驱动力与视觉事件，再把结论提炼成带判据的可迁移规则，最后落到本片场景与检查点；外观量测仍由现有风格契约承担。

## What Changes

- 新增 Skill 参考文档 `reference-video-analysis.md`：规定触发条件、证据类型、时间轴拆解、视觉事件筛选、导演设计、视觉语法、母题、声音（仅有声）、表面风格与底层机制分栏、可迁移规则、反推模板、多参考共同规律、本片落点与自检。
- 明确拆解与风格契约的分工：拆解回答「为什么有效、迁移什么」，风格契约回答「外观像不像」；两者可叠加，不能互相替代。
- 接入现有触发点：`SKILL.md`、`reference-style.md`、`creative-production.md`、`visual-creative-direction.md`、`visual-impact-design.md`、`subagent-review.md`。
- 增加边界：静帧不得推断运动与节奏；无音频证据不得虚构声音；评分只用于同一参考内的投入排序，不是验收门禁；参考素材、分镜与符号不进入成片与盲审包。
- 不新增 CLI 命令、运行时字段、分镜 JSON 字段、制作阶段或自动审美阈值。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `reference-style-transfer`：把能力范围从「风格转译」扩展为「参考学习与风格转译」。新增逆向拆解、可迁移规则落点、多参考共同规律与表面/机制分栏三项要求；现有风格契约、风格基准与素材边界保持不变。

## Impact

影响 `.agents/skills/material2video/` 下的触发说明与参考文档、`tests/test_doc_examples.py` 的入口可达性检查，以及 `openspec/specs/reference-style-transfer/spec.md` 的主规格同步。不修改制作代码、校验器、示例材料或渲染链路；`examples/` 与 `videos/` 不因本变更重制。
