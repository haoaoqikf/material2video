# 全片设计：luck-on-stage

## 当前流程与历史证据范围

研究固定见[RESEARCH.md](RESEARCH.md)，每个正式场景文档继续保留；日常记录可用目标、画面与注意力、实现、验证与未知四问，复杂机制沿原详细编排深化。成熟方案优先采用或改造。

本文保留原制作版本的设计和评审记录。新版交付按[现行审核策略](../../../.agents/skills/material2video/references/review-contract.md)执行正式关键帧、适用关键样片、技术 QA 与总代理整片复核，旧结论仅覆盖原版。


## 目标、约束与选案依据

以尝试次数与单次成功概率解释机会，并区分期望与实际结果。具体原始要求、选案和历史限制保留在[分层前原记录](design/previous-design.md)，不能将作者转化扩大或缩小为新授权。当前类型、画幅、帧率和精确时间以[project](project.json)及[分镜](storyboard.json)为准。

## 当前硬约束与共同规则

原要求：全片统一用“尝试”，结尾唯一指定句为“多尝试，提高成功概率”，不增加解释文字。表达必须分清尝试次数N和单次概率p是两个独立改进方向；E(S)=Np为期望，重复尝试不自动提高p，也不保证实际命中。红色示意未中，金色示意命中/成功区域/结果；球只在尝试、记录、三柱追踪。七场、41秒以当前分镜为准，历史45秒表不作为执行时点。

## 五维共同语言与贯穿对象

近黑、米白主体、金色结果、红色未中。开场/记录/三柱使用球的弧线与接触，桥段/概率盘/面积/结尾由文字和图形自己承担动作；不再每场强加球。声音随现有命名事件，光不盖必要信息。

## 结构、节奏与有效范围

场序和执行时间由分镜维护；各场详细编排如下。当前依据整理自既有设计及实现，本轮没有补造研究、重新制作或授予独立通过。历史材料只支持其原范围；新修订按[场景设计指南](../../../.agents/skills/material2video/references/scene-design.md)补足实际目标与证据。[来源](SOURCES.md)；[原验证记录](VERIFICATION.md)；

## 场景索引

| scene.id | 叙事作用 | 场景设计 |
|---|---|---|
| hook | 运气、期望值、尝试次数、成功概率 | [hook](design/scenes/hook.md) |
| ledger | 运气、期望值、尝试次数、成功概率 | [ledger](design/scenes/ledger.md) |
| bridge | 运气、期望值、尝试次数、成功概率 | [bridge](design/scenes/bridge.md) |
| probability | 运气、期望值、尝试次数、成功概率 | [probability](design/scenes/probability.md) |
| bars | 运气、期望值、尝试次数、成功概率 | [bars](design/scenes/bars.md) |
| area | 运气、期望值、尝试次数、成功概率 | [area](design/scenes/area.md) |
| closing | 运气、期望值、尝试次数、成功概率 | [closing](design/scenes/closing.md) |
