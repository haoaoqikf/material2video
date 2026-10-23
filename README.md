# Material2Video（材料成片）

面向短视频的离线制作工具链，采用**共享制作底座、独立视频类型、统一制作入口**。当前重点发展金融时间序列等专用视频，再沉淀可复用能力，逐步扩展到通用多场景编排。

通用视频默认 **30 fps**，可显式选择 **60 fps**；金融和住宅固定 **60 fps**。通用作品的 `project.json.output.fps` 与 `storyboard.json.fps` 均填写时必须一致，仅一处填写时使用该值，均省略时默认30；只接受整数30或60。现有显式60帧作品与三个示例保持原帧率。修改帧率后须重新 prepare，显式帧数字段不会自动换算。

所有作品默认面向手机观看，但不强制竖屏；制作复核按作品画幅检查字号、主体比例和播放器遮挡风险。制作流程按发布语境、受众理解和内容目标安排时长，并把降低前两秒流失作为开场审美考虑；没有真实发布数据时不推算实际跳出率、不造代理分数。成片文案须逐项排查仓库内部文件名、路径和材料查阅提示；来源与版权信息集中为唯一一份简短片尾署名。评审将重复静态信息卡片和机械逐页切换列为必改项，并结合全片帧序列确认画面有信息推进。

制作统一采用方案确定、粗片验证、精制修订、最终验收四阶段，见[制作流程](.agents/skills/material2video/references/production-workflow.md)。共用设计、唯一问题表和独立原始报告；核心表达、重要返工与争议按条件盲审，最终由叙事与视觉两名代理分工检查。传播评估并入最终记录，技术与制作完成分别报告。仅用于后续任务，不要求活跃制作切换，不改变 CLI 与金融住宅专用契约。

