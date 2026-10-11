---
name: article2video
description: 使用统一 a2v 制作入口创作金融时间序列、文章叙事与通用多场景视频。用于准备类型材料、编排、预演、评审、渲染与排查不一致问题。
---

# article2video 制作 Skill

项目采用共享制作底座、独立视频类型、统一制作入口。发展顺序是先建设金融时间序列等专用视频，再沉淀多类型共用能力，逐步扩展到通用多场景视频。

开始制作前读取作品目录中的 `project.json`，确认类型，再按该类型参考材料组织内容。始终先校验和准备，生成完整预演并实际查看，再填写评审结论；没有当前且完整的评审不能正式导出。所有生成产物都是派生产物，不代替可编辑材料。

| 类型 | 创作指导 |
|---|---|
| `financial-timeseries` | [金融时间序列视频](references/financial-timeseries-video.md)：验证行情口径、假设投资计算与手机可读性。 |
| `article-narrative` | [文章生成分镜](references/article-to-storyboard.md)、[输入审查](references/input-review.md)、[制作流程](references/production-workflow.md)：保留 v4 world、口播、状态轨道、镜头与连续性门禁。 |
| `general` | 按独立的 `general-plan.json` 组合受控图文、完整金融/文章片段及公开 React code scene。 |

通用场景共享一条全片帧轴。首版画布为 1080×1920、30 fps；完整嵌入片段不支持裁切、变速或拉伸。代码场景通过公开 `@a2v/scene` API 使用确定性帧上下文。源码约束检查不是执行任意不可信代码的安全沙箱。

## 统一命令

```powershell
uv run a2v types
uv run a2v init --type general --project videos/<slug>
uv run a2v validate --project videos/<slug>
uv run a2v prepare --project videos/<slug>
uv run a2v preview --project videos/<slug>
uv run a2v review-template --project videos/<slug>
# 查看预演，填写 outputs/review.json 中的评审结论与证据
uv run a2v review --project videos/<slug>
uv run a2v render --project videos/<slug>
uv run a2v status --project videos/<slug>
```

金融材料在价格来源和交易日核验完成后，可用 `uv run a2v financial plan --project videos/<slug> --duration-seconds 60` 生成计划。

文章专属输入审查与候选稿工具保留为 `uv run a2v article input-review|candidate|adopt-candidate ...`。已有 v4 文章或历史金融材料迁移前先完整备份，执行 `uv run a2v migrate --project <目录> --from article-v4|financial`；金融支持当前 v7 和旧 v1～v6 计划，v1～v3 文章不自动迁移。统一入口与状态规则见仓库 [README](../../../README.md)，架构规格见 [OpenSpec 变更](../../../openspec/changes/refactor-modular-video-production/proposal.md)。

## 文章视觉和编排原则

文章类型通过同一视觉世界承载一个观点；`stages[]` 是推理阶段，不代表切换到新的视觉世界。对象身份、状态、镜头、beats 与文字在一个确定性时间轴内共同推进。先声明阶段的视觉论证、关系、焦点、构图和动效语义，再选用 [视觉原语目录](references/primitive-catalog.md)。树形原语不足以表达按帧几何时，才使用作品代码场景。

代码场景须符合[代码场景契约](references/code-scenes.md)的依赖白名单、纯函数与按帧求值要求。动画不得依赖挂钟、随机数或网络；同一场景帧无论重复、倒序或随机求值都必须一致。

正文与口播的历史文章标准、材料字段和连续性评审规则见[分镜结构](references/storyboard-schema.md)、[文章创作](references/article-to-storyboard.md)和[评审量表](references/visual-review-rubric.md)。这些文章专属约束不作用于金融片段或整条通用视频。

## 渲染与评审

- 材料、资产或嵌入作品变化后重新 `prepare`，再生成完整 `preview` 和新评审。
- 完整预演只绑定当前准备指纹；限帧预览只用于开发排查。
- 人工或 AI 语义评审须由人实际查看画面后填写依据，工具不会自动判定审美通过。
- 正式渲染在临时路径生成并验收后替换交付文件；失败不覆盖先前有效成片。
- 嵌入的金融或文章片段不能绕过其类型校验及专用评审门禁。

测试和严格示例校验方式见仓库 README。测试、构建和输出参数应使用仓库配置与 `a2v --help`，不要调用旧的 Skill 脚本制作入口。
