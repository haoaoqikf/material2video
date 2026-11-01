## Why

`frontend-design` 与 `motion-design` 已作为项目级知识 skill 接入路由、三阶段和评审词汇，但制品层仍停在接入之前：主规格同时要求"视觉创意七段式"和"五块式设计记录"，视觉复核仍在核对已删除的七段模板，规范示例与全部作品都没有五块式范本，运动计划只有四行文字、没有任何落到镜头的通道。运动又只能靠"事件"触发证据加密，入场、离场与减速落点在 0.5 秒采样下判不出来；五份类型专用指南一次都没有引用两个 skill。继续让助手自己补，等于让新知识停留在文档层。

## What Changes

- **BREAKING（对指导文档）**：移除主规格中的"视觉创意七段式"要求，其仍有效的约束并入五块式要求；视觉复核条目由"七段是否齐全"改为按五块核对可观察兑现。
- 五块式中的**运动计划**补齐落地方式：按 `scene.id` / `shots[].id` 记录入场、离场与画面内运动的起止帧与命名曲线，`linear` 例外就地写用途；逐场表增加运动行为列。不新增分镜字段、CLI 或门禁。
- 一个规范示例补五块式记录与可执行的运动计划范本（一镜到底的 `linear` 例外作为真实案例），保留历史记录与既有交付结论。
- 运动节拍进入既有证据链路：关键运动节点登记为幕内事件，使 `minEventFrames` 与采样密度守卫覆盖运动而不是只覆盖事件；`structure-timing` 的 requiredEvidence 补"关键运动窗口的加密帧或片段"。
- 五份类型专用指南（building-construction、driving-route、financial-timeseries、road-trip、vehicle-showcase）接入两个 skill 的链接，明确类型内的视觉与运动判断以 skill 为权威。

## Capabilities

### New Capabilities
<!-- 无新增能力：本变更只收敛既有权威与证据链路。 -->

### Modified Capabilities
- `video-production-workflow`: 移除七段式要求并扩充五块式设计记录（含运动计划的镜头级映射与 `linear` 例外记录）；新增类型专用指南必须接入项目级视觉与运动知识的要求。
- `checkpoint-based-visual-acceptance`: 新增动态证据必须覆盖关键运动节拍的要求（采样与 `minEventFrames` 依据运动变化，`structure-timing` 要求关键运动窗口证据）。

## Impact

- 主规格：`openspec/specs/video-production-workflow/spec.md`、`openspec/specs/checkpoint-based-visual-acceptance/spec.md`。
- 指导文档：`visual-creative-direction.md`（五块模板、逐场表）、`visual-review-rubric.md`（复核条目）、`stage-plan.md` / `stage-iterate.md` / `stage-final.md`（运动映射与证据）、`checkpoint-gates.md`（生成表文本）、五份类型专用指南。
- 策略源：`src/m2v/production/policy.py` 的 `structure-timing` evidence 文本，经 `sync_docs.py` 重新生成 `checkpoint-gates.md` 生成区。
- 示例：`styles/deep-journey/examples/solar-system-journey/DESIGN.md` 增补五块式记录（属作品内容，不改风格包指纹、不新增生成媒体）。
- 规格行为不变的部分：分镜 JSON 字段、检查点合同、审核人数与轮次、CLI 命令与门禁结果均不改。
