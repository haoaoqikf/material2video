## 1. 规格增量

- [x] 1.1 在 `article-explainer` 主规格加入统一制作契约、零音频流与运动载体优先三条要求。
- [x] 1.2 归档 `general-video-composition`，确认 v8 自由代码场景要求已由 `article-explainer` 覆盖。
- [x] 1.3 从 `modular-video-production` 删除重复的逐作品路径迁移要求，并修正 v4 旧事实。
- [x] 1.4 精简 `vibe-fable-style` 的示例要求，六示例名单只由 `article-explainer` 维护。
- [x] 1.5 修正 `us-top10-market-cap-silent-video` 的固定示例集合口径。

## 2. 主规格与参考文档

- [x] 2.1 修正 `vibe-fable-style` Purpose：每个正式风格配一个规范示例。
- [x] 2.2 修正 `single-pass-delivery` Purpose：覆盖所有正式视频类型。
- [x] 2.3 补写 `shared-motion-components` Purpose，移除 TBD。
- [x] 2.4 在 `subagent-review.md` 明确只有 `isolation=independent-subagent` 计为独立评审，外部评审按未独立处理并披露。

## 3. 验证

- [x] 3.1 `openspec validate consolidate-duplicated-spec-authorities --strict` 通过。
- [x] 3.2 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` 通过。
- [x] 3.3 相对链接与锚点检查通过；`grep` 确认没有文档再把 `general-video-composition` 当作现行权威。
- [x] 3.4 `uv run pytest` 默认层通过。

## 4. 归档与提交

- [x] 4.1 同步主规格并归档变更到 `openspec/changes/archive/`。
- [x] 4.2 检查暂存内容，只包含本变更的规格、文档与归档材料，提交 Git。
