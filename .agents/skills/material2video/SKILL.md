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
| `general` | [作品视觉设计与制作流程](references/production-workflow.md)、[分镜结构](references/storyboard-schema.md)、[媒体素材与音效](references/article-media-and-sound.md)、[代码场景契约](references/render-contract.md)：v8 全画布代码场景多幕讲解。 |
| `housing-timeseries` | 按 `series.json` 提供连续年度住宅销售额、面积、计算均价与来源口径；生成 1080×1920、30 fps 无声折线视频。 |
<!-- generated:type-catalog:end -->

通用类型使用 v8 storyboard.json：每一幕都是本地 React `code` 场景，画幅默认为 1920×1080 横屏并支持显式 1080×1920 竖屏；画面配色、构图与动效由作品代码决定，图片与视频经已导入素材 ID 解析；代码场景由准备阶段按画幅实时录制并缓存，完整预演与导出复用同一片段；不支持旧模板、视觉主题、general-plan 编排或完整片段嵌入。

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

通用讲解（含在线素材）使用 `general` 一个入口：可选图库检索用 `uv run m2v general assets search --project videos/general/<slug>`，素材只有经 `uv run m2v general assets import --project <目录> --manifest <清单>` 导入留证后才能被作品按 ID 取用；再走校验、准备、完整预演与导出。材料、检索、导入与混音规则见[文章媒体与音效](references/article-media-and-sound.md)。

通用作品的输入审查与候选稿工具保留为 `uv run m2v general input-review|candidate|adopt-candidate ...`。`m2v relocate --project videos/<slug>` 只迁移作品目录及全部产物；旧金融材料迁移仍使用 `m2v migrate --project <目录> --from financial`；通用 v7 及更早分镜必须重新编排 v8。金融支持当前 v7/v8 和旧 v1～v6 计划；已有统一作品的 v7 升级使用 `m2v financial migrate-line`，文章旧版本不自动迁移。统一入口与状态规则见仓库 [README](../../../README.md)，架构规格见 [OpenSpec 变更](../../../openspec/specs/modular-video-production/spec.md)。

## 自动选择音色（所有有自身旁白的作品）

选音由制作助手执行，CLI 不调用模型。每次新制作或重新生成时先检查 `project.json`：用户明确选择的 `tts.voice` 保持优先；已有助手选择且旁白摘要未变时复用；缺失选择或旁白改变时，按以下步骤执行，无需试听确认：

1. 阅读完整有序旁白，判断语言、受众、内容、情绪与表达风格；通用类型读取逐幕逐段旁白。
2. 运行 `uv run m2v voices --json`，其他语言通过 `--locale <区域>` 或 `--locale all` 查询。查询失败就明确报告并修复连接，不虚构候选、不静默使用晓晓。结合服务返回的 categories/personalities 与内容选择；不按性别硬编码，不预先统一指定某一种声音。
3. 写入 `project.json` 的 `tts.voice` 和 `tts.selection`（mode、rationale、narrationSha256），填写结合具体旁白的理由。摘要使用共享 `m2v.engine.tts.narration_digest(texts)`，`texts` 为播放顺序中的自身旁白数组：通用类型逐幕逐段收集 `text`。忽略空白段，保留其余字符串原文与分段边界。
4. 保留已有语速、停顿设置。继续 prepare、完整 preview 与 render；不得把音色标签或媒体技术验收描述为已试听、自然度达标。

