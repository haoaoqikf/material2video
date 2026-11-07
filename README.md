# Material2Video（材料成片）

Material2Video 是离线短视频制作工具链。五类视频共用 `project.json` v2、分镜 v9、代码场景准备、短预演、单一 `SceneFilm` composition 和制作证据流程。画面可由代码生成，也可使用登记过的真实媒体。架构边界见 [ARCHITECTURE.md](ARCHITECTURE.md)，操作流程见 [material2video Skill](.agents/skills/material2video/SKILL.md)。

## 当前视频类型

<!-- generated:type-catalog:start -->
- `text-motion`：代码生成文字和图形，侧重排版与动效
- `data-evolution`：结构化数据的可视化变化
- `principle-metaphor`：程序生成物体和场景，说明抽象原理
- `spatial-3d`：三维模型和场景的空间渲染
- `documentary-edit`：真实视频、照片与档案的叙事剪辑
<!-- generated:type-catalog:end -->

地图轨迹与情境叙事是可选表现手法，不是独立类型。没有 `general`、专项类型、类别层或风格注册表。作品统一放在 `videos/<类型>/<作品名>/`；随附示例放在 [`examples/`](examples/README.md)。

## 安装与快速开始

```powershell
uv sync
pnpm -C web install
uv run python fonts/fetch.py
pnpm -C web build
uv run playwright install chromium
uv run m2v types
uv run m2v init --type text-motion --project demo
uv run m2v validate --project videos/text-motion/demo
uv run m2v prepare --project videos/text-motion/demo
uv run m2v preview --project videos/text-motion/demo --limit-frames 30
```

`init` 生成可准备的三秒主题示例；正式创作时改写分镜和 `scenes/opening.tsx`。五类使用同一命令：`validate`、`prepare`、`preview`、`lookdev`、`render`、`qa`、`status`、`review`、`sample`、`issues` 与 `baseline`。`preview` 只检查片段；最终成片与审核按[媒体评审契约](.agents/skills/material2video/references/review-contract.md)执行。`render --jobs N` 可按帧区间并行。作品可通过 `--content-root` 或 `M2V_CONTENT_ROOT` 放在仓库外。

## 命令

运行 `uv run m2v --help` 查看入口与参数。类型目录通过 `m2v types` 查询；制作辅助操作使用 `m2v author`，金融来源计划使用 `m2v data financial-plan`。旧命令不保留别名。

## 网页原生设计样品

`m2v sample capture` 从作品 TSX 入口和可选参数直接构建网页、静帧及完整局部视频，无需完整分镜或配音；`sample serve` 提供同源播放、复位与帧定位。`sample deliver` 仅在当前原生采集、独立盲看和同轮目标对照通过、必改项关闭后交付已评媒体，不重复编码。Windows 上采集和交付目录发布后统一恢复继承权限，便于标准权限的图片与媒体应用读取。

```powershell
uv run m2v sample capture --project <作品> --entry scenes/core.tsx --duration-seconds 3 --frame 30
uv run m2v sample serve --project <作品> --id <采集ID>
uv run m2v sample deliver --project <作品> --id <采集ID> --blind-id <盲报告ID> --comparison-id <对照报告ID> --basis <具体选案依据>
```

设计试制不限主动时长和重试次数，未通过持续打磨；AI 图只能辅助内部构思/参考，不能直接交付或贴入网页冒充核心实现。允许调研并引入外部库、模型、Shader、建模与预计算等手段，作品直接依赖改为可扩展登记，校验来源、固定版本、许可与实际安装。具体流程、适配边界及评审请求见[网页原生样品](.agents/skills/material2video/references/design-samples.md)。采集凭据不自动判断审美或鉴别所有 AI 整图包装。

## 材料与画面

`project.json` 只接受以下结构；`output` 可声明宽高、30/60 fps、声音和字幕配置：

```json
{"schemaVersion":2,"id":"demo","type":"data-evolution","materials":{"storyboard":"storyboard.json"},"output":{"width":1920,"height":1080,"fps":30,"audio":"optional"}}
```

分镜必须同时声明 `version: 9` 和 `schemaVersion: 9`。每幕使用 `template: "code"`，通过 `content.entry` 指向作品内 TSX，代码从 `m2v/code-scene` 导入共享绘制与逐帧 API。完整字段见[分镜契约](.agents/skills/material2video/references/storyboard-schema.md)和[代码场景运行时](.agents/skills/material2video/references/code-scene-runtime.md)。原文、主题、字幕、媒体、声音、事件、纯时间采集及制作证据都沿用统一链路。

