## 1. 拆解契约

- [x] 1.1 新增 `.agents/skills/material2video/references/reference-video-analysis.md`，覆盖触发、证据类型、时间轴、视觉事件、导演设计、视觉语法、母题、声音、表面/机制分栏、可迁移规则、反推模板、多参考共性、本片落点、自检与失败模式。
- [x] 1.2 明确与 `reference-style.md` 的分工和叠加顺序，检查不重复要求两套外观指标、不新增 CLI、运行时或分镜字段。

## 2. 接入触发点

- [x] 2.1 更新 `SKILL.md` 通用场景要点，让「学习/拆解/借鉴参考视频」先进入逆向拆解，再按需进入风格契约。
- [x] 2.2 在 `reference-style.md` 增加「第零步：先拆解，再量测」，并在契约模板记录采用的底层机制。
- [x] 2.3 更新 `creative-production.md`、`visual-creative-direction.md`、`visual-impact-design.md` 与 `subagent-review.md` 的相关入口，保持既有词汇与边界一致。

## 3. 验证与交付

- [x] 3.1 检查新增与修改文档的相对链接、锚点、表格与中文表述，确认没有把规划能力写成已实现。
- [x] 3.2 增加入口可达性测试，运行相关测试、`python .agents/skills/material2video/scripts/sync_docs.py --check`，确认类型目录无漂移。
- [x] 3.3 审查暂存内容仅含本变更文档，排除凭据、缓存、示例媒体与其他未跟踪变更后提交。
- [x] 3.4 同步 `openspec/specs/reference-style-transfer/spec.md` 主规格，归档本变更并提交归档结果。