通用作品在叙事候选前完成立意六项（一句话命题、核心体验、表达载体、揭示与记忆、可验算骨架、重点投入）；选定叙事方案后按[视觉创意导演方法](.agents/skills/material2video/references/visual-creative-direction.md)完成七段式视觉创意方案（核心表达、核心视觉母题、整体视觉风格、分镜设计、视觉高潮、结尾视觉揭示、禁止项）与十项自检，必答但非评分或门禁；三案比较构思、揭示、代表段落、题材关联与风险，设计全片强弱和表达统一，精修主动强化亮点。信息与体验共同分配时间，减法与重要返工同时检查理解、感受、期待和记忆的收益／损失。评审区分实际缺陷、创意风险、审美偏好和证据不足；去文字、静音、缩略图、运动密度是[适用性诊断](.agents/skills/material2video/references/visual-review-rubric.md#诊断测试与适用性)，不按静止时限、母题像素差或形式标签直接否决。母题按完整段落的意义与体验判断，不强制重复或单调增长；事实、许可、技术和关键可读性检查不放宽。共享动效原语（数字滚动、数据曲线与柱状生长、列表滚屏、主体状态插值、签名粒子）以 `progress` 为唯一时间输入、不内置视觉主题。

## 当前视频类型

<!-- generated:type-catalog:start -->
- `financial-timeseries`：股票、指数及 crypto 日线材料（含 USD/CNY 历史汇率折算）、假设投资计算、手机竖屏折线画面和完整候选自动验收。
- `general`：v8 全画布代码场景讲解：作品自行设计横屏或竖屏画面的配色、构图与动效，支持原文或主题输入、带来源留证的媒体导入、内置音效与本地音床，成片最长 600 秒。
- `housing-timeseries`：年度住宅销售均价动态折线视频，保存原始销售额、面积与来源口径，输出无声竖屏成片。
<!-- generated:type-catalog:end -->

文章正文、金融原始材料与作品产物属于内容，不入库。所有通用作品采用统一标准与循环选案、核心试制、整片预演和精制回退流程，不再选择普通/电影级档位；旧 `productionProfile` 与 `--profile` 明确拒绝。三个固定示例为 [从电报到大模型](examples/american-science-milestones/README.md)、[人生五选择](examples/five-life-choices/README.md)、[太阳系之旅](examples/solar-system-journey/README.md)，数量最多三个，替换须用户明确授权。三片均为横屏；人生五选择按 30 fps 录制，另两片为 60 fps。美国科学里程碑为30秒无声混合媒体短片，按年代列出十项成果，优先使用已留证的档案与实物素材，代码动画补充原理，逐幕按素材特征变化构图并在片尾集中一份署名；人生五选择为60秒无声横屏动态图解，无旁白、配乐、音效与素材原声，以一条 2.5D 人生时间轴串联城市、行业、伴侣、投资与持续学习，并在结尾后拉成数十条路径的决策树；太阳系为单幕一镜到底，当前重制220.5秒、31个镜头和3个hero。三片合计覆盖 Motion、ECharts、Three.js、React Three Fiber 与 Drei；GSAP 随拥堵波示例退役，不再为覆盖组件增加无关效果。有声场景依实际旁白时间窗推进，无声场景使用明确帧数预算。可编辑分镜、代码、设计与许可来源随仓库分发；成片保存到 `videos/examples/<slug>/outputs/`，不入库。示例媒体也不入库：运行各自的 `assets/fetch.py` 按 `assets/recipe.json` 下载或生成，按登记摘要与实测尺寸、时长校验，缓存命中直接复用；公共字体及其许可仍随仓库分发。

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
# 有自身旁白时，先按下文选音并保存；手动制作可在 prepare 指定 --voice。
uv run m2v prepare --project videos/general/<slug>
# 可选片段检查，默认前十秒且严格短于全片
uv run m2v preview --project videos/general/<slug>
# 所有类型 render 只生成一次全片，自动验收后直接交付；m2v review 为可选工具，A/B 级评审按独立子代理流程执行。
uv run m2v render --project videos/general/<slug>
uv run m2v relocate --project videos/<old-slug> # 迁移旧作品源文件与全部产物
```

有旁白的制作流程为：材料审查 → 编排旁白 → **制作助手自动选择音色并保存** → 校验与时间轴准备 → 按需检查生成与修改 → 全片生成一次 → 验收与复核 → 交付同一文件。助手读取当前音色列表并按内容选择，用户明确音色优先；全流程不要求播放视频、连续收听声音或试听音色，按类型使用静帧/时间标注帧序列、路径与画面量测、字幕及时间戳核对和自动音频信号分析。用户无需试听确认；有自身旁白但缺少 `tts.voice` 时 `prepare` 会阻断，也可用 `--voice` 手动指定。无旁白作品无需选音。字段、溯源与迁移见[配音音色与节奏](.agents/skills/material2video/references/voice-and-rhythm.md#配音音色与语速)。

作品及其全部 `outputs/` 产物按类型分层存放于 `videos/<type>/<slug>/`。`init` 的相对参数填写 `<slug>`，也可传入完整的 `videos/<type>/<slug>`；使用仓库外内容根时，传入 `--content-root` 或设置 `M2V_CONTENT_ROOT`。`relocate` 面向已有的 `videos/<slug>/` 统一契约作品，逐个备份后迁移源文件和产物；同名冲突文件不覆盖目标，解决后可重试。无 `project.json` 的旧文章内容不属于此迁移命令。目录归属、内容根与默认输出见[目录约定与输出路径](.agents/skills/material2video/references/paths.md)。

`init` 会生成材料模板，通用类型还会按类型目录写入起步场景 `scenes/opening.tsx`。通用作品先确定画幅与视觉设计（作品 `DESIGN.md`）、写 `scenes/` 下的本地场景，再完成源文审查与分镜；金融与住宅分别沿用各自的材料契约。三类各自的材料、编排与画面规则见[文档导航](#文档导航)。

## 命令速查

- 基础链路：`types`、`init`、`validate`、`prepare`、`preview`、`review-template`、`review`、`status`、`render`、`migrate`、`relocate`。
- `preview` 只生成片段，默认前十秒（短作品最多全片减一帧），支持 `--start-seconds 20 --end-seconds 25` 或 `--limit-frames N`，覆盖全片会拒绝。它是可选检查工具，不是 render 的前置条件。
- `render` 将完整候选和输入/实现/编码参数指纹及 SHA-256 保存在 `outputs/candidates/` 与 `outputs/delivery.json`，验收后复制交付同一文件；同版本重复执行、验收失败或交付失败重试均不重新完整编码；文件损坏或输入变化后才重新生成。`status` 报告已准备、候选待验收、验收失败、可交付、交付失败或已交付。可选评审绑定候选摘要；异常退出留下 `delivery.lock` 时，先确认没有制作进程再移除锁。候选、交付记录与清理规则见[交付与溯源](.agents/skills/material2video/references/delivery-and-provenance.md)。
- 通用作品另有三个检查入口：`lookdev`（按风险选择尺寸的代表静帧、接触表与自定长度样片；无声作品样片无音轨，有声作品合并对应音轨；静帧、帧序列、量测和自动音频信号结论写入作品 `outputs/visual-notes.md`，不作为导出门禁）、`qa`（接触表、冻结帧、暗部测量提示、字幕配色对比度、响度与真峰值、音轨时长差、claims 时间窗覆盖；技术结果不代表视觉质量，图像与音频候选处置单独记录，输出 `outputs/qa.json`，含逐秒/逐镜头及交界加密采样、分页接触表、黑场/突变与交付音轨静音/削波候选；`inspection.rhythm` 另报全片及逐场旁白字数、旁白窗口并集、含窗口内停顿的平均字速、静音区间并集/占比与逐场交集，以及引子、段间、阅读停留、幕尾留白和未知归因。该测量不设最低字速或最长静音阈值，不参与技术判定；字幕阅读上限仍单独输出 `reading-pace.json`）与 `assets audit`（按实测尺寸与登记许可审计资产，全部登记媒体许可未知时阻断，输出 `outputs/asset-audit.json`）。
- 文章专属：输入审查与候选稿操作使用 `m2v general input-review|candidate|adopt-candidate`，图库默认且仅启用 Pixabay（需 `M2V_PIXABAY_API_KEY`），Pexels 固定停用；公开媒体直链仍可统一导入。混合媒体素材的检索与导入使用 `m2v general assets search|import --project <目录>`。
- 参考素材：`m2v ref fetch <分享链接或分享文本>` 通过浏览器读取抖音作品并下载到 `refs/douyin/<作品ID>/`，写入 `metadata.json` 与 `recipe.json`；`m2v ref verify <目录>` 复核 SHA-256 与字节数。支持视频与图文；已存在且校验通过时直接复用，`--headed` 用于人工完成登录或验证。参考素材属于内容，`refs/` 不入库，默认也不进入成片。用户明确要求复用某条参考作品的整条音频时，用 `m2v ref audio <参考目录> --project <作品目录> --user-authorized "<授权说明>"` 把音轨提取到作品 `assets/audio/` 并写 provenance；渲染链路仍不直接读取 `refs/`，成片只保留一处片尾署名。
- 金融专属：`m2v financial plan` 离线生成 v8 计划，`m2v financial migrate-line` 备份升级已有作品。
- 操作性语义创作指导见 [material2video Skill](.agents/skills/material2video/SKILL.md)。

## 项目结构

- `src/m2v/core/`：作品契约与路径（`project.py`、`workspace.py`）、指纹与资产、源码确定性检查（`source_policy.py`）、公共错误类型。
- `src/m2v/engine/`：Remotion 构建与缓存、渲染会话、字幕、音视频合成、性能报告和输出验收。
- `src/m2v/reference/`：抖音参考素材的浏览器取详情、直链下载、来源与摘要留证，以及用户明确授权时的音轨提取（`refs/` 为内容目录，不入库）。
- `src/m2v/types/`：金融、通用与住宅三个类型的行为适配器，以及类型目录（`catalog.json`）与显式注册。
- `src/m2v/cli.py`：`m2v` 统一命令入口；子命令实现在 `src/m2v/commands.py`。
- `web/src/compositions/`：三个类型各自的 composition（`FinancialTimeSeries`、`ArticleExplainer`、`HousingTimeSeries`）；通用作品的画面由作品自己的 `scenes/` 代码绘制，`ArticleExplainer` 只负责全画布片段回放与共享字幕。
- `web/src/frames.json`：通用作品画幅与字幕几何的唯一真源，Python 准备/量测与前端 SDK、合成层共读。
- `web/src/code-scene/primitives.ts`：五类共享动效原语（数字滚动、数据曲线与柱状生长、列表滚屏、主体状态插值、签名粒子），只做进度到数值的映射，不内置视觉主题；修改会使引用作品缓存失效。
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

旧命令与旧环境变量不再支持。当前通用类型为 `general`，使用 v8 `storyboard.json`，辅助命令为 `m2v general`；原 `article-narrative` 身份、`m2v article`、`general-plan.json` 编排、六种受控模板、视觉主题与完整片段嵌入已删除；画面以 v8 的全画布逐帧录制链路提供，入口是作品 `scenes/` 下的 TSX。旧材料不自动迁移，旧版分镜需重新编排。修改材料后重新 `prepare`，按需检查后执行 `render` 一次生成全片并验收交付；人工画面评审为可选工具。

## 文档导航

- [material2video Skill](.agents/skills/material2video/SKILL.md)：制作流程的操作手册与统一命令。
- 类型创作指导：[金融时间序列视频](.agents/skills/material2video/references/financial-timeseries-video.md)、[年度住宅均价视频](.agents/skills/material2video/references/housing-timeseries-video.md)、[通用作品创作](.agents/skills/material2video/references/article-to-storyboard.md)与[通用分镜 v8](.agents/skills/material2video/references/storyboard-schema.md)。
- 通用作品制作：[制作流程](.agents/skills/material2video/references/production-workflow.md)、[视觉创意导演方法](.agents/skills/material2video/references/visual-creative-direction.md)、[节奏、美术、声音与制作阶段](.agents/skills/material2video/references/creative-production.md)、[逐场设计与独立验收](.agents/skills/material2video/references/scene-design-and-acceptance.md)、[全片导演审查与剪辑重组](.agents/skills/material2video/references/director-review-and-edit.md)、[传播表现评估](.agents/skills/material2video/references/reach-potential.md)、[文章媒体与音效](.agents/skills/material2video/references/article-media-and-sound.md)、[参考风格契约](.agents/skills/material2video/references/reference-style.md)、[独立子代理评审](.agents/skills/material2video/references/subagent-review.md)、[统一制作与质量工具](.agents/skills/material2video/references/cinematic-video.md)、[自主视觉复核](.agents/skills/material2video/references/visual-review-rubric.md)、[讲解输入审查](.agents/skills/material2video/references/input-review.md)。
- 契约参考：[准备记录与字幕](.agents/skills/material2video/references/prepared-and-subtitles.md)、[配音音色与节奏](.agents/skills/material2video/references/voice-and-rhythm.md)、[代码场景运行契约](.agents/skills/material2video/references/code-scene-runtime.md)、[渲染引擎](.agents/skills/material2video/references/render-engine.md)、[目录约定与输出路径](.agents/skills/material2video/references/paths.md)、[交付与溯源](.agents/skills/material2video/references/delivery-and-provenance.md)、[设计令牌](.agents/skills/material2video/references/design-tokens.md)。
- 架构和材料契约见 [OpenSpec 规格](openspec/specs/modular-video-production/spec.md)，未来能力路线见[项目规划](docs/PROJECT_PLAN.md)。