数据演化可以引用 `financial-series` 来源；三维空间可以引用 `construction` 或 `vehicle-model` 来源。分镜顶层 `sources` 把来源 ID 绑定到作品内的请求、行情、构件、模型与资产文件；幕内 `content.sourceIds` 显式选择本幕使用的来源。准备阶段验证材料、素材摘要、画幅、帧率、时长，并把来源及计算实现纳入准备指纹。画面代码从 `m2v/code-scene/sources` 引入 `FinancialSeriesScene`、`ConstructionScene`、`VehicleScene`，也可用 SDK 的 `useSceneSource(id)` 自行绘制。金融计划通过 `m2v data financial-plan --project <作品目录> [--duration-seconds N]` 生成，要求分镜恰好声明一个金融来源。

五类创作都从统一阶段指南进入；金融行情、构件与车辆专项指南按实际绑定的来源展开。固定数学模型的数据演化无需金融行情计划。旧类型作品重制时按当前契约编排到新的类型目录，原目录及历史证据保留，见[修订入口](.agents/skills/material2video/references/video-revision.md)。

创作辅助命令改为 `m2v author`：源文审查、候选稿、素材导入和音效操作分别见 `m2v author --help` 与[媒体和声音契约](.agents/skills/material2video/references/article-media-and-sound.md)。外部画面素材使用 `assets/media-sources.json` 留证；`m2v assets report`、`contact-sheet`、`audit` 用于台账和技术检查。字体二进制按 [`fonts/registry.json`](fonts/registry.json) 恢复并校验，不纳入 Git。

旧类型名、`project.style`、project v1、分镜 v8 及旧准备记录明确拒绝。升级后的材料需重新编排并重新准备；没有兼容入口或迁移命令。

## 示例与文档

七部示例按五类分组，清单和恢复命令见 [examples/README.md](examples/README.md)。画面专属组件放在各示例 `scenes/`；跨作品可复用的计数、图表和轨道能力在共享代码场景 SDK。示例媒体按各自 `assets/recipe.json` 恢复；生成媒体与 `outputs/` 不入库。

- [项目规划](docs/PROJECT_PLAN.md)：未来路线与未实现能力。
- [制作 Skill](.agents/skills/material2video/SKILL.md)：阶段入口、材料、画面、声音与评审规则。
- [三阶段制作](.agents/skills/material2video/SKILL.md)：研究与创意试制 → 正式设计 → 制作与验收。先比较同一关键场景的不同设计，按判断需要补足精度，再集中打磨；分别判断候选优劣与能否作为后续标准，允许全部淘汰。整体品质成立且在拟用链路重现后展开全片，具体选案与收敛见[研究与试制](.agents/skills/material2video/references/stage-research.md)。
- [视频视觉与表达参考](.agents/skills/material2video/references/visual-expression-inspiration.md)：含 14 种视觉风格、6 种表达模式、12 种动态风格和 12 种音效风格，创作或视听表达修订前必读；名称用于拓展探索，采用自选。[深入风格研究](.agents/skills/material2video/references/reference-video-analysis.md)区分整体品质、专项表现和信息表达参考，记录实际观察、效果解释及本片应用；可随研究试制，未知触发补查，不以搜索数量或全部研究结束为前提。
- [架构说明](ARCHITECTURE.md)：代码分层与依赖方向。
- [OpenSpec 规格](openspec/specs/)：已实现行为。
- [项目协作约定](AGENTS.md)：验证、提交与资产管理。

日常验证只跑受影响的测试与真实媒体节点；正式全量回归仅在用户明确要求或人工发布验证时执行。文档投影可用 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` 检查。

### 媒体评审

`m2v review start|pack|import|timeline` 统一周期、隔离包、独立报告和全片预演。试制可从局部媒体开始，不要求完整分镜或机器设计合同。`status` 分别展示试制、当前候选技术 QA、终审与未关闭问题；渲染可以生成待评审候选，技术通过不代表制作完成。旧检查点门、声明式画面量测和可选直接评审已移除，新旧报告不兼容且不转换旧通过。格式见[评审契约](.agents/skills/material2video/references/review-contract.md)。

选定视觉目标时，先盲看作品自身，再用实际参考媒体和中性条件进行同轮对照；整体品质不能缩成局部特征齐全，候选最好或独立 pass 不自动授权展开。评审提供具体观察，作者承担选案与下一试验责任。非空 `references` 必须配套非空 `conditions`，并区分品质标杆、专项目标和备选/历史比较用途；缺失会在创建包前拒绝，旧请求补条件后重建，历史包不改写。工具校验材料与证据，不自动评判审美。

导出后清理会保护当前周期评审包仍绑定的预览源媒体和目标媒体；源文件仍参与证据摘要校验，无引用的旧预览继续清理。无法确认引用时报告并跳过清理。

Windows 基线读写支持深层评审记录路径，保留原相对路径格式，无需修改系统长路径策略。
