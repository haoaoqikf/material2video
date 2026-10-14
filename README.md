# Material2Video（材料成片）

面向短视频的离线制作工具链，采用**共享制作底座、独立视频类型、统一制作入口**。当前重点发展金融时间序列等专用视频，再沉淀可复用能力，逐步扩展到通用多场景编排。

## 当前视频类型

<!-- generated:type-catalog:start -->
- `financial-timeseries`：股票、指数及 crypto 日线材料（含 USD/CNY 历史汇率折算）、假设投资计算、手机竖屏折线画面和完整预演自动验收。
- `article-narrative`：v5 旁白驱动的观点、对比、步骤、因果图和图片讲解，真实语音同步、深浅主题与人工评审，成片不超过 60 秒。
- `general`：受控图文场景、金融/文章完整片段及作品级 React 场景的多场景时间轴。首版 1080×1920、30 fps，支持硬切、交叉淡化和可选口播。
- `housing-timeseries`：年度住宅销售均价动态折线视频，保存原始销售额、面积与来源口径，输出无声竖屏成片。
- `stock-montage`：按主题与逐幕关键词从在线图库检索并下载素材，留证来源、作者与许可后自动剪成竖屏短片，支持可选口播、字幕与本地音床。
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

```powershell
uv run m2v init --type general --project <slug> # 创建 videos/general/<slug>/
uv run m2v validate --project videos/general/<slug>
uv run m2v prepare --project videos/general/<slug>
uv run m2v preview --project videos/general/<slug>
uv run m2v review-template --project videos/general/<slug>
# 文章与通用视频查看预演并填写 outputs/review.json；金融视频直接使用完整预演自动验收。
uv run m2v review --project videos/general/<slug>
uv run m2v render --project videos/general/<slug>
uv run m2v relocate --project videos/<old-slug> # 迁移旧作品源文件与全部产物
```

作品及其全部 `outputs/` 产物按类型分层存放于 `videos/<type>/<slug>/`。`init` 的相对参数填写 `<slug>`，也可传入完整的 `videos/<type>/<slug>`；使用仓库外内容根时，传入 `--content-root` 或设置 `M2V_CONTENT_ROOT`。`relocate` 面向已有的 `videos/<slug>/` 统一契约作品，逐个备份后迁移源文件和产物；同名冲突文件不覆盖目标，解决后可重试。无 `project.json` 的旧文章内容不属于此迁移命令。

`init` 会生成材料模板。文章工作流仍先完成原文输入审查，再编辑 v5 讲解分镜。金融材料沿用 request、prices 和 animation-plan，可用 `m2v financial plan --project <目录>` 离线生成 v8 月波动节奏折线编排；所有新计划默认 60 秒，包含 1 秒开场、57 秒推进和 2 秒静止终幕，不随展示跨度变化，也可通过 `--duration-seconds` 显式指定其他时长。金融折线采用 x=140～940、y=180～1740 的项目布局边界及 x=220～928 绘图区；渲染时测量文字与图表前景的实际包围盒，将其垂直中心自动对齐画布中线 y=960，超过布局边界时阻断。裁剪范围随同一前景变换移动；每帧检查整个历史折线而非仅当前端点，裁剪错位或峰谷被裁切时阻断制作。该边界是项目保守默认值，不代表抖音官方安全区规范。标题格式为“假如你某年买入10万元某标的”，指数保留按比例投资表述，本金含“元”。金融画面底部默认显示统计口径和风险提示，不显示来源标签或来源网站名称；crypto 可配置法律地位说明替换该作品的统计口径和风险提示。完整来源、快照及核验要求保留在作品材料中。该规则也适用于通用视频内嵌的金融片段。既有作品重新准备并通过完整预演自动验收后使用新布局。画面顶部突出实际收盘年份、当前市值和日期，图表只显示跟随最新收盘点的圆点，不重复绘制金额牌，保持历史折线完整可见；终幕冻结完整曲线和坐标，并静止保留最终年份、当前市值及实际收盘日期，不显示收益总结。既有 v8 计划不自动修改，仍按材料内已保存分段校验。v7 保留原日期映射与四秒结尾，已有统一作品需用 `m2v financial migrate-line --project <目录>` 备份升级；旧金融材料使用显式 `m2v migrate --from financial` 迁移。文章仅接受 v5；v1～v4 必须重新编排。`render` 不修改原始材料；文章与通用视频要求人工评审匹配当前指纹，金融视频则要求当前完整预演及自动验收记录有效。

房价年度序列通过 `housing-timeseries` 独立类型制作。材料保存在 `series.json`，每个年度点包含住宅销售面积、销售额和按两者换算的平均价格，连续年份和单位由类型校验；默认 30 秒、1080×1920、30 fps 无声逐年折线（可通过 `durationSeconds` 指定 10 至 180 秒），每个年度点停留 0.5 秒并高亮显示准确年份与均价，须人工检查完整预演后渲染。公布值经过舍入时需说明计算均价的精度限制和统计口径断点。详细字段及流程见 [年度住宅均价视频说明](.agents/skills/material2video/references/housing-timeseries-video.md)。

股票和指数仍按价格或点位比缩放本金；crypto 可指定买入日与 CNY 本金，组合展示价值 = 本金 ×（当前 BTC/USD 收盘价 ÷ 买入日收盘价）×（当日或此前最近 USD/CNY 汇率 ÷ 买入日可用汇率）。crypto 请求还可提供法律地位说明，替换该作品默认估值口径行与通用风险提示；其他作品默认说明不变。prices v4 独立保存汇率来源、观测和原始快照；周末/假日使用最近此前汇率。详见[金融时间序列制作说明](.agents/skills/material2video/references/financial-timeseries-video.md)。

