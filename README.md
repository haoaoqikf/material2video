# Material2Video（材料成片）

面向短视频的离线制作工具链，采用**共享制作底座、独立视频类型、统一制作入口**。当前重点发展金融时间序列等专用视频，再沉淀可复用能力，逐步扩展到通用多场景编排。

## 当前视频类型

<!-- generated:type-catalog:start -->
- `financial-timeseries`：股票、指数及 crypto 日线材料（含 USD/CNY 历史汇率折算）、假设投资计算、手机竖屏折线画面和完整预演自动验收。
- `general`：v7 旁白驱动的观点、对比、步骤、因果图、图片、视频与本地 React 代码场景讲解，支持原文或主题输入、带来源留证的媒体导入、内置音效与本地音床，成片最长 600 秒。
- `housing-timeseries`：年度住宅销售均价动态折线视频，保存原始销售额、面积与来源口径，输出无声竖屏成片。
<!-- generated:type-catalog:end -->

文章正文、金融原始材料与作品产物属于内容，不入库。三个固定示例为 `buffer-smoothing`、`darts-trial-and-error`、`keynote-baseline`，不增删或替换。

新增视频类型只在两处落地：在 `src/m2v/types/catalog.json` 登记类型身份、材料入口与初始化模板，并实现该类型的行为适配器（校验、准备、预演、渲染与可选的评审钩子）。统一入口不按类型名硬编码分发，作品契约也不维护类型白名单与材料映射；未在目录登记的类型会在渲染前失败。上面的清单与 Skill、项目规划中的清单都由该目录生成，改动后运行 `python .agents/skills/material2video/scripts/sync_docs.py` 重新生成。

## 快速开始

```powershell
uv sync
pnpm -C web install
pnpm -C web build
uv run playwright install chromium
uv run m2v types
uv run pytest
pnpm -C web test
```

统一入口以作品目录为唯一归属：

