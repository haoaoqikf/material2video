# Material2Video（材料成片）

Material2Video 是短视频制作指导与工具链。新建作品使用 `project.json` v3 和分镜 v9，拥有自己的运行源码、依赖锁、资源恢复与 `SceneFilm` 合成；主项目通过本地入口委托校验、准备、片段检查与完整导出。画面可由代码生成，也可使用登记过的真实媒体。架构边界见 [ARCHITECTURE.md](ARCHITECTURE.md)，操作流程见 [material2video Skill](.agents/skills/material2video/SKILL.md)。

四部随附示例均为独立工程，运行源码、依赖锁、字体与资源恢复、预览、采集和导出都归作品。`lookdev`、时间线与 QA 读取本地产物。主项目提供制作指导、初始化、可选组件参考和制作管理。[`web/`](web/README.md) 集中维护现行参考源码与测试夹具。

## 当前视频类型

<!-- generated:type-catalog:start -->
- `text-motion`：代码生成文字和图形，侧重排版与动效
- `data-evolution`：结构化数据的可视化变化
- `principle-metaphor`：程序生成物体和场景，说明抽象原理
- `spatial-3d`：三维模型和场景的空间渲染
- `documentary-edit`：真实视频、照片与档案的叙事剪辑
<!-- generated:type-catalog:end -->

地图轨迹与情境叙事是可选表现手法，不是独立类型。没有 `general`、专项类型、类别层或风格注册表。作品默认生成到 `videos/<类型>/<作品名>/`；随附示例放在 [`examples/`](examples/README.md)。

