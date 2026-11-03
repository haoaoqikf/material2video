## Why

当前 `openspec/specs/` 中同一个制作契约存在多个权威：`general-video-composition` 与 `article-explainer` 同时定义 general，前者已无文档引用且仍写着初始化 60 fps；`modular-video-production` 与 `article-workspace` 各有一份逐作品路径迁移要求；六个随附示例名单也在两个规格中重复。另有若干 Purpose 与场景残留旧事实（TBD、两种示例、三种类型、v4 分镜、旧迁移范围）。这会让人和助手无法判断哪份规格是当前真源。

## What Changes

- 将 `general-video-composition` 中仍独有的“统一制作契约”“无声音声明作品交付零音频流”“运动载体优先”三条要求迁入 `article-explainer`，其余 general 行为由 `article-explainer` 现有 v8 要求覆盖；随后移除该能力，避免 general 出现第二份权威。
- 删除 `modular-video-production` 中与 `article-workspace` 重复的“逐作品路径迁移”要求，路径迁移只由 `article-workspace` 维护；`relocate` 命令仍保留在统一入口要求中。
- 从 `vibe-fable-style` 的示例要求中删除与 `article-explainer` 重复的六示例名单，只保留风格包自身的示例声明、旁白/文字模式与指纹隔离要求。
- 修正现行规格中的过期事实：`vibe-fable-style` Purpose 的“两个示例”、`single-pass-delivery` Purpose 的“三种视频类型”、`shared-motion-components` 的 TBD Purpose、`modular-video-production` 的 v4 分镜与旧迁移范围、`us-top10-market-cap-silent-video` 的“三个固定示例集合”。
- 在 `subagent-review.md` 明确：当前门禁只把 `isolation=independent-subagent` 计为独立评审；“外部评审”可使用同一评审包，但不能提供独立子代理调用证据时按未独立处理并披露。行为与代码一致，只消除文档歧义。
- 本变更不改变任何命令、材料、渲染、审核人数或门禁行为，只收敛规格权威与文档事实。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `article-explainer`: 接收 general 的统一制作契约、零音频流与运动载体优先要求，成为 general 唯一权威规格。
- `general-video-composition`: 移除全部要求并归档该能力，行为由 `article-explainer` 承接。
- `modular-video-production`: 删除重复的逐作品路径迁移要求；修正初始化与显式迁移场景中的 v4 旧事实。
- `vibe-fable-style`: 删除重复的六示例名单，只保留风格包自身的示例隔离与声明要求。
- `us-top10-market-cap-silent-video`: 把“三个固定示例集合”更新为当前风格示例集合口径。

## Impact

- 受影响文档：`openspec/specs/article-explainer/spec.md`、`openspec/specs/general-video-composition/spec.md`、`openspec/specs/modular-video-production/spec.md`、`openspec/specs/vibe-fable-style/spec.md`、`openspec/specs/us-top10-market-cap-silent-video/spec.md`、`.agents/skills/material2video/references/subagent-review.md`。
- 不涉及代码、命令、材料格式、渲染契约或示例媒体；`relocate`、`migrate` 与审核门禁行为保持不变。
- 归档时删除 `openspec/specs/general-video-composition/`，并把迁移后的要求写入 `article-explainer` 主规格。
