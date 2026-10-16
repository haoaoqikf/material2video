---
name: material2video
description: 使用统一 m2v 制作入口创作金融时间序列、住宅时间序列、通用讲解视频。用于准备类型材料、编排、预演、评审、渲染与排查不一致问题。
---

# Material2Video（材料成片）制作 Skill

项目采用共享制作底座、独立视频类型、统一制作入口。发展顺序是先建设金融时间序列等专用视频，再沉淀多类型共用能力，完善通用混合媒体讲解视频。

开始制作前读取作品目录中的 `project.json`，确认类型，再按该类型参考材料组织内容。整体流程为材料审查 → 编排旁白 → 选择音色并保存 → 校验与准备 → 完整预演 → 正式导出；无自身旁白时跳过选音。所有类型通过当前完整预演自动验收后即可正式导出，无需人工查看、填写依据或再次确认；人工画面评审仅为可选工具，文章原文语义审查保留。所有生成产物都是派生产物，不代替可编辑材料。

| 类型 | 创作指导 |
|---|---|
<!-- generated:type-catalog:start -->
| `financial-timeseries` | [金融时间序列视频](references/financial-timeseries-video.md)：核验行情口径、投资计算并通过完整预演自动验收。 |
| `general` | [文章生成分镜](references/article-to-storyboard.md)、[分镜结构](references/storyboard-schema.md)、[媒体素材与音效](references/article-media-and-sound.md)、[制作流程](references/production-workflow.md)：v7 混合媒体与代码场景多幕讲解。 |
| `housing-timeseries` | 按 `series.json` 提供连续年度住宅销售额、面积、计算均价与来源口径；生成 1080×1920、30 fps 无声折线视频。 |
<!-- generated:type-catalog:end -->

通用类型使用 v7 storyboard.json，支持原文或主题输入、七种模板（六种受控模板加本地 React `code` 场景）及混合媒体；代码场景由准备阶段实时录制并缓存，完整预演与导出复用同一片段；不支持 general-plan 编排或完整片段嵌入。

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

文章讲解（含在线素材）使用 `general` 一个入口：可选图库检索用 `uv run m2v general assets search --project videos/general/<slug>`，素材只有经 `uv run m2v general assets import --project <目录> --manifest <清单>` 导入留证后才能进入分镜；再走校验、准备、完整预演与导出。材料、检索、导入与混音规则见[文章媒体与音效](references/article-media-and-sound.md)。

文章专属输入审查与候选稿工具保留为 `uv run m2v general input-review|candidate|adopt-candidate ...`。`m2v relocate --project videos/<slug>` 只迁移作品目录及全部产物；旧金融材料迁移仍使用 `m2v migrate --project <目录> --from financial`；文章 v6 及更早分镜必须重新编排 v7。金融支持当前 v7/v8 和旧 v1～v6 计划；已有统一作品的 v7 升级使用 `m2v financial migrate-line`，文章旧版本不自动迁移。统一入口与状态规则见仓库 [README](../../../README.md)，架构规格见 [OpenSpec 变更](../../../openspec/specs/modular-video-production/spec.md)。

## 自动选择音色（所有有自身旁白的作品）

选音由制作助手执行，CLI 不调用模型。每次新制作或重新生成时先检查 `project.json`：用户明确选择的 `tts.voice` 保持优先；已有助手选择且旁白摘要未变时复用；缺失选择或旁白改变时，按以下步骤执行，无需试听确认：

1. 阅读完整有序旁白，判断语言、受众、内容、情绪与表达风格；通用类型读取逐幕逐段旁白。
2. 运行 `uv run m2v voices --json`，其他语言通过 `--locale <区域>` 或 `--locale all` 查询。查询失败就明确报告并修复连接，不虚构候选、不静默使用晓晓。结合服务返回的 categories/personalities 与内容选择；不按性别硬编码，不预先统一指定某一种声音。
3. 写入 `project.json` 的 `tts.voice` 和 `tts.selection`（mode、rationale、narrationSha256），填写结合具体旁白的理由。摘要使用共享 `m2v.engine.tts.narration_digest(texts)`，`texts` 为播放顺序中的自身旁白数组：通用类型逐幕逐段收集 `text`。忽略空白段，保留其余字符串原文与分段边界。
4. 保留已有语速、停顿设置。继续 prepare、完整 preview 与 render；不得把音色标签或媒体技术验收描述为已试听、自然度达标。

