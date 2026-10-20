---
name: material2video
description: 使用统一 m2v 制作入口创作金融时间序列、住宅时间序列、通用讲解视频。用于准备类型材料、编排、预演、评审、渲染与排查不一致问题。
---

# Material2Video（材料成片）制作 Skill

项目采用共享制作底座、独立视频类型、统一制作入口。发展顺序是先建设金融时间序列等专用视频，再沉淀多类型共用能力，完善通用混合媒体讲解视频。

开始制作前读取作品目录中的 `project.json`，确认类型，再按该类型参考材料组织内容。整体流程为材料审查 → 编排旁白 → 按文本和服务元数据选择音色并保存 → 校验与时间轴准备 → 按需检查生成与修改 → 全片生成一次 → 验收与复核 → 交付同一文件；无自身旁白时跳过选音。所有类型由 render 生成一次完整候选，自动验收后直接交付同一文件，CLI 不要求人工记录；助手须为所有作品复核手机观看下的可读性、观众可见文案与风格，并关闭必改项，general 另基于帧序列、量测与自动检测完成完整替代复核。所有制作阶段无需用户确认。全流程不要求播放视频、连续收听声音或试听音色；按作品类型使用静帧/时间标注帧序列、路径与画面量测、字幕和时间戳核对及自动音频信号分析等证据，并如实记录覆盖范围。文章原文语义审查保留。所有生成产物都是派生产物，不代替可编辑材料。

**所有作品默认面向手机观看**，但不因此强制竖屏；按作品选定的画幅与用户指定的设备方向设计和复核。每部作品只在片尾出现一份简短署名与版权说明，不在逐幕重复素材署名，也不在画面或字幕中出现仓库文件名、路径、制作文档或内部查阅指引。完整事实来源、作者和许可依据保存在作品材料中。多段落作品还须复核重复版式和信息推进；重复静态卡片或逐页替换文字板主导全片时，作为必改项返工，不得以技术 QA 通过放行。

| 类型 | 创作指导 |
|---|---|
<!-- generated:type-catalog:start -->
| `financial-timeseries` | [金融时间序列视频](references/financial-timeseries-video.md)：核验行情口径、投资计算并通过完整候选自动验收。 |
| `general` | [作品视觉设计与制作流程](references/production-workflow.md)、[分镜结构](references/storyboard-schema.md)、[媒体素材与音效](references/article-media-and-sound.md)、[代码场景契约](references/code-scene-runtime.md)：v8 全画布代码场景多幕讲解。 |
| `housing-timeseries` | 按 `series.json` 提供连续年度住宅销售额、面积、计算均价与来源口径；生成 1080×1920、60 fps 无声折线视频。 |
<!-- generated:type-catalog:end -->

通用类型使用 v8 storyboard.json：每一幕都是本地 React `code` 场景，画幅默认为 1920×1080 横屏并支持显式 1080×1920 竖屏；画面配色、构图与动效由作品代码决定，图片与视频经已导入素材 ID 解析；代码场景在检查或正式生成时按所需窗口逐帧录制并缓存，检查和正式生成按区间复用录制缓存；不支持旧模板、视觉主题、general-plan 编排或完整片段嵌入。

## 制作档位（standard / cinematic）