旁白变化必须重新判断，可保留同一音色并更新理由和摘要；画面变化不要求重选。用户手动修改作品音色时移除原助手 `selection`；`prepare --voice` 仅覆盖本次，并且不沿用助手理由。只有 CLI 覆盖语速时仍需有效助手选择。有自身旁白但未明确音色时 prepare 会阻断，不能靠重新渲染自动换声。字段、实际参数溯源和迁移见[配音契约](references/media-contract.md#配音音色与语速)。

## 通用作品编排原则

通用类型只接受 v8 全画布代码场景：每一幕声明唯一 `id`、`template: "code"`、`content.entry`
（作品 `scenes/` 下的 TSX）与可选 `content.props`，并声明旁白数组（可以没有旁白，此时用
`durationFrames` 声明镜头长度）。`input.kind` 为 `article` 时绑定源文，为 `topic` 时只声明
`input.topic` 并由逐幕 `keywords` 驱动可选图库检索。

制作顺序是**先设计再动手**：确定画幅（用户未指定时取横屏）→ 在作品 `DESIGN.md` 写下参考依据、
视觉隐喻、字体配色、开场/核心/结尾三处代表构图、镜头承接与声音意图 → 做三张关键画面 →
编排运动 → 再扩展全片。作品代码控制整张画布，必须自己画满不透明背景，并让重要文字与主体
避让 `subtitleSafeArea`；共享字幕是白字配不透明深色底板，独立于作品配色。

先做一段 15～20 秒的代表片段验证风格，再扩展全片；做完要**实际观看**关键帧与含运动、转场和
声音的代表片段，把时间位置、修改与复查写进作品 `outputs/visual-notes.md`；无法观看时如实说明，
不能虚构通过。记录与设计稿都不是导出门禁，也没有新增的用户逐次确认环节。

动画由 `segmentWindows` 与录制时钟驱动，画面随真实口播推进；视频与图片用 `useMediaAsset(id)`
按素材 ID 取用，比例不受画幅限制，裁切与摆位由作品决定；视频要等到可播放后再 `ready()`，
素材原声不进入母版。素材只能来自 `assets/media/` 中已导入并留证的内容寻址文件。音效用顶层
`soundtrack` 按 `sceneId`/`segmentId`/`offsetMs` 定位，可用内置提示音或本地素材。默认根据旁白
原文生成字幕并烧录到预演和正式成片，无需额外开关，不得仅交付外置字幕；无讲话的停顿及阅读尾段
不显示字幕。每段实际 TTS 决定时间，无旁白镜头按声明帧数或目标剩余时长分配，完整成片含阅读停留
与淡化不超过 600 秒。

浏览器量测只覆盖共享字幕的安全区、换行与可见性；作品正文在录制的片段里，系统不声称能自动
识别其中的全部正文或主体遮挡——那部分由上面的实际观看补足。详见
[通用作品创作](references/article-to-storyboard.md)、[分镜结构](references/storyboard-schema.md)、
[媒体素材与音效](references/article-media-and-sound.md)与[评审量表](references/visual-review-rubric.md)。

## 渲染与评审

- 材料、资产或渲染代码变化后重新 `prepare`，再生成完整 `preview`；可选评审如需使用也应重新填写。
- 完整预演只绑定当前准备指纹；限帧预览只用于开发排查，不能授权正式导出。
- 所有类型均不要求人工画面评审；默认在校验、准备和完整预演自动验收后直接导出。`review-template` / `review` 仅供主动评审，填写通过结论时仍需真实依据，不自动虚构人工结论；金融维持专用自动探针。通用作品的设计稿与观看记录不参与门禁。
- 正式导出独立验证完整预演的当前准备指纹、文件摘要与完整帧数，并进行媒体技术验收；缺失、过期、被替换或限帧预演仍会阻断。
- 正式渲染在临时路径生成并验收后替换交付文件；失败不覆盖先前有效成片。
- 正式渲染成功并写好成片旁车后，统一入口会清理本作品 `outputs/` 中旧视频和已知检查/调试产物；金融绑定的完整预演会保留，其他类型按原规则清理预演。保留本次成片及旁车、准备与评审 JSON、可重渲的准备媒体。渲染失败不清理，共享构建缓存不受影响；逐项清理失败会报告遗留路径。

测试和严格示例校验方式见仓库 README。测试、构建和输出参数应使用仓库配置与 `m2v --help`，不要调用旧的 Skill 脚本制作入口。

## 新增视频类型

只在两处落地：先在 `src/m2v/types/catalog.json` 登记类型身份（名称与一句话说明）、材料入口（材料名与默认文件名）、初始化模板与文档文案，再实现该类型的行为适配器（校验、准备、预演、渲染与可选的评审钩子）。统一入口不按类型名硬编码分发，作品契约也不维护类型白名单与材料映射；已实现但未在目录登记的类型会在渲染前失败。

上述类型表、README 的类型清单与项目规划的规划清单都由该目录生成。改动目录后运行 `python .agents/skills/material2video/scripts/sync_docs.py` 重新生成，用 `--check` 只比对不写入。
