---
name: material2video
description: 使用统一 m2v 制作入口创作金融时间序列、住宅时间序列、通用讲解视频。用于准备类型材料、编排、预演、评审、渲染与排查不一致问题。
---

# Material2Video（材料成片）制作 Skill

项目采用共享制作底座、独立视频类型、统一制作入口。发展顺序是先建设金融时间序列等专用视频，再沉淀多类型共用能力，完善通用混合媒体讲解视频。

开始制作前读取作品目录中的 `project.json`，确认类型，再按该类型参考材料组织内容。整体流程为材料审查 → 编排旁白 → 按文本和服务元数据选择音色并保存 → 校验与时间轴准备 → 按需检查生成与修改 → 全片生成一次 → 验收与复核 → 交付同一文件；无自身旁白时跳过选音。所有类型由 render 生成一次完整候选，自动验收后直接交付同一文件，CLI 不要求人工记录；助手须为所有作品复核手机观看下的可读性、观众可见文案与风格，并关闭必改项，general 另基于帧序列、量测与自动检测完成完整替代复核。所有制作阶段无需用户确认。全流程不要求播放视频、连续收听声音或试听音色；按作品类型使用静帧/时间标注帧序列、路径与画面量测、字幕和时间戳核对及自动音频信号分析等证据，并如实记录覆盖范围。文章原文语义审查保留。所有生成产物都是派生产物，不代替可编辑材料。

**所有作品默认面向手机观看**，但不因此强制竖屏；按作品选定的画幅与用户指定的设备方向设计和复核。每部作品只在片尾出现一份简短署名与版权说明，不在逐幕重复素材署名，也不在画面或字幕中出现仓库文件名、路径、制作文档或内部查阅指引。完整事实来源、作者和许可依据保存在作品材料中。多段落作品还须复核重复版式和信息推进；重复静态卡片或逐页文字板主导全片且没有信息、关系或体验推进时，作为必改项返工，不得以技术 QA 通过放行。

| 类型 | 创作指导 |
|---|---|
<!-- generated:type-catalog:start -->
| `financial-timeseries` | [金融时间序列视频](references/financial-timeseries-video.md)：核验行情口径、投资计算并通过完整候选自动验收。 |
| `general` | [作品视觉设计与制作流程](references/production-workflow.md)、[视觉创意导演方法](references/visual-creative-direction.md)、[分镜结构](references/storyboard-schema.md)、[媒体素材与音效](references/article-media-and-sound.md)、[代码场景契约](references/code-scene-runtime.md)：v8 全画布代码场景多幕讲解。 |
| `housing-timeseries` | 按 `series.json` 提供连续年度住宅销售额、面积、计算均价与来源口径；生成 1080×1920、60 fps 无声折线视频。 |
<!-- generated:type-catalog:end -->

通用类型使用 v8 storyboard.json：每一幕由本地 React `code` 场景承担时间轴和全画布合成，画幅默认为 1920×1080 横屏并支持显式 1080×1920 竖屏；具体画面服从已通过的视觉设计，可由场景绘制并组合按当前契约导入的图片、视频等素材。代码场景在检查或正式生成时按所需窗口逐帧录制并缓存，检查和正式生成按区间复用录制缓存；不支持旧模板、视觉主题、general-plan 编排或完整片段嵌入。

## 统一制作标准与循环创作

所有通用作品执行同一高质量流程，不再区分普通与电影级。`productionProfile` 和 `--profile` 已删除，旧声明明确拒绝。镜头分级仅控制采集资源；`look.profile` 是美术名字，不是制作档位。