口播配实拍或外部素材使用 `documentary-edit`。逐段匹配文案里的对象、动作、过程与情绪，通用画面优先查 Pexels 和 Pixabay，按缺口扩展到其他公开来源。具体事实优先核对原件，选材见[制作指导](.agents/skills/material2video/references/visual-material-selection.md#观点旁白与意境素材)。适用口播的固定「真人播客女」音色见[配音指南](.agents/skills/material2video/references/voice-and-rhythm.md#口播作品的固定默认音色)。

纪实口播默认使用本地 `kokoro`，其他类型默认使用联网的 `edge-tts`。纪实口播可按文案选择合适的 Kokoro 中文音色，例如 `zf_027` 这类本地音色，并按作品内 `models/registry.json` 恢复固定 revision 的模型。需要克隆参考音色时，作品可声明 `qwen3-tts`，用 `clone_<slug>` 指作品内参考音频与参考文本，按 `models/qwen3-tts/registry.json` 恢复 Qwen3-TTS 主模型与 stable-ts 对齐模型。Qwen3-TTS 使用 FFmpeg `atempo` 做保音高变速，再对实际音频强制对齐。三种后端都输出真实词边界，进入同一字幕断句与停顿整形链路。Kokoro 与 Qwen3-TTS 目前只接受纯中文旁白，数字与拉丁字母会在合成前失败；Qwen3-TTS 参考音色的来源与用户授权必须留证，不能从模型仓库恢复参考音频。

字幕支持中文主行 + 英文次行上下排列；带字幕的五类作品默认从实绘背景选择浅字或深字和自适应柔光，`frames.json` 保持字体、字号和画幅参数的统一入口。既有独立工程需采用更新后的本地运行时再生成。画面标注和片尾编排见[素材采用与署名](.agents/skills/material2video/references/material-sourcing.md#5-采用政策与署名)。人物不设默认限制；素材与使用一律从宽，只有权利人明确禁止当前用途才不用，平台条款不算禁止。

三维示例[太阳系之旅](examples/spatial-3d/solar-system-journey/README.md)采用120秒、十五站的连续旅程，以实测旁白预算生成差异化镜头，突出地月关系、土星显环与外层尺度。示例的媒体和原创声音按固定配方恢复，当前制作与验收证据见其[验证记录](examples/spatial-3d/solar-system-journey/VERIFICATION.md)。

## 安装与快速开始

```powershell
uv sync
uv run m2v types
uv run m2v init --type text-motion --project demo
Push-Location videos/text-motion/demo
pnpm install --frozen-lockfile --ignore-workspace
uv sync --frozen
pnpm run setup --download --install-browser
pnpm run render
Pop-Location
uv run m2v validate --project videos/text-motion/demo
uv run m2v prepare --project videos/text-motion/demo
uv run m2v preview --project videos/text-motion/demo --limit-frames 30
```

`init` 生成完整的三秒主题工程，五类默认都不预装三维、图表或业务来源模块；正式创作时改写分镜和 `scenes/opening.tsx`。使用 Kokoro 的作品需在自身依赖中安装 `kokoro` 与 `misaki[zh]`（模板提供 `kokoro` extra），并用 `python models/fetch.py --download --voice <音色>` 恢复模型。使用 Qwen3-TTS 的作品需安装 `qwen-tts` 与 `stable-ts`（模板提供 `qwen3-tts` extra），并用 `python models/qwen3-tts/fetch.py --download --voice <音色>` 恢复主模型与对齐模型；参考音色必须随作品保存并登记摘要。本地命令、环境和恢复前提见[独立工程说明](templates/standalone/README.md)。生成后可以直接在作品目录运行，也可由 m2v 委托；默认 `videos/<类型>/<作品名>/` 只是生成位置，显式路径和后续搬移不要求该目录层级。`preview` 只检查片段；最终成片与审核按[媒体评审契约](.agents/skills/material2video/references/review-contract.md)执行。`render --jobs N` 可并行，默认 2；内存紧张时改为 1，并行只影响耗时，不改变帧序与成片契约。默认内容位置可通过 `--content-root` 或 `M2V_CONTENT_ROOT` 设置。

## 命令

运行 `uv run m2v --help` 查看入口与参数。类型目录通过 `m2v types` 查询；制作辅助操作使用 `m2v author`，金融来源计划使用 `m2v data financial-plan`。旧命令不保留别名。

## 网页原生设计样品

`m2v sample capture` 委托作品本地构建与采集，不需要完整分镜或配音。原生样品 v2 默认 static，只采集可复现网页和关键帧，不编码视频；motion 另生成完整过程。源码、实际依赖、字体、登记媒体、参数及产物均绑定，变化后重新采集。

试制及正式关键帧均独立盲审并做同轮目标对照。试制验证已成立的艺术方向，正式验证所选风格的成片完成度。对照按已登记的画面职责使用实际参考。研究试制的完整动态样片由总代理用有序帧、完整解码及适用信号核验。正式关键片段按审核策略做独立过程对照，核心时间机制需要时可登记正式过程盲审。总代理实际查看、初筛、核对报告并负责最终选案。[审核政策](.agents/skills/material2video/references/review-contract.md)

```powershell
uv run m2v sample capture --project <作品> --entry scenes/core.tsx --kind static --duration-seconds 3 --frame 30
uv run m2v sample serve --project <作品> --id <采集ID>
uv run m2v sample review --project <作品> --id <采集ID> --purpose keyframe --targets <目标.json>
uv run m2v review import --project <作品> --file <真实盲报告.json>
uv run m2v review compare --project <作品> --blind-id <盲报告ID>
uv run m2v review import --project <作品> --file <真实对照报告.json>
uv run m2v sample deliver --project <作品> --id <采集ID> --blind-id <盲报告ID> --comparison-id <对照报告ID> --basis <具体选案依据>
```

sample review 为同源关键帧自动派生来源、窗口、显示尺寸和只读隔离包，compare 根据封存目标生成同轮对照。静态和动态样品使用同一套关键帧报告参数交付。交付直接复制已有媒体。Windows 发布后恢复继承权限。

关键帧在正常尺寸核对阶段艺术效果，在手机等小屏核对核心形象、关键关系和必要信息。抽象细节只在小屏减弱时可随通过记录，见[不同观看尺寸的职责](.agents/skills/material2video/references/visual-review-rubric.md#不同观看尺寸的职责)。

同轮对照回传可直接观察的复查问题。主代理用原尺寸的前后实绘回答同一个问题，凭实际效果决定是否复送，见[返工交接](.agents/skills/material2video/references/production-workflow.md#返工交接)。

固定保留 RESEARCH.md、DESIGN.md 和每个正式场景文档，默认四问、复杂机制按需深化。成熟外部组件、模型、材质、Shader 和开源方案优先采用与改造，只自研必要缺口。预演、粗片和精制合并到问题驱动制作循环，见[研究与试制](.agents/skills/material2video/references/stage-research.md)与[原生样品](.agents/skills/material2video/references/design-samples.md)。试制关键帧按[阶段标准](.agents/skills/material2video/references/visual-review-rubric.md#试制关键帧的通过标准)判断。同一个问题连续两次修改无明显改善时，按[暂停送审规则](.agents/skills/material2video/references/production-workflow.md#试制暂停送审与重新选案)先内部重选。AI 图只作内部构思或参考。

采集使用完整 Chromium 的无头模式；`uv run playwright install chromium` 会安装所需浏览器，仅安装 headless shell 不足以在 Windows 加载 WebGPU 的 DXC。代码场景可通过 `waitForFrame(PromiseLike)` 登记异步绘制，初始就绪和每帧/子帧在工作及合成完成后才放行；拒绝或超时仍失败，纯时间仍须实际验证。静态代码场景可在作品内采用路径追踪、OIDN 去噪等可选能力；共享层不登记这类依赖，采用时由作品把实际依赖、补丁、权重来源与许可写进自己的工程和锁文件，固定种子、样本与分块，在 GPU 与本地权重就绪后采集，并逐场核验确定性，不据此宣称动态已验证；模型权重由作品登记来源、许可和恢复摘要，不入库。


## 材料与画面

`project.json` 只接受以下结构；`output` 可声明宽高、30/60 fps、声音和字幕配置：

```json
{"schemaVersion":3,"id":"demo","type":"data-evolution","materials":{"storyboard":"storyboard.json"},"runtime":{"version":1,"command":["uv","run","--frozen","python","scripts/video.py"]},"output":{"width":1920,"height":1080,"fps":30,"audio":"optional"}}
```

分镜必须同时声明 `version: 9` 和 `schemaVersion: 9`。每幕使用 `template: "code"`，通过 `content.entry` 指向作品内 TSX。新工程从本地 `src/code-scene/context` 导入时间接口，组件和第三方依赖由作品显式采用，不解析 `m2v/*`。分镜字段见[分镜契约](.agents/skills/material2video/references/storyboard-schema.md)；存量画面参考见[代码场景运行时](.agents/skills/material2video/references/code-scene-runtime.md)。原文、主题、字幕、媒体、声音与事件仍使用分镜 v9。

分镜顶层 `sources` 把来源 ID 绑定到作品内文件，幕内 `content.sourceIds` 选择来源。主项目仍保留 `financial-series`、`construction`、`vehicle-model` 的材料校验与计算辅助；新工程按需携带所采用的准备模块、数据快照及绘制实现，基础模板缺模块时明确报错，不回退主项目SDK。金融计划辅助入口为 `m2v data financial-plan --project <作品目录> [--duration-seconds N]`，要求分镜恰好声明一个金融来源。

五类创作都从统一阶段指南进入；金融行情、构件与车辆专项指南按实际绑定的来源展开。固定数学模型的数据演化无需金融行情计划。旧类型作品重制时按当前契约编排到新的类型目录，原目录及历史证据保留，见[修订入口](.agents/skills/material2video/references/video-revision.md)。

创作辅助命令改为 `m2v author`：源文审查、候选稿、素材导入和音效操作分别见 `m2v author --help` 与[媒体和声音契约](.agents/skills/material2video/references/article-media-and-sound.md)。外部画面素材使用 `assets/media-sources.json` 留证；`m2v assets report`、`contact-sheet`、`audit` 用于台账和技术检查。字体二进制按 [`fonts/registry.json`](fonts/registry.json) 恢复并校验，不纳入 Git。

Pexels 是可用的图片和视频素材来源。选定素材后，把公开媒体直链填入 `mediaUrl`，由 `m2v author assets import` 下载并留证，无需 API Key。操作见 [Pexels 导入示例](.agents/skills/material2video/references/material-sourcing.md#pexels-公开媒体直链)。

`m2v author assets` 另有 discover / fetch / index / find / preview / select / library / models / doctor 九个工作流，覆盖无分镜发现、受控公开/平台/本地获取、字幕/转录/OCR/镜头/文本/视觉索引、中文检索与候选预览、精裁选择和作品内凭据。索引/查找离线运行，模型必须显式 `models prepare`；完整教程与能力边界见[素材工作层](.agents/skills/material2video/references/material-sourcing.md#完整工作层发现获取索引检索预览选择)。`search`/`import` 行为保持不变，Pexels API 仍停用。

素材库支持全时间轴预算采样、可继续的流式增量扫描、来源标题/描述的跨语言语义检索及背景负例筛选；同次请求复用查询编码。`library annotate/list/similar/browse` 提供标签、收藏、主题集合、已有视觉索引的相似镜头建议和显式多库本地浏览。相似建议不合并来源或删除文件，动作与身份仍需观察。

旧类型名、`project.style`、project v1/v2、分镜 v8 及旧准备记录明确拒绝。升级后的材料需重新编排并重新准备；没有兼容入口或迁移命令，旧实现从 Git 历史追溯。

## 示例与文档

《复利 40 年》用 38.7 秒回答同一笔钱前、后各二十年的利息为何相差 6.73 倍。四幕展示同一账户的起点、利息再投入、年度柱从零线生长及两组归塔。原克隆音色从本地参考 WAV 和音色档案恢复。详见[作品说明](examples/data-evolution/compound-after-20/README.md)。

四部示例均为独立工程，可复制到仓库外按各自 README 恢复、预览与完整导出。需要下载的示例媒体按各自 `assets/recipe.json` 恢复，生成媒体与 `outputs/` 不入库。当前示例和恢复入口见[随附示例](examples/README.md)。

- [项目规划](docs/PROJECT_PLAN.md)：未来路线与未实现能力。
- [制作 Skill](.agents/skills/material2video/SKILL.md)：阶段入口、材料、画面、声音与评审规则。
- [三阶段制作](.agents/skills/material2video/SKILL.md)：研究与创意试制 → 正式设计 → 制作与验收。先比较同一关键场景的不同设计，按判断需要补足精度，再集中打磨；分别判断候选优劣与能否作为后续标准，允许全部淘汰。整体品质成立且在拟用链路重现后展开全片，具体选案与收敛见[研究与试制](.agents/skills/material2video/references/stage-research.md)。样片适用范围及整片复核见[审核策略](.agents/skills/material2video/references/review-contract.md)。
- [全片与场景设计](.agents/skills/material2video/references/scene-design.md)：总设计先组织叙事、共用视听规则和场景索引。逐场以既有 scene.id 回答四问，按需用对象、节拍、单体变化和光影模板展开，并区分预期和实绘结果。指南附复杂和简明的实作示例。分镜和代码维护执行参数，脚本支持全片或局部对应检查。
- [案例调研](.agents/skills/material2video/references/reference-video-analysis.md)统一在全片开展，形成可验证的镜头方案。[组件调研](.agents/skills/material2video/references/visual-components.md#成熟组件调研)分全片和场景两层，先查内部实现，按缺口查外部。全片案例、核心效果与共用选型归 RESEARCH.md，局部组件选型和验证归[场景文档](.agents/skills/material2video/references/scene-design.md#分工与对应)。
- [架构说明](ARCHITECTURE.md)：代码分层与依赖方向。
- [OpenSpec 规格](openspec/specs/)：已实现行为。
- [项目协作约定](AGENTS.md)：验证、提交与资产管理。

日常验证只跑受影响的测试与真实媒体节点；正式全量回归仅在用户明确要求或人工发布验证时执行。文档投影可用 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` 检查。

### 媒体评审

`m2v review start|pack|compare|import|timeline|retarget|reuse|scope|confirm-evidence` 统一周期、隔离包、报告和证据复用。评审 v4 声明 keyframe 或 process 用途；报告顶层及每项明确 adoption=adopt/reject，仅 pass 可以采用。旧评审通过不授权新版本，历史与未解决必改保留。

status 只读展示正式关键帧、适用的关键样片窗口、当前技术 QA、整片证据复核（`wholeFilmReview`）和待解决问题。超过 30 秒的作品须登记并通过全部必审样片窗口。技术候选可以提前生成。研究、试制和验收均无需播放观看或试听；整片复核基于当前候选的抽帧、时间轴和适用音频信号登记。

目标参考与中性条件绑定，盲看后不能暗换；真实用户改变已失败目标时使用 retarget 保留原指令及旧失败，再完成对应独立复查。完整字节及观察条件相同的 trial 双评可显式 reuse，当前技术来源仍核验。具体格式、调用与失效处理按需读[工具协议](.agents/skills/material2video/references/review-protocol.md)，隔离执行见[独立子代理](.agents/skills/material2video/references/subagent-review.md)。

导出后清理会保护当前周期评审包仍绑定的预览源媒体和目标媒体；源文件仍参与证据摘要校验，无引用的旧预览继续清理。无法确认引用时报告并跳过清理。

Windows 基线读写支持深层评审记录路径，保留原相对路径格式，无需修改系统长路径策略。