在线素材剪辑通过 `stock-montage` 独立类型制作。材料保存在 `brief.json`，只写主题、逐幕关键词、目标时长、图库配置与可选口播/音床；先设置图库凭据（只从环境变量读取，默认 `M2V_PEXELS_API_KEY`）并执行 `m2v stock search --project <目录>`，工具按幕检索并下载素材到 `assets/stock/`，同时把来源页、作者、许可、像素尺寸、时长与文件摘要写进 `outputs/footage-search.json`。任一幕没有可用候选、素材缺少来源/作者/许可、素材文件或 `brief.json` 被改动，都会让校验失败并要求重新检索；被替换过的素材不会进入渲染。准备阶段按目标时长自动分配逐幕帧数（口播幕按真实语音时长、固定帧数幕按声明值、其余均分并夹在 `minClipSeconds`/`maxClipSeconds` 与素材可用时长之间），静图做推拉平移，短视频按声明入点裁切，有口播或音床时合成单条母版音轨。画布 1080×1920、30 fps，渲染期素材经回环 HTTP 提供，画面不访问外部网络。须人工查看完整预演并填写 `outputs/review.json` 后渲染。详细字段、检索规则与剪辑规则见 [在线素材剪辑说明](.agents/skills/material2video/references/stock-montage-video.md)。

统一入口的正式渲染通过验收并写完成片旁车后，会清理本作品 `outputs/` 中旧视频、检查图和已知调试产物；金融完整预演作为自动验收绑定记录予以保留，其他类型按原规则清理预演。保留新成片及旁车、准备/评审 JSON 和可重渲的准备媒体。渲染失败不会触发清理，共享构建缓存不受影响；清理失败会报告遗留路径。

可用命令：`types`、`init`、`validate`、`prepare`、`preview`、`review-template`、`review`、`status`、`render`、`migrate`、`relocate`。文章专属的输入审查与候选稿操作使用 `m2v article input-review|candidate|adopt-candidate`；在线素材剪辑的检索使用 `m2v stock search --project <目录>`；操作性语义创作指导仍见 [material2video Skill](.agents/skills/material2video/SKILL.md)。

文章讲解使用 v5 多幕模板，详见 [分镜结构](.agents/skills/material2video/references/storyboard-schema.md)。在作品内保存非空 `article.md`，执行 `m2v article input-review --storyboard <路径>` 并填写 `outputs/input-review.json` 后准备配音。旁白与屏幕摘要独立，画面随实际 TTS 分段时间出现；每幕保留 12 帧阅读停留，可选 8 帧画面淡化，完整成片最多 60 秒。自动检查文字溢出及字幕遮挡，完整预演后填写统一 `outputs/review.json` 五项依据。旧 `production.json`、单世界动画分镜与旧评审不再适用，v1～v4 须重新编排；不自动迁移。

作品可以位于仓库外内容根；`M2V_CONTENT_ROOT` 用作默认内容根。架构和材料契约见 [OpenSpec 变更](openspec/specs/modular-video-production/spec.md)，未来能力路线见 [项目规划](docs/PROJECT_PLAN.md)。

## 项目结构

- `src/m2v/core/`：作品契约、路径、指纹、公共错误。
- `src/m2v/engine/`：Remotion 构建与缓存、渲染会话、音视频合成和验收。
- `src/m2v/types/`：文章、金融、通用类型、类型目录（`catalog.json`）与显式注册。
- `src/m2v/cli.py`：`m2v` 统一命令入口。
- `web/src/compositions/`：共享 composition、金融画面、文章讲解模板与通用场景宿主。
- `.agents/skills/material2video/references/`：材料、类型创作与评审操作参考。
- `openspec/specs/`、`openspec/changes/`：已归档规格与进行中的变更。

本轮不建设行情服务、云端队列、账号、自动发布、自动选曲或第三方插件系统。

## 从旧名称迁移

本次为全面改名，不提供旧入口兼容别名。重新执行 `uv sync`、`pnpm -C web install` 和 `pnpm -C web build` 后，更新调用方：

| 旧名称 | 新名称 |
| --- | --- |
| `article2video` / `article2video-web` | `material2video` / `material2video-web` |
| `a2v` 命令及 Python 模块 | `m2v` |
| `@a2v/scene` | `@m2v/scene` |
| `A2V_*` 环境变量（含 `A2V_CONTENT_ROOT`） | `M2V_*`（含 `M2V_CONTENT_ROOT`） |
| `.agents/skills/article2video/` | `.agents/skills/material2video/` |
| `window.__A2V__`、`a2v-storyboard`、`/__a2v_web__/` | `window.__M2V__`、`m2v-storyboard`、`/__m2v_web__/` |
| `a2v-` / `data-a2v-` / `--a2v-` 样式与属性前缀 | `m2v-` / `data-m2v-` / `--m2v-` |

作品中的旧场景导入、样式、属性及自定义契约引用需自行更新；旧命令、旧环境变量和旧场景接口不再支持。材料格式、分镜版本和视频类型保持不变，改名不会自动修改仓库内被忽略的作品或外部内容根。更新材料后重新执行 `m2v prepare` 和完整 `m2v preview`；文章与通用视频再填写并执行新评审，金融视频按完整预演自动验收后渲染。旧准备记录、评审和缓存不作为此次迁移的验收依据。本地仓库目录无需随品牌名移动。
