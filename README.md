# Material2Video（材料成片）

Material2Video 是短视频制作指导与工具链。新建作品使用 `project.json` v3 和分镜 v9，拥有自己的运行源码、依赖锁、资源恢复与 `SceneFilm` 合成；主项目通过本地入口委托校验、准备、片段检查与完整导出。画面可由代码生成，也可使用登记过的真实媒体。架构边界见 [ARCHITECTURE.md](ARCHITECTURE.md)，操作流程见 [material2video Skill](.agents/skills/material2video/SKILL.md)。

独立工程改造主体已完成：七部存量示例已原地改为独立工程，运行源码、依赖锁、字体与资源恢复、预览、采集和导出都归作品；`lookdev`、时间线与 QA 读取本地产物。主项目只保留制作指导、初始化、可选组件参考和制作管理；旧 `web/` 源码仅作参考与测试夹具，不参与任何作品运行。独立审查与 OpenSpec 归档正在收尾。

## 当前视频类型

<!-- generated:type-catalog:start -->
- `text-motion`：代码生成文字和图形，侧重排版与动效
- `data-evolution`：结构化数据的可视化变化
- `principle-metaphor`：程序生成物体和场景，说明抽象原理
- `spatial-3d`：三维模型和场景的空间渲染
- `documentary-edit`：真实视频、照片与档案的叙事剪辑
<!-- generated:type-catalog:end -->

地图轨迹与情境叙事是可选表现手法，不是独立类型。没有 `general`、专项类型、类别层或风格注册表。作品默认生成到 `videos/<类型>/<作品名>/`；随附示例放在 [`examples/`](examples/README.md)。

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

`init` 生成完整的三秒主题工程，五类默认都不预装三维、图表或业务来源模块；正式创作时改写分镜和 `scenes/opening.tsx`。本地命令、环境和恢复前提见[独立工程说明](templates/standalone/README.md)。生成后可以直接在作品目录运行，也可由 m2v 委托；默认 `videos/<类型>/<作品名>/` 只是生成位置，显式路径和后续搬移不要求该目录层级。`preview` 只检查片段；最终成片与审核按[媒体评审契约](.agents/skills/material2video/references/review-contract.md)执行。`render --jobs N` 可按帧区间并行。默认内容位置可通过 `--content-root` 或 `M2V_CONTENT_ROOT` 设置。

## 命令

运行 `uv run m2v --help` 查看入口与参数。类型目录通过 `m2v types` 查询；制作辅助操作使用 `m2v author`，金融来源计划使用 `m2v data financial-plan`。旧命令不保留别名。

## 网页原生设计样品

`m2v sample capture` 委托作品自己的 TSX 构建与采集入口，核对实际可达来源、字体、登记媒体、参数及产物，不需要完整分镜或配音；`sample serve` 使用本作品的字体与登记媒体，提供同源播放、复位与帧定位。`sample deliver` 仅在当前原生采集、独立盲看和同轮目标对照通过、必改项关闭后交付已评媒体，不重复编码。Windows 上采集和交付目录发布后统一恢复继承权限，便于标准权限应用读取。