有旁白的制作流程为：材料审查 → 编排旁白 → **制作助手自动选择音色并保存** → 校验与准备 → 完整预演 → 正式导出。助手读取当前音色列表并按内容选择，用户明确音色优先，不新增试听确认。纯 CLI 读取选音结果；有自身旁白但缺少 `tts.voice` 时 `prepare` 会阻断，也可用 `--voice` 手动指定。助手选择绑定完整旁白，旁白变化需重新判断；实际音色、语速和来源写入准备与成片溯源。无旁白作品无需选音。详细字段、迁移和限制见[配音契约](.agents/skills/material2video/references/media-contract.md#配音音色与语速)。

```powershell
uv run m2v init --type general --project <slug> # 创建 videos/general/<slug>/
uv run m2v validate --project videos/general/<slug>
# 有自身旁白时，先按上文选音并保存；手动制作可在 prepare 指定 --voice。
uv run m2v prepare --project videos/general/<slug>
uv run m2v preview --project videos/general/<slug>
# 所有类型完整预演自动验收通过后直接导出；人工画面评审为可选工具。
uv run m2v render --project videos/general/<slug>
uv run m2v relocate --project videos/<old-slug> # 迁移旧作品源文件与全部产物
```

作品及其全部 `outputs/` 产物按类型分层存放于 `videos/<type>/<slug>/`。`init` 的相对参数填写 `<slug>`，也可传入完整的 `videos/<type>/<slug>`；使用仓库外内容根时，传入 `--content-root` 或设置 `M2V_CONTENT_ROOT`。`relocate` 面向已有的 `videos/<slug>/` 统一契约作品，逐个备份后迁移源文件和产物；同名冲突文件不覆盖目标，解决后可重试。无 `project.json` 的旧文章内容不属于此迁移命令。

`init` 会生成材料模板。文章工作流仍先完成原文输入审查，再编辑 v7 讲解分镜。金融材料沿用 request、prices 和 animation-plan，可用 `m2v financial plan --project <目录>` 离线生成 v8 月波动节奏折线编排；所有新计划默认 60 秒，包含 1 秒开场、57 秒推进和 2 秒静止终幕，不随展示跨度变化，也可通过 `--duration-seconds` 显式指定其他时长。金融折线采用 x=140～940、y=180～1740 的项目布局边界及 x=220～928 绘图区；渲染时测量文字与图表前景的实际包围盒，将其垂直中心自动对齐画布中线 y=960，超过布局边界时阻断。裁剪范围随同一前景变换移动；每帧检查整个历史折线而非仅当前端点，裁剪错位或峰谷被裁切时阻断制作。该边界是项目保守默认值，不代表抖音官方安全区规范。标题格式为“假如你某年买入10万元某标的”，指数保留按比例投资表述，本金含“元”。金融画面底部默认显示统计口径和风险提示，不显示来源标签或来源网站名称；crypto 可配置法律地位说明替换该作品的统计口径和风险提示。完整来源、快照及核验要求保留在作品材料中。既有作品重新准备并通过完整预演自动验收后使用新布局。画面顶部突出实际收盘年份、当前市值和日期，图表只显示跟随最新收盘点的圆点，不重复绘制金额牌，保持历史折线完整可见；终幕冻结完整曲线和坐标，并静止保留最终年份、当前市值及实际收盘日期，不显示收益总结。既有 v8 计划不自动修改，仍按材料内已保存分段校验。v7 保留原日期映射与四秒结尾，已有统一作品需用 `m2v financial migrate-line --project <目录>` 备份升级；旧金融材料使用显式 `m2v migrate --from financial` 迁移。文章仅接受 v7；v6 及更早作品必须重新编排。`render` 不修改原始材料；所有类型均要求当前完整预演及自动验收有效，无需人工查看、填写依据或再次确认；`review-template` / `review` 保留为可选工具，文章原文语义审查及金融自动探针保留。

房价年度序列通过 `housing-timeseries` 独立类型制作。材料保存在 `series.json`，每个年度点包含住宅销售面积、销售额和按两者换算的平均价格，连续年份和单位由类型校验；默认 30 秒、1080×1920、30 fps 无声逐年折线（可通过 `durationSeconds` 指定 10 至 180 秒），每个年度点停留 0.5 秒并高亮显示准确年份与均价，完整预演自动验收通过后即可渲染，人工画面评审为可选工具。公布值经过舍入时需说明计算均价的精度限制和统计口径断点。详细字段及流程见 [年度住宅均价视频说明](.agents/skills/material2video/references/housing-timeseries-video.md)。

股票和指数仍按价格或点位比缩放本金；crypto 可指定买入日与 CNY 本金，组合展示价值 = 本金 ×（当前 BTC/USD 收盘价 ÷ 买入日收盘价）×（当日或此前最近 USD/CNY 汇率 ÷ 买入日可用汇率）。crypto 请求还可提供法律地位说明，替换该作品默认估值口径行与通用风险提示；其他作品默认说明不变。prices v4 独立保存汇率来源、观测和原始快照；周末/假日使用最近此前汇率。详见[金融时间序列制作说明](.agents/skills/material2video/references/financial-timeseries-video.md)。

文章讲解与素材剪辑已合并到 `general` 一个入口：同一份 v7 分镜既能写受控图文幕，也能放图片与视频镜头，还能用 `code` 幕运行作品 `scenes/` 下的本地 React 组件；代码场景由准备阶段实时录制、按摘要缓存，完整预演与导出复用同一段已验收片段，只允许批准的共享依赖且不访问外网，详见 [分镜结构](.agents/skills/material2video/references/storyboard-schema.md)。`input.kind` 为 `article` 时绑定 `article.md` 并先完成源文语义审查，为 `topic` 时只声明 `input.topic`、跳过源文审查，由逐幕 `keywords` 驱动可选图库检索。媒体进入作品只有一条路：把候选写进导入清单后执行 `m2v general assets import --project <目录> --manifest <清单>`，工具下载或复制素材、实测真实类型与尺寸、按内容摘要落盘到 `assets/media/`，并把来源页、作者、许可、实测像素尺寸、时长与文件摘要写进 `assets/media-sources.json`；准备与渲染只读本地文件，不联网取素材。素材长宽比默认必须与画布 1080×1920（9:16）一致（容差 2%），个别幕可显式声明 `aspectRatio: "any"` 放宽；被替换过的素材或缺少导入记录的素材都会让校验失败，渲染期素材经回环 HTTP 提供，画面不访问外部网络。可选图库检索用 `m2v general assets search --project <目录>`，支持 Pexels 与 Pixabay（凭据只从环境变量读取：`M2V_PEXELS_API_KEY`、`M2V_PIXABAY_API_KEY`），没有候选不算失败，助手也可以改用其他公开媒体直链再统一导入留证。声音方面，分镜可用顶层 `soundtrack` 声明本地音床（`sourceRef`、`gainDb`、`loop`、淡入淡出）与最多 128 个音效；音效按 `sceneId`、可选 `segmentId` 与 `offsetMs` 定位，既可引用本地素材，也可使用内置 `ding`、`ding-dong`、`click`、`transition`；准备阶段按真实语音时长分配帧数，无旁白镜头按声明帧数或目标剩余时长分配，最后合成单条母版音轨并严格裁到全片时长，全片最多 600 秒。当前完整预演自动验收通过后即可渲染，人工画面评审为可选工具。详细字段、检索规则与混音规则见 [文章媒体与音效](.agents/skills/material2video/references/article-media-and-sound.md)。

统一入口的正式渲染通过验收并写完成片旁车后，会清理本作品 `outputs/` 中旧视频、检查图和已知调试产物；金融完整预演作为自动验收绑定记录予以保留，其他类型按原规则清理预演。保留新成片及旁车、准备/评审 JSON 和可重渲的准备媒体。渲染失败不会触发清理，共享构建缓存不受影响；清理失败会报告遗留路径。

可用命令：`types`、`init`、`validate`、`prepare`、`preview`、`review-template`、`review`、`status`、`render`、`migrate`、`relocate`。文章专属的输入审查与候选稿操作使用 `m2v general input-review|candidate|adopt-candidate`，混合媒体素材的检索与导入使用 `m2v general assets search|import --project <目录>`；操作性语义创作指导仍见 [material2video Skill](.agents/skills/material2video/SKILL.md)。

文章讲解使用 v7 混合媒体多幕模板，详见 [分镜结构](.agents/skills/material2video/references/storyboard-schema.md)。在作品内保存非空 `article.md`（或改用 `input.kind: "topic"` 声明主题），执行 `m2v general input-review --storyboard <路径>` 并填写 `outputs/input-review.json` 后准备配音。旁白与屏幕摘要独立，画面随实际 TTS 分段时间出现；默认根据旁白原文生成同步字幕并烧录到预演和正式成片，无需开启字幕选项，仅外置 SRT 不算完成字幕交付；每幕保留 12 帧阅读停留，可选 1～1800 帧画面淡化，完整成片最多 600 秒。自动检查文字溢出、正文侵入字幕区及字幕实际遮挡，完整预演自动验收通过后即可导出；统一 `outputs/review.json` 五项依据为可选评审材料。旧 `production.json`、v6 及更早分镜与旧评审不再适用，须重新编排；不自动迁移。


作品可以位于仓库外内容根；`M2V_CONTENT_ROOT` 用作默认内容根。架构和材料契约见 [OpenSpec 变更](openspec/specs/modular-video-production/spec.md)，未来能力路线见 [项目规划](docs/PROJECT_PLAN.md)。

## 项目结构

- `src/m2v/core/`：作品契约与路径（`project.py`、`workspace.py`）、指纹与资产、源码确定性检查（`source_policy.py`）、公共错误与报告类型。
- `src/m2v/engine/`：Remotion 构建与缓存、渲染会话、字幕、音视频合成、性能报告和输出验收。
- `src/m2v/types/`：金融、通用与住宅三个类型的行为适配器，以及类型目录（`catalog.json`）与显式注册。
- `src/m2v/cli.py`：`m2v` 统一命令入口。
- `web/src/compositions/`：三个类型各自的 composition（`FinancialTimeSeries`、`ArticleExplainer`、`HousingTimeSeries`）。
- `.agents/skills/material2video/references/`：材料、类型创作与渲染契约参考。
- `openspec/specs/`、`openspec/changes/`：已归档规格与进行中的变更。

本轮不建设行情服务、云端队列、账号、自动发布、自动选曲或第三方插件系统。

## 从旧名称迁移

本次为全面改名，不提供旧入口兼容别名。重新执行 `uv sync`、`pnpm -C web install` 和 `pnpm -C web build` 后，更新调用方：

| 旧名称 | 新名称 |
| --- | --- |
| `article2video` / `article2video-web` | `material2video` / `material2video-web` |
| `a2v` 命令及 Python 模块 | `m2v` |
| `A2V_*` 环境变量（含 `A2V_CONTENT_ROOT`） | `M2V_*`（含 `M2V_CONTENT_ROOT`） |
| `.agents/skills/article2video/` | `.agents/skills/material2video/` |
| `window.__A2V__`、`a2v-storyboard`、`/__a2v_web__/` | `window.__M2V__`、`m2v-storyboard`、`/__m2v_web__/` |
| `a2v-` / `data-a2v-` / `--a2v-` 样式与属性前缀 | `m2v-` / `data-m2v-` / `--m2v-` |

旧命令与旧环境变量不再支持。当前通用类型为 `general`，使用 v7 `storyboard.json`，辅助命令为 `m2v general`；原 `article-narrative` 身份、`m2v article`、`general-plan.json` 编排与完整片段嵌入已删除；作品代码场景以 v7 的独立实时录制链路重新提供，入口是作品 `scenes/` 下的 TSX。旧材料不自动迁移，旧版分镜需重新编排。修改材料后重新 `prepare` 和完整 `preview`，通过自动验收后导出；人工画面评审为可选工具。
