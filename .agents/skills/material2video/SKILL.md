---
name: material2video
description: 使用统一 m2v 制作入口创作金融时间序列、文章叙事、通用多场景与在线素材剪辑视频。用于准备类型材料、编排、预演、评审、渲染与排查不一致问题。
---

# Material2Video（材料成片）制作 Skill

项目采用共享制作底座、独立视频类型、统一制作入口。发展顺序是先建设金融时间序列等专用视频，再沉淀多类型共用能力，逐步扩展到通用多场景视频。

开始制作前读取作品目录中的 `project.json`，确认类型，再按该类型参考材料组织内容。先校验和准备，再生成完整预演；所有类型通过当前完整预演自动验收后即可正式导出，无需人工查看、填写依据或再次确认；人工画面评审仅为可选工具，文章原文语义审查保留。所有生成产物都是派生产物，不代替可编辑材料。

| 类型 | 创作指导 |
|---|---|
<!-- generated:type-catalog:start -->
| `financial-timeseries` | [金融时间序列视频](references/financial-timeseries-video.md)：核验行情口径、投资计算并通过完整预演自动验收。 |
| `article-narrative` | [文章生成分镜](references/article-to-storyboard.md)、[分镜结构](references/storyboard-schema.md)、[制作流程](references/production-workflow.md)：v5 多幕卡片与真实语音时间轴。 |
| `general` | 按独立的 `general-plan.json` 组合受控图文、完整金融/文章片段及公开 React code scene。 |
| `housing-timeseries` | 按 `series.json` 提供连续年度住宅销售额、面积、计算均价与来源口径；生成 1080×1920、30 fps 无声折线视频。 |
| `stock-montage` | [在线素材剪辑](references/stock-montage-video.md)：先执行 `m2v stock search` 检索并留证素材，再校验、完整预演与导出。 |
<!-- generated:type-catalog:end -->

通用场景共享一条全片帧轴。首版画布为 1080×1920、30 fps；完整嵌入片段不支持裁切、变速或拉伸。嵌入文章使用 v5 讲解 composition，保留完整时间轴、字幕与配音。代码场景通过公开 `@m2v/scene` API 使用确定性帧上下文。源码约束检查不是执行任意不可信代码的安全沙箱。

## 统一命令

```powershell
uv run m2v types
uv run m2v init --type general --project <slug>
uv run m2v validate --project videos/general/<slug>
uv run m2v prepare --project videos/general/<slug>
uv run m2v preview --project videos/general/<slug>
uv run m2v render --project videos/general/<slug>
uv run m2v status --project videos/general/<slug>
uv run m2v relocate --project videos/<old-slug> # 迁移旧目录及全部产物
```

金融材料在价格来源和交易日核验完成后，可用 `uv run m2v financial plan --project videos/financial-timeseries/<slug> --duration-seconds 60` 生成计划。

年度住宅销售均价使用独立 `housing-timeseries` 类型，材料、校验和画面契约见[年度住宅均价视频](references/housing-timeseries-video.md)。

在线素材剪辑使用独立 `stock-montage` 类型：先 `uv run m2v stock search --project videos/stock-montage/<slug>` 检索并留证素材，再走校验、准备、完整预演与导出；材料、检索与剪辑规则见[在线素材剪辑视频](references/stock-montage-video.md)。

文章专属输入审查与候选稿工具保留为 `uv run m2v article input-review|candidate|adopt-candidate ...`。`m2v relocate --project videos/<slug>` 只迁移作品目录及全部产物；旧金融材料迁移仍使用 `m2v migrate --project <目录> --from financial`；文章 v1～v4 必须重新编排 v5。金融支持当前 v7/v8 和旧 v1～v6 计划；已有统一作品的 v7 升级使用 `m2v financial migrate-line`，文章旧版本不自动迁移。统一入口与状态规则见仓库 [README](../../../README.md)，架构规格见 [OpenSpec 变更](../../../openspec/specs/modular-video-production/spec.md)。

## 文章讲解编排原则

文章类型只接受 v5 scenes 多幕讲解。按观点、对比、步骤、因果图、图片选择模板，旁白和画面摘要独立，展示项绑定本幕旁白 ID。默认深色，可选浅色。每段实际 TTS 决定时间，完整成片含阅读停留与淡化不超过 60 秒；旧 v1～v4 须重新编排。

先阅读源文并填写 outputs/input-review.json，再制作分镜与配音。完整有声预演自动验收后即可导出；可按需填写 outputs/review.json，不再要求旧 production.json、单世界或镜头连续性门禁。详见 [分镜结构](references/storyboard-schema.md)、[文章创作](references/article-to-storyboard.md)和[评审量表](references/visual-review-rubric.md)。共享原语与代码场景文档仍供 general 和内部动画模块使用，不属于 v5 模板创作入口。

## 渲染与评审

- 材料、资产或嵌入作品变化后重新 `prepare`，再生成完整 `preview`；可选评审如需使用也应重新填写。
- 完整预演只绑定当前准备指纹；限帧预览只用于开发排查，不能授权正式导出。
- 所有类型均不要求人工画面评审；默认在校验、准备和完整预演自动验收后直接导出。`review-template` / `review` 仅供主动评审，填写通过结论时仍需真实依据，不自动虚构人工结论；金融维持专用自动探针。
- 正式导出独立验证完整预演的当前准备指纹、文件摘要与完整帧数，并进行媒体技术验收；缺失、过期、被替换或限帧预演仍会阻断。
- 正式渲染在临时路径生成并验收后替换交付文件；失败不覆盖先前有效成片。
- 正式渲染成功并写好成片旁车后，统一入口会清理本作品 `outputs/` 中旧视频和已知检查/调试产物；金融绑定的完整预演会保留，其他类型按原规则清理预演。保留本次成片及旁车、准备与评审 JSON、可重渲的准备媒体。渲染失败不清理，共享构建缓存不受影响；逐项清理失败会报告遗留路径。
- 嵌入的金融或文章片段不能绕过其类型校验及专用自动验收和完整预演门禁。

测试和严格示例校验方式见仓库 README。测试、构建和输出参数应使用仓库配置与 `m2v --help`，不要调用旧的 Skill 脚本制作入口。

## 新增视频类型

只在两处落地：先在 `src/m2v/types/catalog.json` 登记类型身份（名称与一句话说明）、材料入口（材料名与默认文件名）、初始化模板与文档文案，再实现该类型的行为适配器（校验、准备、预演、渲染与可选的评审钩子）。统一入口不按类型名硬编码分发，作品契约也不维护类型白名单与材料映射；已实现但未在目录登记的类型会在渲染前失败。

上述类型表、README 的类型清单与项目规划的规划清单都由该目录生成。改动目录后运行 `python .agents/skills/material2video/scripts/sync_docs.py` 重新生成，用 `--check` 只比对不写入。