选案由作者依据实际媒体和独立观察作出，明确参考采用范围、保留项、必修项和打磨项；仍可改善的次要处理不自动否决已成立的整体方向。`m2v review reuse --project <作品> --file <复用请求.json>` 支持同周期 trial 完整媒体字节及观察条件完全相同的视觉结论复用，重新验证当前技术来源，保留原独立报告和观察时间；不能绕过失败、用户目标变更或当前完整候选终审。格式与限制见[视觉复用](.agents/skills/material2video/references/review-contract.md#完整媒体相同的-trial-视觉复用)。

用户原始视觉要求、实际选中媒体与范围保留在设计和既有对照条件中，作者转化不得自行限缩；对照先检查目标转化忠实性，再检查画面兑现。整体风格向不同解释内容展开须有代表性迁移试制，不能仅用终态或同色同字体授权全片。用户指出偏离后保留旧报告并记录未完成，旧工具通过不替代真实要求，详见[采用边界](.agents/skills/material2video/references/review-contract.md#采用边界与选案责任)。

抽象表达按实际信息职责评审：意象、空间与动作可由清晰文字/读数配合承载精确事实，不默认要求每层字形或每个抽象局部都能辨认。整体表达成立时局部辨认代价作为打磨建议；关键误导、必要读数不可读、核心形象失效或风格偏离仍阻断，详见[抽象表达与信息职责](.agents/skills/material2video/references/review-contract.md#抽象表达与信息职责)。既有失败沿原规则保留，真实用户放宽须登记并重新复查。

```powershell
uv run m2v sample capture --project <作品> --entry scenes/core.tsx --duration-seconds 3 --frame 30
uv run m2v sample serve --project <作品> --id <采集ID>
uv run m2v sample deliver --project <作品> --id <采集ID> --blind-id <盲报告ID> --comparison-id <对照报告ID> --basis <具体选案依据>
```

设计试制不限主动时长和重试次数，未通过持续打磨；AI 图只能辅助内部构思/参考，不能直接交付或贴入网页冒充核心实现。允许调研并引入外部库、模型、Shader、建模与预计算等手段，作品直接依赖改为可扩展登记，校验来源、固定版本、许可与实际安装。具体流程、适配边界及评审请求见[网页原生样品](.agents/skills/material2video/references/design-samples.md)。采集凭据不自动判断审美或鉴别所有 AI 整图包装。

采集使用完整 Chromium 的无头模式；`uv run playwright install chromium` 会安装所需浏览器，仅安装 headless shell 不足以在 Windows 加载 WebGPU 的 DXC。代码场景可通过 `waitForFrame(PromiseLike)` 登记异步绘制，初始就绪和每帧/子帧在工作及合成完成后才放行；拒绝或超时仍失败，纯时间仍须实际验证。静态代码场景可使用已登记的本地路径追踪与 OIDN 去噪依赖；固定种子、样本和分块，在 GPU 及本地权重就绪后采集，逐场核验确定性，不据此宣称动态已验证。路径追踪与 OIDN 能力只保留在参考源码中，采用时由作品把实际依赖、补丁、权重来源和许可写进自己的工程与锁文件；动态仍须当前实际验证。参考依赖与许可见 [three-gpu-pathtracer](docs/licenses/three-gpu-pathtracer.txt)、[three-mesh-bvh](docs/licenses/three-mesh-bvh.txt)、[xatlas-web](docs/licenses/xatlas-web.txt)、[oidn-webgpu](docs/licenses/oidn-webgpu.txt)及 [WebGPU 类型](docs/licenses/webgpu-types.txt)；模型权重由作品登记来源、许可和恢复摘要，不入库。


## 材料与画面

`project.json` 只接受以下结构；`output` 可声明宽高、30/60 fps、声音和字幕配置：

```json
{"schemaVersion":3,"id":"demo","type":"data-evolution","materials":{"storyboard":"storyboard.json"},"runtime":{"version":1,"command":["uv","run","--frozen","python","scripts/video.py"]},"output":{"width":1920,"height":1080,"fps":30,"audio":"optional"}}
```

分镜必须同时声明 `version: 9` 和 `schemaVersion: 9`。每幕使用 `template: "code"`，通过 `content.entry` 指向作品内 TSX。新工程从本地 `src/code-scene/context` 导入时间接口，组件和第三方依赖由作品显式采用，不解析 `m2v/*`。分镜字段见[分镜契约](.agents/skills/material2video/references/storyboard-schema.md)；存量画面参考见[代码场景运行时](.agents/skills/material2video/references/code-scene-runtime.md)。原文、主题、字幕、媒体、声音与事件仍使用分镜 v9。

分镜顶层 `sources` 把来源 ID 绑定到作品内文件，幕内 `content.sourceIds` 选择来源。主项目仍保留 `financial-series`、`construction`、`vehicle-model` 的材料校验与计算辅助；新工程按需携带所采用的准备模块、数据快照及绘制实现，基础模板缺模块时明确报错，不回退主项目SDK。金融计划辅助入口为 `m2v data financial-plan --project <作品目录> [--duration-seconds N]`，要求分镜恰好声明一个金融来源。

五类创作都从统一阶段指南进入；金融行情、构件与车辆专项指南按实际绑定的来源展开。固定数学模型的数据演化无需金融行情计划。旧类型作品重制时按当前契约编排到新的类型目录，原目录及历史证据保留，见[修订入口](.agents/skills/material2video/references/video-revision.md)。

创作辅助命令改为 `m2v author`：源文审查、候选稿、素材导入和音效操作分别见 `m2v author --help` 与[媒体和声音契约](.agents/skills/material2video/references/article-media-and-sound.md)。外部画面素材使用 `assets/media-sources.json` 留证；`m2v assets report`、`contact-sheet`、`audit` 用于台账和技术检查。字体二进制按 [`fonts/registry.json`](fonts/registry.json) 恢复并校验，不纳入 Git。

旧类型名、`project.style`、project v1/v2、分镜 v8 及旧准备记录明确拒绝。升级后的材料需重新编排并重新准备；没有兼容入口或迁移命令，旧实现从 Git 历史追溯。

## 示例与文档

七部示例均为独立工程，可复制到仓库外按各自 README 恢复、预览与完整导出；主题、场景身份、数学／事实口径和音轨要求保持不变。素材与媒体按各自 `assets/recipe.json` 恢复，生成媒体与 `outputs/` 不入库。逐例改造范围与实际验证见[示例独立化记录](openspec/changes/make-video-projects-standalone/implementation-examples.md)和 [examples/README.md](examples/README.md)。

- [项目规划](docs/PROJECT_PLAN.md)：未来路线与未实现能力。
- [制作 Skill](.agents/skills/material2video/SKILL.md)：阶段入口、材料、画面、声音与评审规则。
- [三阶段制作](.agents/skills/material2video/SKILL.md)：研究与创意试制 → 正式设计 → 制作与验收。先比较同一关键场景的不同设计，按判断需要补足精度，再集中打磨；分别判断候选优劣与能否作为后续标准，允许全部淘汰。整体品质成立且在拟用链路重现后展开全片，具体选案与收敛见[研究与试制](.agents/skills/material2video/references/stage-research.md)。
- [全片与场景设计](.agents/skills/material2video/references/scene-design.md)：总设计统一五维与结构，每场以既有 scene.id 深化动作、配合、镜头、光影、声音和衔接；试制反馈持续回写。文档当前不渲染，分镜/代码维护执行参数，技能脚本支持全片或局部对应检查。
- [视频视觉与表达参考](.agents/skills/material2video/references/visual-expression-inspiration.md)：含 14 种视觉风格、6 种表达模式、12 种动态风格、12 种音效风格和 12 种转场风格，创作或视听表达修订前必读；名称用于拓展探索，采用自选。[深入风格研究](.agents/skills/material2video/references/reference-video-analysis.md)区分整体品质、专项表现和信息表达参考，记录实际观察、效果解释及本片应用；可随研究试制，未知触发补查，不以搜索数量或全部研究结束为前提。
- [架构说明](ARCHITECTURE.md)：代码分层与依赖方向。
- [OpenSpec 规格](openspec/specs/)：已实现行为。
- [项目协作约定](AGENTS.md)：验证、提交与资产管理。

日常验证只跑受影响的测试与真实媒体节点；正式全量回归仅在用户明确要求或人工发布验证时执行。文档投影可用 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` 检查。

### 媒体评审

`m2v review start|pack|import|timeline|retarget` 统一周期、隔离包、独立报告和全片预演。试制可从局部媒体开始，不要求完整分镜或机器设计合同。评审以有序帧、帧差/场景切分、主体区域量测和音频信号量测为证据，不要求播放或试听。`status` 分别展示试制、当前候选技术 QA、终审与未关闭问题；渲染可以生成待评审候选，技术通过不代表制作完成。旧检查点门、声明式画面量测和可选直接评审已移除，新旧报告不兼容且不转换旧通过。格式见[评审契约](.agents/skills/material2video/references/review-contract.md)。

选定视觉目标时，先盲看作品自身，再用实际参考媒体和中性条件进行同轮对照；整体品质不能缩成局部特征齐全，候选最好或独立 pass 不自动授权展开。评审提供具体观察，作者承担选案与下一试验责任。非空 `references` 必须配套非空 `conditions`，并区分品质标杆、专项目标和备选/历史比较用途；缺失会在创建包前拒绝，旧请求补条件后重建，历史包不改写。工具校验材料与证据，不自动评判审美。

用户明确要求更换已绑定失败的视觉目标时，可用 `review retarget --file <用户目标变更.json>` 保存用户原指令、旧失败ID和新盲包摘要；周期、旧失败及范围保留，登记不关闭问题。新目标必须在登记后重新独立盲看和同轮对照，仍须覆盖原职责、来源、窗口及显示尺寸。工具只验证授权声明与证据，实际用户授权由操作者依据对话核实。格式见[目标变更登记](.agents/skills/material2video/references/review-contract.md#用户明确变更目标)。

导出后清理会保护当前周期评审包仍绑定的预览源媒体和目标媒体；源文件仍参与证据摘要校验，无引用的旧预览继续清理。无法确认引用时报告并跳过清理。

Windows 基线读写支持深层评审记录路径，保留原相对路径格式，无需修改系统长路径策略。