旁白变化必须重新判断，可保留同一音色并更新理由和摘要；画面变化不要求重选。用户手动修改作品音色时移除原助手 `selection`；`prepare --voice` 仅覆盖本次，并且不沿用助手理由。只有 CLI 覆盖语速时仍需有效助手选择。有自身旁白但未明确音色时 prepare 会阻断，不能靠重新渲染自动换声。字段、实际参数溯源和迁移见[配音契约](references/media-contract.md#配音音色与语速)。

## 文章讲解编排原则

文章类型只接受 v7 scenes 多幕讲解，`input.kind` 为 `article` 时绑定源文，为 `topic` 时只声明 `input.topic` 并由逐幕 `keywords` 驱动可选图库检索。按观点、对比、步骤、因果图、图片、视频与本地代码场景选择模板，旁白和画面摘要独立，展示项绑定本幕旁白 ID；图片、视频与代码幕允许没有旁白，此时用 `durationFrames` 声明镜头长度。默认深色，可选浅色。默认根据旁白原文生成字幕，并烧录到预演和正式成片，无需额外开关，不得仅交付外置字幕；正文留出字幕安全区，无讲话的停顿及阅读尾段不显示字幕。每段实际 TTS 决定时间，无旁白镜头按声明帧数或目标剩余时长分配，完整成片含阅读停留与淡化不超过 600 秒；v6 及更早分镜须重新编排。素材只能来自 `assets/media/` 中已导入并留证的内容寻址文件，默认要求 9:16（容差 2%），个别幕可显式 `aspectRatio: "any"`；代码场景的 TSX 入口放在作品 `scenes/` 下，只允许批准的共享依赖；音效用顶层 `soundtrack` 按 `sceneId`/`segmentId`/`offsetMs` 定位，可用内置提示音或本地素材。

先阅读源文并填写 outputs/input-review.json（`topic` 输入跳过该审查），再制作分镜、导入素材与配音。完整有声预演自动验收后即可导出；可按需填写 outputs/review.json，不再要求旧 production.json 门禁。详见 [分镜结构](references/storyboard-schema.md)、[文章创作](references/article-to-storyboard.md)、[媒体素材与音效](references/article-media-and-sound.md)和[评审量表](references/visual-review-rubric.md)。

## 渲染与评审

- 材料、资产或渲染代码变化后重新 `prepare`，再生成完整 `preview`；可选评审如需使用也应重新填写。
- 完整预演只绑定当前准备指纹；限帧预览只用于开发排查，不能授权正式导出。
- 所有类型均不要求人工画面评审；默认在校验、准备和完整预演自动验收后直接导出。`review-template` / `review` 仅供主动评审，填写通过结论时仍需真实依据，不自动虚构人工结论；金融维持专用自动探针。
- 正式导出独立验证完整预演的当前准备指纹、文件摘要与完整帧数，并进行媒体技术验收；缺失、过期、被替换或限帧预演仍会阻断。
- 正式渲染在临时路径生成并验收后替换交付文件；失败不覆盖先前有效成片。
- 正式渲染成功并写好成片旁车后，统一入口会清理本作品 `outputs/` 中旧视频和已知检查/调试产物；金融绑定的完整预演会保留，其他类型按原规则清理预演。保留本次成片及旁车、准备与评审 JSON、可重渲的准备媒体。渲染失败不清理，共享构建缓存不受影响；逐项清理失败会报告遗留路径。

测试和严格示例校验方式见仓库 README。测试、构建和输出参数应使用仓库配置与 `m2v --help`，不要调用旧的 Skill 脚本制作入口。

## 新增视频类型

只在两处落地：先在 `src/m2v/types/catalog.json` 登记类型身份（名称与一句话说明）、材料入口（材料名与默认文件名）、初始化模板与文档文案，再实现该类型的行为适配器（校验、准备、预演、渲染与可选的评审钩子）。统一入口不按类型名硬编码分发，作品契约也不维护类型白名单与材料映射；已实现但未在目录登记的类型会在渲染前失败。

上述类型表、README 的类型清单与项目规划的规划清单都由该目录生成。改动目录后运行 `python .agents/skills/material2video/scripts/sync_docs.py` 重新生成，用 `--check` 只比对不写入。
