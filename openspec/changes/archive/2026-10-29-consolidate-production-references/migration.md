# 文档迁移记录

清单基线：`.agents/skills/material2video/references/` 原有 40 份 Markdown，整理后 29 份。条目按原文档的仍有效内容定位；纯导航或失效规则不迁移。

| 原文档 | 处理 | 新权威位置 |
|---|---|---|
| `article-to-storyboard.md` | 移除重复操作指南；输入分流补入阶段入口 | `stage-plan.md`、`production-workflow.md`、`storyboard-schema.md`、`input-review` 操作段现并入 `stage-plan.md` |
| `cinematic-video.md` | 移除已退役档位说明；当前命令/契约拆回实际所有者 | `README.md`（lookdev）、`article-media-and-sound.md`（无声/声音）、`storyboard-schema.md` 与 `code-scene-runtime.md`（镜头/场景） |
| `code-scene-troubleshooting.md` | 按需排错并入运行时契约 | `code-scene-runtime.md#按需排错` |
| `production-record-template.md` | 模板放回规则所在流程文档 | `production-workflow.md#推进与回退记录模板` |
| `reference-analysis-template.md` | 模板放回参考拆解方法页；去掉无依据评分列 | `reference-video-analysis.md#交付模板` |
| `subagent-review-template.md` | 评审模板放入隔离与输出契约 | `subagent-review.md#评审输出模板` |
| `reach-potential.md` | 保留为可选传播表现评估并并入导演审查 | `director-review-and-edit.md#传播表现评估` |
| `visual-diagnosis.md` | 症状因果表、形象判据和主体尺度起点并入讲解设计 | `explainer-design.md#看图诊断与形象判据` |
| `visual-creative-direction-examples.md` | 合并为按需创作示例集 | `production-examples.md` |
| `visual-review-examples.md` | 合并为按需复核演练集 | `production-examples.md#视觉复核判断演练` |
| `external-projects.md` | 来源、许可、固定提交登记保留并入合页 | `external-reference-projects.md` |
| `vibe-knowledge-film.md` | 专项查阅顺序与转译说明合并入登记页 | `external-reference-projects.md#vibe-knowledge-film-项目使用指引` |
| `input-review.md` | 保留命令、人工判定字段与主题跳过边界，合并进方案阶段 | `stage-plan.md#源文审查命令与记录` |

## 重要边界

- `creative-production.md` 保留：它仍含独有的体验设计、预算、迭代和回归要求，全部迁入 `production-workflow.md` 会造成职责混杂及超长入口。
- `visual-review-rubric.md` 与 `director-review-and-edit.md` 保持分工：前者定义视觉复核和问题闭环；后者承载按需全片导演审查、剪辑重组与可选传播判断。
- `checkpoint-gates.md` 继续唯一规定审核风险、人员、轮次与完成条件。参考风格页删去固定轮次表，改为引用风险计划；不改变评审合同。
- 示例媒体、作品材料和运行时代码未修改。

## 删除前引用检查

活动入口、examples、styles 与项目规划已更新到新位置。`openspec/changes/archive/` 中的旧路径属于历史记录，刻意不回写历史档案。