**方案确定 → 粗片验证 → 精制修订 → 最终验收**。general 的方案确定阶段必须先完成独立目标关键帧、逐段盲审和全片并排检查；关键帧优先表达最终观感，技术可行性后置评估。通过的关键帧是后续实现的视觉合同。静态门通过后，动态表达先验证一个完整窗口原型，通过后扩展全片。阶段与完成条件以[统一制作流程](references/production-workflow.md)为唯一入口。
未收到足以执行的用户详细方案时，每轮默认3个不同叙事方案，允许全部淘汰后再出下一轮；各案比较核心构思、揭示顺序、代表段落、题材关联与主要风险，先验证核心体验再投入全片精制。若用户方案已明确核心表达、关键事件或画面顺序及主要约束，足以开始设计或试制，则直接采用，不强制补齐叙事候选或两个美术方向，也不重新论证核心创意；次要细节最小补全，表现、事实、技术与交付仍按流程验证。详见[用户详细方案直接采用](references/production-workflow.md#用户详细方案直接采用)。同一问题连续两轮无改善必须换方法或方案，不设总轮数上限，不为凑轮次重复制作。

制作过程中发现任何环节可优化（流程编排、命令与工具、校验与技术验证、审美判断与视觉规范、评审与记录方式、文档与示例等），都应当在本次制作中一并改进并验证，能优化的都优化，不要只记录留待以后；优化须与当前契约一致，并保证其他类型与示例不回归，超出本轮范围的按 AGENTS.md 的「制作视频时同步优化流程」登记。

评审区分实际缺陷、创意风险、审美偏好与证据不足；去文字、静音、缩略图和运动密度按[诊断适用性](references/visual-review-rubric.md#诊断测试与适用性)使用，不按静止时长、母题像素差或形式标签直接否决。事实、许可、技术与关键可读性仍严格检查，作者意图不能豁免核心失败。

返工先检查信息推进，重复与等待优先剪辑；连续两轮无改善必须匿名独立比较剪辑候选并按原条件复查。技术交付与制作复核分别报告，空白评审不能支持制作完成。详见[返工升级](references/creative-production.md#信息推进与返工升级)、[问题闭环](references/visual-review-rubric.md#版本与问题闭环)及[完成边界](references/director-review-and-edit.md#完成边界)。

详见[循环创作流程](references/creative-production.md)及[统一制作与质量工具](references/cinematic-video.md)。所有阶段由助手自主推进，无新增用户确认、运行时创作字段、审美评分或人工导出门禁。设计须安排全片强弱与文字／运动／静止／声音分工，每轮精修主动强化有效表达；重要返工比较修复收益和表达损失。关键画面、核心动态试制与最终完整复核必做；二维/三维、镜头数量与时长、配乐、后期、采样尺度按内容决定。无声作品保持无声；有声成片目标−14 LUFS / −1 dBTP。

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
uv run m2v lookdev --project videos/general/<slug>  # 代表静帧与风险样片，结论记入 visual-notes.md
uv run m2v qa --project videos/general/<slug>       # 技术 QA，输出 outputs/qa.json
uv run m2v assets audit --project videos/general/<slug>  # 资产质量与许可审计
# 仅在用户明确要求复用某条参考作品音频时：
uv run m2v ref audio <参考目录> --project videos/general/<slug> --user-authorized "<授权说明>"
```

参考素材默认只用于分析、比对与制作参考，渲染链路不直接读取 `refs/`。`m2v ref fetch/verify` 负责获取与复核；用户明确要求复用单条参考作品音频时，`ref audio` 才把音轨提取到作品 `assets/audio/` 并写 provenance（来源、摘要、授权原文、许可状态），成片只保留一处署名。无旁白作品只用 `soundtrack.music` 作全片音源时，必须显式写 `gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`，并按 `ceil(samples × fps / sampleRate)` 对齐每幕 `durationFrames`。细节见[文章媒体与音效](references/article-media-and-sound.md#复用参考音轨受控例外)。

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

核心图形高潮按[视觉力量设计](references/visual-impact-design.md)分开设计事件、力量、动态导演与实现；先比较同一事件的不同视觉机制、代表画面与完整粗样，再扩展精制。理解与表现分别验收，沿用四阶段、隔离评审与唯一问题表，不新增评分或导出门禁。

旧片修复先按[重制启动](references/production-workflow.md#重制启动)核验用户约束、历史实现与重入阶段，并保留比较基线；核心事件按[最小动态证据](references/visual-review-rubric.md#核心事件的最小动态证据)取证。重制须分别验证理解、表现与相对改善，最终按[完成边界](references/director-review-and-edit.md#完成边界)同摘要汇总技术与制作结果。

制作必须执行[统一制作流程](references/production-workflow.md)和[关键帧验证门](references/visual-creative-direction.md#关键帧美术验证门)：general 每个核心段落均制作一张独立目标关键帧，并逐张盲审、按时间顺序并排检查。关键帧优先呈现最终观感，不受技术可行性预先限制；静态门通过后再单独评估实现。通过的关键帧是后续实现的视觉合同。参考图和关键帧分别放在 `outputs/design/references/`、`outputs/design/keyframes/`，索引与来源记录在唯一的 `DESIGN.md`。静态门未通过不得动画；动态原型通过后才制作全片粗预演。金融和住宅继续适用专用流程。

确定母题或替代载体后、逐场构图与关键画面前，按[视觉事件设计](references/visual-creative-direction.md#视觉事件设计)构造核心事件，并为关键表达镜头在 `DESIGN.md` 写导演卡：说明观众按什么顺序看到、何时获得新信息；普通镜头简写目标、事件和镜头/注意力意图，核心高潮另补视觉力量。用现有 storyboard scene/shot ID、target 与帧窗映射，先验证完整事件窗口粗样再扩展全片；不增加运行时字段、不强制反转。模板见[导演设计](references/visual-creative-direction.md#导演设计观众按什么顺序看到)。

通用作品在选定叙事方案后、逐场设计与关键画面前，按[视觉创意导演方法](references/visual-creative-direction.md)在 `DESIGN.md` 完成七段式视觉创意方案与十项自我检查：核心表达、核心视觉母题、整体视觉风格、分镜设计、视觉高潮、结尾视觉揭示、禁止项。核心表达写变化／冲突／规律而非复述标题；母题写成「把 ___ 设计成 ___」且载体可变化；抽象观点必须转为可见变化；镜头按行为而非页面设计；转场优先形态变换或连续承接。载体来源先定整体政策（档案证据型／解释型／混合），再在逐场设计表落实实例；不得用图库冒充真实事件或人物，不得用代码伪造证据。七项均为必答问题，不适用时写明原因与替代做法；不新增阶段、运行时字段或 CLI 门禁，不强制重复母题、反转或传统高潮。

用户明确要求借鉴某条参考作品的风格时，必须按[参考风格契约](references/reference-style.md)先把借鉴拆到视觉层：分层选定采用项、列出不借清单、量取八项指标并做画幅转译，在 `outputs/style-reference.md` 留下参考值、目标值、实际值与差值。只写「气质一致」、只复用配色或只复用音频都不算借鉴完成。进入全片前先做三张风格基准与 2 秒动效样片，由独立冷审判断是否同族；参考画面仍不得进入成片。

冷观众、文案复述、适用时的叙事候选淘汰与美术方向比较、风格同族、逐场观察复述、两次导演审查，以及传播反面依据、可见文案核对、手机可读性、节奏判断、风格八项指标量取，一律按[独立子代理评审](references/subagent-review.md)执行。用户已提供可执行设计时，独立评审检查设计的呈现与执行效果，不重新选择已确定的核心创意。评审优先由新建上下文子代理执行并只投喂评审包；环境不具备时降级为角色分离自审，标注并披露，不得据此把评审项标为已关闭或声称「像作品」。

每场和内部镜头按[精简设计表](references/scene-design-and-acceptance.md)覆盖，共享规则只写一次。粗片审查合并逐场观察、信息推进和首次导演审查；最终由理解结构节奏与视觉文案两名隔离代理检查。核心表达在扩展全片前盲测，重要返工首次匿名比较，实质分歧交新代理先盲看再核对原条件，职责以[独立评审](references/subagent-review.md)为准。

仅维护设计、visual-notes 阶段汇总与唯一问题表、独立原始报告三类记录；传播表现并入最终汇总。核心问题逐项关闭，不以总体交付结论替代；未变观察可附来源和依赖证明引用，当前最终文件仍完整检查。

短视频制作前明确发布语境、目标受众、核心传播重点及大致时长；按受众理解成本安排内容取舍，不把技术字数/时长合规当成传播效果通过。制作前、制作中与制作后均把降低前两秒流失作为定性审美因素：开场尽早给出可辨认的主题、主体或有意义动作，避免空泛铺垫；复核前两秒在手机尺寸下能否快速建立主题和继续观看的理由。没有真实平台数据时不计算或声称“2秒跳出率”，不设代理分数或机器门禁。中文受众作品以中文专名和贡献说明为主，英文缩写不能成为理解前提。

标题与画面文案先做自然中文与抖音受众知识水平检查：用日常中文念一遍，避免“十大 XX 事件”式名词堆叠和“XX 权益”这类公文式名词；每项事件补一句“发生了什么”的平实背景，禁止只给术语；假设观众第一次接触主题，看完能复述“谁做了什么、新增什么权利”。三关未过不得进入精制，逐场复述结果写入 `outputs/visual-notes.md`；详细规则见[节奏、美术、声音与制作阶段](references/creative-production.md#标题与文案自然中文与抖音受众知识水平)。

先把核心体验写成可观察验收条目，并在制作前声明手机显示尺寸、关键可见事件及主体辨认、动作理解、关系理解中的适用目标；各目标不能互相替代，无动作表达不强制添加动作。立即理解与延迟揭示分别声明，按完整表达窗口复核。问题记录沿用原验收条件，状态分为未解决、待复查、已关闭、接受保留：只有已关闭计入解决，接受保留必须记录剩余影响，核心理解问题不得降级放行。按[自主视觉复核](references/visual-review-rubric.md)检查整段运动及交界，已知核心体验缺陷必须返工，不作为限制放行。素材、运动与实测配音共同调整预算；`m2v qa` 的 `inspection.rhythm` 提供客观节奏测量，只作证据，不设审美阈值。最终候选必须逐页实际查看全片时间标注帧序列并记录页码与时间范围，生成采样不等于实际检查。任务包含流程改进与作品重制时，两项均完成才算交付。


通用类型只接受 v8 全画布代码场景作为时间轴与合成容器：每一幕声明唯一 `id`、`template: "code"`、`content.entry`
（作品 `scenes/` 下的 TSX）与可选 `content.props`，并声明旁白数组（可以没有旁白，此时用
`durationFrames` 声明镜头长度）。`input.kind` 为 `article` 时绑定源文，为 `topic` 时只声明
`input.topic` 并由逐幕 `keywords` 驱动可选图库检索。

场景负责完整画布合成，但不要求所有视觉内容都由程序化代码生成；画面实现服从已通过的视觉设计，并受当前代码场景及素材导入契约约束。

制作顺序是**先设计再动手**：确定发布语境与画幅（默认抖音、1920×1080 横屏、默认30 fps（可显式60 fps），显式要求优先；所有画幅均默认面向手机播放）→ 在作品 `DESIGN.md` 完成
[立意六项](references/production-workflow.md#立意六项方案确定前)（一句话命题、核心体验、表达载体、揭示与记忆、可验算骨架、重点投入）→
若用户已提供足以执行的详细设计，直接将方案映射到六项并采用，不进入叙事／美术多方案选案；否则提出并选定三个叙事候选 → 完成[视觉创意七段式](references/visual-creative-direction.md)（核心表达、核心视觉母题、整体视觉风格、分镜设计、视觉高潮、结尾视觉揭示、禁止项；例外留痕），确定载体后构造核心视觉事件，为关键表达镜头完成导演卡，并为核心高潮补充视觉力量 →
按信息单元及观察／情绪用途安排全片预算 → 定美术规则并独立制作每个核心段落的最终目标关键帧 → 逐张盲审并全片并排检查 → 静态门通过后单独评估实现可行性 → 对动态表达先验证最高风险事件的完整窗口 → 制作覆盖全片的粗预演 → 关闭必改项后再扩展精制全片。关键帧既是设计证据也是视觉合同；规则详见[关键帧验证门](references/visual-creative-direction.md#关键帧美术验证门)。作品代码控制整张画布，必须自己画满不透明背景，并让重要文字与主体
避让 `subtitleSafeArea`；共享字幕是白字配不透明深色底板，独立于作品配色。

先自主搜索参考，再做覆盖开场、核心难点、结尾与主要风险的代表片段。静帧、全片高密度时间标注帧序列、运动/构图量测和自动音频候选分别检查；必改项关闭后再扩展全片，最终文件执行全片帧序列与自动音频复核。记录准备指纹、文件摘要、时间码、修改与复查；必要图像或自动检测缺失则报告未完成；不要求播放视频或试听音色，按替代证据复核并披露采样间运动与主观听感的覆盖限制。记录不作为 CLI 导出门禁，所有阶段均无需用户确认。具体模板与判断规则见[自主视觉复核](references/visual-review-rubric.md)。

动画由 `segmentWindows` 与录制时钟驱动，画面随真实口播推进；视频与图片用 `useMediaAsset(id)`
按素材 ID 取用，比例不受画幅限制，裁切与摆位由作品决定；视频要等到可播放后再 `ready()`，
素材原声不进入母版。素材只能来自 `assets/media/` 中已导入并留证的内容寻址文件。音效用顶层
`soundtrack` 按 `sceneId`/`segmentId`/`offsetMs` 定位，可用内置提示音或本地素材。默认根据旁白
原文生成字幕并烧录到预演和正式成片，无需额外开关，不得仅交付外置字幕；无讲话的停顿及阅读尾段
不显示字幕。每段实际 TTS 决定时间，无旁白镜头按声明帧数或目标剩余时长分配，完整成片含阅读停留
与淡化不超过 600 秒。

共享动效原语（数字滚动、数据曲线与柱状生长、列表滚屏、主体状态插值、签名粒子）见[代码场景契约](references/code-scene-runtime.md#共享动效原语)：以 `progress` 为唯一时间输入、不内置视觉主题，不得用于关闭信息推进、母题可信度或版式重复问题。

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
- `m2v review` 仍是可选工具，review-template / review 绑定当前候选 key、preparedFingerprint 和 sha256；旧预演记录不再生效。文章输入语义审查和金融自动探针保留。可选工具不等于制作复核可省：A/B 级评审按[独立子代理评审](references/subagent-review.md)执行，缺有效记录视为对应阶段未完成。
- 统一流程无需用户确认。general 助手须逐页复核最终文件全片时间标注帧序列及音频候选、关闭必改项，不能用成功导出代替制作完成；逐页检查需记录实际页码与时间范围，未覆盖部分保持未完成。逐场验收与最终传播评估分别见[逐场设计与独立验收](references/scene-design-and-acceptance.md)和[传播表现评估](references/reach-potential.md)，结论并入 `outputs/visual-notes.md`，直接链接原始报告与证据。两次导演审查的时点与模板见[全片导演审查与剪辑重组](references/director-review-and-edit.md)。
- 成功交付后才清理旧视频及已知调试产物；清理前按[基线保留](references/production-workflow.md#基线保留)排除旧版比较文件及引用证据，保留当前候选与交付记录、准备媒体、准备/评审 JSON；general 还保留 visual-notes.md 及其引用证据。失败不清理，共享缓存不受影响，清理失败报告遗留路径。

测试和严格示例校验方式见仓库 README。测试、构建和输出参数应使用仓库配置与 `m2v --help`，不要调用旧的 Skill 脚本制作入口。

## 新增视频类型

只在两处落地：先在 `src/m2v/types/catalog.json` 登记类型身份（名称与一句话说明）、材料入口（材料名与默认文件名）、初始化模板与文档文案，再实现该类型的行为适配器（校验、准备、预演、渲染与可选的评审钩子）。统一入口不按类型名硬编码分发，作品契约也不维护类型白名单与材料映射；已实现但未在目录登记的类型会在渲染前失败。

上述类型表、README 的类型清单与项目规划的规划清单都由该目录生成。改动目录后运行 `python .agents/skills/material2video/scripts/sync_docs.py` 重新生成，用 `--check` 只比对不写入。
