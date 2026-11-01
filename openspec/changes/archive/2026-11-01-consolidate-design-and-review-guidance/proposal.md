## Why

两个项目级 skill 已经接入，但项目指导仍把“设计方法”和“项目契约”混写：`visual-creative-direction.md`、`production-workflow.md`、`creative-production.md`、`visual-review-rubric.md` 与 `director-review-and-edit.md` 之间大量重复导演设计、核心事件、观察顺序、问题闭环和演练；`production-examples.md` 还维护第二份七段式模板。结果是制作助手要先读很多重复规则，skill 反而成了附加说明。

用户要求：进一步删减原有流程和文档，把视觉与运动方法更多交给 `frontend-design` 与 `motion-design`，项目文档只保留“何时做、做什么、证据是什么、何时算完成”。

## What Changes

- 删除 `creative-production.md`，把仍属项目独有的信息单元预算、标题与文案、返工升级、分层精修、减法复核、阶段回归与反馈影响并入 `production-workflow.md`；声音部分并入 `voice-and-rhythm.md`。
- 删除 `director-review-and-edit.md`，把 G5/G6、全片逐页检查、剪辑重组、第二次导演审查与传播评估并入 `visual-review-rubric.md`。
- 压缩 `visual-creative-direction.md`：删除重复的七段式模板、十项自检与判断演练；精简“视觉力量设计”中已由 frontend-design 覆盖的通用构图/层级说明；新增一页式 `DESIGN.md` 模板（题材、视觉计划、叙事计划、运动计划、风险计划）。
- 压缩 `production-workflow.md`：删除与 `visual-creative-direction.md` 重复的视觉创意方案、导演设计、核心事件观察、减法与唯一画面、静态目标验证、核心事件短循环，改为链接。
- 压缩 `production-examples.md`：删除第二份七段式模板和十项自检，只保留项目特有的判断演练与排错案例。
- 压缩 `explainer-design.md`：把通用构图、色彩、字体、留白判断明确交给 `frontend-design`，保留项目特有的形象判据、主体尺度、辉光、字幕区与讲解机制。
- 重写三份阶段指南为决策表：方案确定回答“要决定什么”，制作与迭代回答“要验证什么”，最终验收回答“要接受什么”；方法与观察顺序直接指向两个 skill。
- 更新 `guidance-routes.json`、README、ARCHITECTURE、AGENTS、示例 DESIGN.md 链接与相关测试。
- 不改变检查点、审核人数、证据失效、CLI 行为、渲染契约或视频类型。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `video-production-workflow`：制作流程只保留一个权威文档；`DESIGN.md` 采用五块式设计记录；返工、减法、阶段回归并入流程文档。
- `stage-guidance-routing`：入口与阶段指南改为决策表；删除文档的路由必须迁移，不得留下失效链接。
- `explainer-visual-diagnosis`：通用视觉判断委托 `frontend-design`，项目文档只保留讲解特有的形象、尺度、辉光、字幕区诊断。
- `frontend-design`：项目指导不得复述 skill 已覆盖的通用方法；`DESIGN.md` 记录 skill 决策与有意例外。
- `motion-design`：项目指导不得复述 skill 已覆盖的通用运动方法；`DESIGN.md` 记录运动人格、签名动作与时长/缓动起点。

## Impact

- 删除：`references/creative-production.md`、`references/director-review-and-edit.md`。
- 重写：`references/stage-plan.md`、`stage-iterate.md`、`stage-final.md`。
- 压缩：`references/visual-creative-direction.md`、`production-workflow.md`、`production-examples.md`、`explainer-design.md`。
- 合并：`references/visual-review-rubric.md`、`voice-and-rhythm.md`。
- 更新：`guidance-routes.json`、`SKILL.md`、`README.md`、`ARCHITECTURE.md`、`AGENTS.md`、示例 `DESIGN.md` 链接、`tests/common/test_doc_examples.py`、`tests/common/test_guidance_routes.py`、OpenSpec 主规格。
- 不涉及：代码、运行时、CLI、分镜字段、检查点合同、审核人数、门禁数量。