通用作品分 **standard**（默认）与 **cinematic** 两档：standard 是默认档，保持快速链路与自动
验收；cinematic 由作品在 `project.json` 的 `productionProfile` 显式声明（也可用
`prepare --profile cinematic` 临时覆盖，分镜不重复声明档位）；用户明确要求
「电影级 / 极致 / 惊艳 / 发布级 / 品牌片」时必须用 cinematic。逐项对照表见
[电影级制作档位](references/cinematic-video.md#档位对照)。

**触发词**：用户明确要求「电影级 / 极致 / 惊艳 / 发布级 / 品牌片」时 MUST 使用 cinematic，
不得静默按 standard 交付再声称电影级；反过来，用户没有这样要求时不要默认加电影级开销。

cinematic 按 **Brief → Look-dev → Hero → Full film → QA/自主复核** 五个阶段推进，每阶段有产出与
放行条件；命令为 `m2v lookdev`、`m2v qa`、`m2v assets audit`，正式导出沿用 `m2v render`。
三者已接线并只服务 general 作品（其他类型会明确拒绝）。cinematic 不设数字评分卡：技术 QA 与
hero 风险帧序列及运动量测后全片帧序列与自动音频复核最终文件，自主关闭必改项并交付。字段、清单、自主复核、反模式与成本见
[电影级制作档位](references/cinematic-video.md)。

**look-dev 不设人工确认门禁**：standard 与 cinematic 都不在 look-dev 停下来等确认。
cinematic 必须生成覆盖全片的时间标注帧序列及关键静帧，结合逐帧运动/构图量测和自动音频信号复核，把时间码与问题记进作品 `outputs/visual-notes.md`，
关闭必改项后再铺全片；该记录是制作完成依据，不是 CLI 导出门禁。最终成片也无需用户确认。
不得把未完成帧序列与自动信号复核的成片描述为电影级；不要求播放视频或试听音色，替代证据的覆盖和限制须如实记录。

档位声明、镜头/look 字段与电影级共享套件（`CameraRig`、`PostFX` 与深空元件）已经落地；
`lookdev` / `qa` / `assets audit` 入口已接线，太阳系一镜到底参考片保留历史 look-dev 与 QA 记录；旧用户确认不代替当前版本的完整复核。cinematic 交付普通 H.264 MP4，不另出母版。

## 统一命令

```powershell
uv run m2v types
uv run m2v init --type general --project <slug>
uv run m2v validate --project videos/general/<slug>
uv run m2v prepare --project videos/general/<slug>
# 可选片段检查，默认前十秒且严格短于全片
uv run m2v preview --project videos/general/<slug>
uv run m2v render --project videos/general/<slug>
uv run m2v status --project videos/general/<slug>
uv run m2v relocate --project videos/<old-slug> # 迁移旧目录及全部产物
uv run m2v lookdev --project videos/general/<slug>  # cinematic：4K 静帧、时间标注风险帧与自动音频报告（复核结论记入 visual-notes.md）
uv run m2v qa --project videos/general/<slug>       # cinematic：技术 QA，输出 outputs/qa.json
uv run m2v assets audit --project videos/general/<slug>  # 资产质量与许可审计
```

金融材料在价格来源和交易日核验完成后，可用 `uv run m2v financial plan --project videos/financial-timeseries/<slug> --duration-seconds 60` 生成计划。

年度住宅销售均价使用独立 `housing-timeseries` 类型，材料、校验和画面契约见[年度住宅均价视频](references/housing-timeseries-video.md)。

通用讲解（含在线素材）使用 `general` 一个入口：图库默认且仅启用 Pixabay（需 `M2V_PIXABAY_API_KEY`），Pexels 固定停用；公开媒体直链仍可统一导入。可选图库检索用 `uv run m2v general assets search --project videos/general/<slug>`，素材只有经 `uv run m2v general assets import --project <目录> --manifest <清单>` 导入留证后才能被作品按 ID 取用；再走校验、准备、按需检查与一次全片生成交付。材料、检索、导入与混音规则见[文章媒体与音效](references/article-media-and-sound.md)。

通用作品的输入审查与候选稿工具保留为 `uv run m2v general input-review|candidate|adopt-candidate ...`。`m2v relocate --project videos/<slug>` 只迁移作品目录及全部产物；旧金融材料迁移仍使用 `m2v migrate --project <目录> --from financial`；通用 v7 及更早分镜已不再适用，必须重新编排 v8。金融支持当前 v7/v8 和旧 v1～v6 计划；已有统一作品的 v7 升级使用 `m2v financial migrate-line`，文章旧版本不自动迁移。统一入口与状态规则见仓库 [README](../../../README.md)，架构规格见 [OpenSpec 变更](../../../openspec/specs/modular-video-production/spec.md)。

## 自动选择音色（所有有自身旁白的作品）

选音由制作助手执行，CLI 不调用模型。每次新制作或重新生成时先检查 `project.json`：用户明确选择的 `tts.voice` 保持优先；已有助手选择且旁白摘要未变时复用；缺失选择或旁白改变时，按以下步骤执行，无需试听确认：

1. 阅读完整有序旁白，判断语言、受众、内容、情绪与表达风格；通用类型读取逐幕逐段旁白。
2. 运行 `uv run m2v voices --json`，其他语言通过 `--locale <区域>` 或 `--locale all` 查询。查询失败就明确报告并修复连接，不虚构候选、不静默使用晓晓。结合服务返回的 categories/personalities 与内容选择；不按性别硬编码，不预先统一指定某一种声音。
3. 写入 `project.json` 的 `tts.voice` 和 `tts.selection`（mode、rationale、narrationSha256），填写结合具体旁白的理由。摘要使用共享 `m2v.engine.tts.narration_digest(texts)`，`texts` 为播放顺序中的自身旁白数组：通用类型逐幕逐段收集 `text`。忽略空白段，保留其余字符串原文与分段边界。
4. 保留已有语速、停顿设置。继续 prepare、按需片段检查与 render；音色选择与声音复核记录基于旁白文本、服务元数据和自动信号检查，不要求试听。

旁白变化必须重新判断，可保留同一音色并更新理由和摘要；画面变化不要求重选。用户手动修改作品音色时移除原助手 `selection`；`prepare --voice` 仅覆盖本次，并且不沿用助手理由。只有 CLI 覆盖语速时仍需有效助手选择。有自身旁白但未明确音色时 prepare 会阻断，不能靠重新渲染自动换声。字段、实际参数溯源和迁移见[配音契约](references/voice-and-rhythm.md#配音音色与语速)。

## 通用作品编排原则

制作必须执行[节奏、美术、声音与制作阶段](references/creative-production.md)：创作目标、两个美术方向、四张关键画面、整片动态粗预演、风险样片、分层精修、阶段条件和改动回归。文案、节奏、连续性、审美、声音及技术分别复核。三类作品共用审美原则并按类型检查：general 完整执行镜头叙事与强度编排；金融和住宅检查趋势、关键转折、常规图表及结尾，同时保留专用画幅、图表和声音契约。粗预演不代替正式候选的全片验收。

先把核心体验写成可观察验收条目；内容、运动与实测配音共同调整预算。按[自主视觉复核](references/visual-review-rubric.md)检查整段运动及交界，已知核心体验缺陷必须返工，不作为限制放行。任务包含流程改进与作品重制时，两项均完成才算交付。


通用类型只接受 v8 全画布代码场景：每一幕声明唯一 `id`、`template: "code"`、`content.entry`
（作品 `scenes/` 下的 TSX）与可选 `content.props`，并声明旁白数组（可以没有旁白，此时用
`durationFrames` 声明镜头长度）。`input.kind` 为 `article` 时绑定源文，为 `topic` 时只声明
`input.topic` 并由逐幕 `keywords` 驱动可选图库检索。

制作顺序是**先设计再动手**：确定发布语境与画幅（默认抖音、1920×1080 横屏、60 fps，显式要求优先；所有画幅均默认面向手机播放）→ 在作品 `DESIGN.md` 写下参考依据、
视觉隐喻、字体配色、开场/核心/普通信息镜头/结尾四处代表构图、镜头承接与声音意图 → 做四张关键画面与完整动态粗预演 →
优先验证风险运镜和声音样片 → 关闭必改项后再扩展精制全片。作品代码控制整张画布，必须自己画满不透明背景，并让重要文字与主体
避让 `subtitleSafeArea`；共享字幕是白字配不透明深色底板，独立于作品配色。

先自主搜索参考，再做覆盖开场、核心难点、结尾与主要风险的代表片段。静帧、全片高密度时间标注帧序列、运动/构图量测和自动音频候选分别检查；必改项关闭后再扩展全片，最终文件执行全片帧序列与自动音频复核。记录准备指纹、文件摘要、时间码、修改与复查；必要图像或自动检测缺失则报告未完成；不要求播放视频或试听音色，按替代证据复核并披露采样间运动与主观听感的覆盖限制。记录不作为 CLI 导出门禁，所有阶段均无需用户确认。具体模板与判断规则见[自主视觉复核](references/visual-review-rubric.md)。

动画由 `segmentWindows` 与录制时钟驱动，画面随真实口播推进；视频与图片用 `useMediaAsset(id)`
按素材 ID 取用，比例不受画幅限制，裁切与摆位由作品决定；视频要等到可播放后再 `ready()`，
素材原声不进入母版。素材只能来自 `assets/media/` 中已导入并留证的内容寻址文件。音效用顶层
`soundtrack` 按 `sceneId`/`segmentId`/`offsetMs` 定位，可用内置提示音或本地素材。默认根据旁白
原文生成字幕并烧录到预演和正式成片，无需额外开关，不得仅交付外置字幕；无讲话的停顿及阅读尾段
不显示字幕。每段实际 TTS 决定时间，无旁白镜头按声明帧数或目标剩余时长分配，完整成片含阅读停留
与淡化不超过 600 秒。

浏览器量测只覆盖共享字幕的安全区、换行与可见性；作品正文在录制的片段里，系统不声称能自动
识别其中的全部正文或主体遮挡——那部分由全片时间标注帧序列与屏幕量测补足。详见
[通用作品创作](references/article-to-storyboard.md)、[分镜结构](references/storyboard-schema.md)、
[媒体素材与音效](references/article-media-and-sound.md)与[评审量表](references/visual-review-rubric.md)。

## 渲染与评审

- 材料、资产或实现变化后重新 prepare。prepare 只准备配音、时间轴和源码输入，不录制全片。
- preview 是可选片段检查，默认前十秒，短作品最多全片减一帧。支持 `--start-seconds` / `--end-seconds` 或 `--limit-frames`，禁止覆盖全片；旧 samples / rehearsal 别名已移除。
- keyframes 原生采集代表静帧；lookdev 按需生成静帧与样片，二者不先录制全片。状态动画从零推进，只截图所需帧；正式生成复用已录区间并补齐缺口。
- render 不要求预演。完整候选写入 candidates 并绑定输入、实现、参数和 SHA-256 后执行字幕、媒体及类型检查；有效候选重复执行直接复用，验收失败或交付失败也只重试检查和复制，禁止再次完整编码。
- 全片技术验收通过后复制交付同一文件并保存溯源；失败保留候选和旧有效交付。status 显示 prepared / candidate-pending / validation-failed / ready / delivery-failed / delivered，不将技术通过解释为审美完成。
- 人工画面评审可选，review-template / review 绑定当前候选 key、preparedFingerprint 和 sha256；旧预演记录不再生效。文章输入语义审查和金融自动探针保留。
- standard 与 cinematic 均无需用户确认。general 助手须复核最终文件全片帧序列及音频候选、关闭必改项，不能用成功导出代替制作完成。
- 成功交付后才清理旧视频及已知调试产物，保留当前候选与交付记录、准备媒体、准备/评审 JSON；general 还保留 visual-notes.md 及其引用证据。失败不清理，共享缓存不受影响，清理失败报告遗留路径。

测试和严格示例校验方式见仓库 README。测试、构建和输出参数应使用仓库配置与 `m2v --help`，不要调用旧的 Skill 脚本制作入口。

## 新增视频类型

只在两处落地：先在 `src/m2v/types/catalog.json` 登记类型身份（名称与一句话说明）、材料入口（材料名与默认文件名）、初始化模板与文档文案，再实现该类型的行为适配器（校验、准备、预演、渲染与可选的评审钩子）。统一入口不按类型名硬编码分发，作品契约也不维护类型白名单与材料映射；已实现但未在目录登记的类型会在渲染前失败。

上述类型表、README 的类型清单与项目规划的规划清单都由该目录生成。改动目录后运行 `python .agents/skills/material2video/scripts/sync_docs.py` 重新生成，用 `--check` 只比对不写入。
