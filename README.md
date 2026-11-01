# Material2Video（材料成片）

面向短视频的离线制作工具链，采用**通用代码、类型专属代码、具体作品代码**三层组织，并保持统一的制作入口。代码分层、模块职责与依赖方向见 [ARCHITECTURE.md](ARCHITECTURE.md)；项目当前能力见下方类型目录；制作流程和类型契约由 [material2video Skill](.agents/skills/material2video/SKILL.md) 及其参考文档维护。

## 当前视频类型

<!-- generated:type-catalog:start -->
**路线旅程**：以真实道路为骨架的路线与旅程影像：单段自驾行程与多日地图游记。
- `driving-route`：真实高速优先驾车路线、竖屏普通道路地图、无注记路网与市/县行政区标注、小车沿路行驶与 12× 平滑镜头跟随；顶部两行“模拟行程”标题，已行驶里程随车显示，在线取数与离线成片分离，1080×1920、30 fps、无声交付。
- `road-trip`：真实国道走廊、多日行程、每日章节卡与数据卡、旁白字幕音效与程序化音床；1080×1920 竖屏、30 fps、有声交付。

**未分类**
- `financial-timeseries`：股票、指数及 crypto 日线材料（含 USD/CNY 历史汇率折算）、假设投资计算、手机竖屏折线画面和完整候选自动验收。
- `general`：v8 全画布代码场景讲解：作品自行设计横屏或竖屏画面的配色、构图与动效，支持原文或主题输入、带来源留证的媒体导入、双来源音效库与本地音床，成片最长 600 秒。
- `building-construction`：程序化两层框架住宅、基础到完工的分阶段确定性动画、1920×1080 横屏、30 fps、无声交付。
- `vehicle-showcase`：本地汽车模型、自动环绕、影棚灯光与视觉疾驰；固定 1920×1080、30 fps、无声。
<!-- generated:type-catalog:end -->

风格示例：[从电报到大模型](styles/doc-archive/examples/american-science-milestones/README.md)、[复利](styles/count-ledger/examples/compound-interest/README.md)、[太阳系之旅](styles/deep-journey/examples/solar-system-journey/README.md)、[折叠](styles/vibe-night/examples/fold/README.md)与[鸽子的迷信](styles/vibe-fable/examples/pigeon/README.md)。复利示例为29秒数学讲解动画：开场以“复利的力量”点题；1枚圆片=1,000元，以米白/金色/暗金三种资金状态解释收益再投入；第30年以40枚/约174.5枚可数圆片直接比较两种处理方式的30年总资产，随后用独立 S6 让16枚金色收益归队变白，只剩175枚本金堆，再以结论与片名收束。无旁白、无旋律配乐，含8秒进入的环境床与25个同步事件音。制作状态见示例验证记录。作品材料和输出位置见各示例说明及[协作约定](AGENTS.md)。

通用视频的创作方法（视觉事件、导演设计、逐场设计与验收）集中见[视觉创意导演方法](.agents/skills/material2video/references/visual-creative-direction.md)；看图诊断见[看图诊断与形象判据](.agents/skills/material2video/references/explainer-design.md#看图诊断与形象判据)。

制作载体选择见[素材选择规范](.agents/skills/material2video/references/visual-material-selection.md#视频优先与代码适用场景)；规则来源及文档维护边界见[架构说明](ARCHITECTURE.md#契约与文档)。类型清单、制作门及审核策略表由共享定义生成，运行 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` 可检查漂移。

讲解机制与实际表达复核已纳入制作指导：按需组织对象追踪、尺度变化、过程结果与回场，沿现有独立评审验证画面实际建立的关系；方法见[讲解设计](.agents/skills/material2video/references/explainer-design.md#四种讲解机制的执行方法)。注册风格和组件技术通过不代表成片表现通过。

general 讲解制作在现有逐场记录和时间线上协调贯穿对象、连续行为、画面事件与适用声音，并检查完整变化和观察窗口；具体方法见[贯穿对象、事件和完整动作](.agents/skills/material2video/references/explainer-design.md#贯穿对象事件和完整动作)。场景可声明 `content.props.capture.timebase: "global"` 获取全片时间，把连续行为写成一条不依赖幕 ID 的状态轨迹，各镜头只取景；声音与画面共用幕内事件，并用事件密度、增益、淡化与不同素材表达语义变化。写法见[全局时间与连续行为](.agents/skills/material2video/references/code-scene-runtime.md#全局时间与连续行为)与[声音语义](.agents/skills/material2video/references/article-media-and-sound.md#声音语义与事件化)。

可选 Canvas 绘制层的量测同步透明度、逐字显影、分组变换与裁剪，使用实际字形外框；完全不可见文字不会作为可见对象通过，部分裁剪明确报告失败。最终像素遮挡与可读性仍需视觉复核，见[绘制量测边界](.agents/skills/material2video/references/code-scene-runtime.md#绘制量测的可见性边界)。

Painter 另提供离屏 `layer()` 整体合成与纯数值关键帧 `keyframeAt()`；`web/gallery.html` 是只在开发服务器提供的动态能力货架，含可回放固定种子模拟，不进入作品或生产构建。通用声音支持可选全片增益曲线与声音设计层静音窗口；长片的编年、论证链和侧面探索方法见[讲解设计](.agents/skills/material2video/references/explainer-design.md#长片叙事结构)。

代码场景可声明 `content.props.capture.mode: "pure-time"` 走纯时间采集：任意帧直接 seek，按块并行采集后无损拼接，预览与 lookdev 不再回放前缀；纯性由静态源码闸门与正序/倒序 PSNR 双重验证，失败明确拒绝。`render --jobs N` 可进一步按帧区间分进程渲染。默认仍为顺序采集、单进程；写法与限制见[纯时间采集](.agents/skills/material2video/references/code-scene-runtime.md#纯时间采集opt-in)。

general 制作采用「方案确定 → 制作与迭代 → 最终验收」三阶段；核心表达明确后可先做低成本画面原型，再补齐正式扩展所需设计。G5 全片粗片由制作助手内部检查；低风险作品只派一次当前候选独立终审，核心风险按计划在扩展前增加适用评审。入口见[制作与迭代](.agents/skills/material2video/references/stage-iterate.md)。同一材料可由连续构图完善到动态实现，通过后保留并逐段扩展。选案按未决问题比较，不固定候选数量；检查工具按需调用，完整证据与制作完成条件仍须满足。具体见[完整段落试制与逐段扩展](.agents/skills/material2video/references/production-workflow.md#完整段落试制与逐段扩展)。

## 快速开始

general 可声明幕内事件，由动画、计数、视觉强调和音效共同引用同一帧；prepare 输出绑定准备指纹的 `outputs/events.json`，改事件后重新准备。声明见[幕内事件](.agents/skills/material2video/references/storyboard-schema.md#幕内事件)，SDK 用法见[事件查询](.agents/skills/material2video/references/code-scene-runtime.md#幕内事件查询)。

```powershell
uv sync
uv run python fonts/fetch.py
pnpm -C web install
pnpm -C web build
uv run playwright install chromium
uv run m2v types
uv run pytest            # 默认：纯单元与契约用例
pnpm -C web test
```

测试按运行成本分层，默认只跑不依赖外部进程的纯单元与契约用例，约数分钟；需要真实媒体或渲染时显式选择：

```powershell
uv run pytest                  # 默认层：不含 media 与 slow
uv run pytest -m "not slow"    # 交付前回归：默认层加真实媒体编解码
uv run pytest -m slow          # 浏览器、真实渲染与长时等待
uv run pytest --full           # 全部用例
```

`media` 用例需要 ffmpeg 真实编解码，`slow` 用例需要 Chromium 或完整渲染链路。CI 运行 `-m "not slow"`；本地缺少示例媒体时相关用例按既有约定跳过。显式指定测试文件、目录或节点时按指定范围运行，不套用默认排除。示例内容只由各自作品的制作与验收流程维护，不再作为通用测试重复断言固定帧数与时长。

统一入口以作品目录为唯一归属：

```powershell
uv run m2v init --type general --project <slug> # 创建 videos/general/<slug>/，项目与分镜均默认横屏
uv run m2v validate --project videos/general/<slug>
# 有自身旁白时，先按下文选音并保存；手动制作可在 prepare 指定 --voice。
uv run m2v prepare --project videos/general/<slug>
# 可选局部片段检查：默认前十秒或显式短窗口，不能替代全片生成
uv run m2v preview --project videos/general/<slug>
# render 每次生成一个全片候选并自动技术验收；制作完成还须有效证据与适用评审。m2v review 是可选工具。
uv run m2v render --project videos/general/<slug> [--jobs N] # N>1 为进程级分段渲染
uv run m2v relocate --project videos/<old-slug> # 迁移旧作品源文件与全部产物
```

general 作品未配置旁白、音乐和音效时，预览与正式成片均不含音轨；有任一声音声明则保留原混音与验收流程。

有旁白的制作流程为：材料审查 → 编排旁白 → **制作助手自动选择音色并保存** → 校验与时间轴准备 → 按需检查生成与修改 → 全片生成一次 → 验收与复核 → 交付同一文件。助手读取当前音色列表并按内容选择，用户明确音色优先；全流程不要求播放视频、连续收听声音或试听音色，按类型使用静帧/时间标注帧序列、路径与画面量测、字幕及时间戳核对和自动音频信号分析。用户无需试听确认；有自身旁白但缺少 `tts.voice` 时 `prepare` 会阻断，也可用 `--voice` 手动指定。无旁白作品无需选音。字段、溯源与迁移见[配音音色与节奏](.agents/skills/material2video/references/voice-and-rhythm.md#配音音色与语速)。

作品及其全部 `outputs/` 产物按类型与类别分层存放：未分类类型为 `videos/<type>/<slug>/`，属于类别的类型为 `videos/<category>/<type>/<slug>/`（例如 `videos/route-journey/driving-route/<slug>/`）。仓库自带风格示例（`styles/<style-id>/examples/<slug>/`）的全部产物写在示例目录下的 `outputs/`，同样不入库。`init` 的相对参数填写 `<slug>`，也可传入完整的规范相对路径；使用仓库外内容根时，传入 `--content-root` 或设置 `M2V_CONTENT_ROOT`。`relocate` 面向位于 `videos/` 下非规范位置的统一契约作品（如 `videos/<slug>/` 或旧的 `videos/<type>/<slug>/`），按类型目录中的类别迁移到规范位置，逐个备份后移动源文件和产物；同名冲突文件不覆盖目标，解决后可重试。无 `project.json` 的旧文章内容不属于此迁移命令。目录归属、内容根与默认输出见[目录约定与输出路径](.agents/skills/material2video/references/paths.md)。

`init` 会生成材料模板，通用类型还会按类型目录写入起步场景 `scenes/opening.tsx`。通用作品先确定画幅与视觉设计（作品 `DESIGN.md`）、写 `scenes/` 下的本地场景，再完成源文审查与分镜；金融与自驾路线各自沿用专用材料契约。各类型的材料、编排与画面规则见[文档导航](#文档导航)。

多日地图游记使用一份 `trip.json`，每日路线在 `routes/day-XX.json` 并由 `trip.json` 引用：填写起终点、天数、每日目的地与 via、旁白、卡片与事实来源后，设置 `M2V_AMAP_KEY` 执行 `uv run m2v road-trip fetch --project videos/route-journey/road-trip/<slug>`；第 1 天从行程起点定位，第 N 天起点直接使用前一天终点，按 via 顺序分段规划并原子保存全部路线。授权落实后执行 `uv run m2v road-trip basemap --project videos/route-journey/road-trip/<slug>` 生成全局概览、每日概览与每日跟随瓦片走廊，`--style` 可临时覆盖逐日普通/卫星设置。之后 `prepare / preview / render` 全程离线：准备阶段合成旁白与字幕、混入音效与 30 秒程序化音床并归一化母版；渲染时通过本地静态服务注入底图路径，只挂载当前视口瓦片。画幅固定 1080×1920、30 fps、有声；材料形状、命令与画面契约见[多日地图游记](.agents/skills/material2video/references/road-trip-video.md)。

自驾路线使用独立的 `request.json` 与 `route.json`：填写起终点与来源使用依据后，设置 `M2V_AMAP_KEY` 并执行 `uv run m2v driving-route fetch --project videos/route-journey/driving-route/<slug>` 取得真实高速优先路线；需要普通道路底图时，确认授权并置 `mapTiles=true` 后执行 `uv run m2v driving-route basemap --project videos/route-journey/driving-route/<slug>`，概览拼接图与 z12 跟随瓦片走廊会本地保存并绑定摘要；加 `--style satellite` 可生成卫星底图版本，路线、市/县标签与镜头保持不变。之后 `validate / prepare / preview / render` 全程离线，不需要 Key。画幅固定 1080×1920 竖屏、30 fps、无音轨，默认 30 秒，首例 60 秒；顶部两行居中标题“模拟行程 / 上海 → 郑州”，已行驶公里数显示在车辆旁，市名与县/县级市名以 40 px 加粗白描边显示（市辖区不单独标注），不显示底部数据面板。普通道路底图使用 `style=8&scl=2` 的 512×512 无文字/POI 注记瓦片，画面地名只由标签层绘制。城市间画面跳过起点接入大路前的小路，里程同步扣除，5 公里内找不到大路时准备失败。开场 2 秒从 8×快速推到 12×，行政区自绘标签在推近与拉远时淡出、镜头稳定后淡入；中段 12×匀速跟随，跟随段相机平移对齐整像素，底图与标签共享同一重采样相位以避免文字抖动，屏内标签保持全不透明并随地图连续滑出视口；结尾 2 秒拉远并保持全程，最终总览只显示市级标签。小车起步朝向采用路线首段方向。取数授权、材料形状与画面契约见[自驾路线视频](.agents/skills/material2video/references/driving-route-video.md)。

可选风格机制独立于视频类型：`uv run m2v styles` 查询注册包，作品通过 `project.json` 的 `style.id` 选择；当前已登记 `vibe-fable`（B 寓言）、`vibe-night`（C 夜曲）、`doc-archive`（档案纪录片）、`count-ledger`（可数物证）与 `deep-journey`（深空旅程），每个风格配一个可校验的风格示例（`styles/<id>/examples/<slug>/`，示例子树不参与风格指纹）。示例各附 `DESIGN.md` 与 `HOWTO.md`（可复现的调时、取景或几何布局练习，含修改位置、验证命令与恢复方式）；技术检查与理解观察分开记录，前者不替代后者。general 场景可显式使用参数、组件和资产，选择风格不会自动换肤。无旁白作品可在字幕安全区内自绘屏幕字幕；讲解方法与六种画法见[讲解设计](.agents/skills/material2video/references/explainer-design.md)。契约见[风格接入](.agents/skills/material2video/references/style-pack.md)，示例与目录约定见[风格包目录](styles/README.md)。

## 命令

运行 `uv run m2v --help` 查看当前命令；类型专属材料和制作流程见 [material2video Skill](.agents/skills/material2video/SKILL.md)。

仅当用户明确要求复用整条参考音轨时，使用 `m2v ref audio <参考目录> --project <作品目录> --user-authorized "<授权说明>"` 并在作品材料记录授权；参考作品默认不进入成片。

架构边界与模块职责见 [ARCHITECTURE.md](ARCHITECTURE.md)。

通用视频支持键盘、火花、电流、掠过、碰撞和提示等常见音效：代码合成与第三方直链／本地文件导入统一登记，通过音效 ID 按帧定位，支持裁切、循环、淡化与左右声像。第三方素材须提供来源、作者及明确许可，准备与渲染离线执行。命令为 `m2v general sounds catalog|import|audit`；配方、分镜字段和制作检查见[媒体与音效](.agents/skills/material2video/references/article-media-and-sound.md#统一音效库)，[键盘与火花演练](styles/doc-archive/examples/american-science-milestones/assets/SOUND_EXERCISE.md)提供可复现配方。

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

通用作品当前使用 `general` 类型和 v8 `storyboard.json`，画面入口是作品 `scenes/` 下的 TSX。旧通用材料不自动迁移，须按当前材料契约重新编排；修改材料后重新 `prepare`，再执行 `render`。

## 文档导航

- [material2video Skill](.agents/skills/material2video/SKILL.md)：按类型与任务/阶段调度，指向四份阶段指南和按触发条件展开的专项参考。
- [阅读路由](.agents/skills/material2video/references/guidance-routes.json)：阶段、任务、条件参考与规则归属的结构化清单；`sync_docs.py --check` 一并校验目标、锚点与阅读预算。
- [视觉创意导演方法](.agents/skills/material2video/references/visual-creative-direction.md)：集中维护视觉事件、导演顺序、视觉力量、逐场设计和验收方法；模板、反例与演练在[按需参考](.agents/skills/material2video/references/production-examples.md)。
- [视觉素材选择与使用](.agents/skills/material2video/references/visual-material-selection.md)：载体判断、素材检索、入片编排与替换复核。
- [看图诊断与形象判据](.agents/skills/material2video/references/explainer-design.md#看图诊断与形象判据)：症状→成因→改法、形象判据与主体尺度起点。
- [讲解设计](.agents/skills/material2video/references/explainer-design.md)：通用讲解画法、贯穿关系与长片章节递进。
- [代码场景运行时](.agents/skills/material2video/references/code-scene-runtime.md)：Painter、相机、数值轨道与动态能力货架。
- [媒体与音效](.agents/skills/material2video/references/article-media-and-sound.md)：本地素材、声音包络和主动留静。
- [ARCHITECTURE.md](ARCHITECTURE.md)：代码模块职责与依赖边界。
- [OpenSpec 规格](openspec/specs/)：已实现能力契约；[项目规划](docs/PROJECT_PLAN.md)：未来路线。

## 制作证据与状态

已有视频可通过制作助手的[修订入口](.agents/skills/material2video/references/video-revision.md)按修改意图继续制作：定位受影响场景与时间轴、保护旧版、复用有效方案和证据，实际查看局部修改效果并按[收敛判断](.agents/skills/material2video/references/production-workflow.md#再次全片生成前的收敛判断)汇总后生成下一全片候选，最后完整复核。入口串联现有命令，未新增修订 CLI 或自动影响分析器。

general 提供 G0–G6 检查点门、指定帧采集、DOM 状态/布局量测、隔离评审包、缓存粗片播放器、追加式制作历史与显式基线清理。`m2v status --history --json` 在既有技术状态之外显示 production 制作状态；门不新增导出硬门禁。合同格式、覆盖局限与操作见[检查点制作门](.agents/skills/material2video/references/checkpoint-gates.md)。新作品/后续重制适用制作合同 v2，v1 明确拒绝、不自动迁移；缺失独立证据不自动放行。

看图改图用 `m2v lookdev` 的四种取点模式：`--sheet 3.5 9 21.5` 按秒拼一张接触表，`--motion 8.2 10.6` 看区间转场，`--det` 核对同帧一致性，`--event compound:drop-1 --before 6 --after 6` 按幕内事件取发生前/关键帧/发生后/结果停留。事件模式从当前准备记录解析，窗口由作者用帧声明；事件簇会警告，越界会失败，不会自动绑定检查点。它们是预览工具，不成为导出门禁，也不替代 `m2v gates check` 的正式检查点证据；以上即当前预览模式用法，正式检查点仍用 `m2v gates check`。

v2 合同以 `reviewPlan.risks` 声明六类适用风险，审核人数和轮次由唯一策略派生：无核心未决风险的普通作品只需一次独立终审；有核心风险时，在扩展前增加适用核心评审。G5 内部检查记录范围、发现和未覆盖限制。独立评审覆盖表绑定适用门；状态查询分列自身结果、等待前置及真实过期。见[检查点契约](.agents/skills/material2video/references/checkpoint-gates.md)。

适用核心样片评审在扩展前、G5 内部粗片检查在阶段问题收敛前，分别作出通过、局部修复、补充试制或退回重设计的制作决策。设计机制、全片结构或技术路线存在有证据的根本失败时立即退回对应设计层，不必等两轮修复；保留原问题、限制受影响工作并经对应验证重新放行。决策复用现有失败与问题状态，不新增自动审美判定或导出门禁。触发条件与记录见[回退规则](.agents/skills/material2video/references/production-workflow.md#核心样片与全片粗片的回退决策)。

核心盲审覆盖表分别验证理解、表现与样片代表性；有目标图的核心实际片段须先盲审、后同轮独立对照，缺少或失败不授权扩展。独立评审必改项须凭当前同范围独立复查报告关闭。`status` 保留技术 `stage/candidate`，另用 `summary`、`production.complete` 和 `production.expansion` 区分候选生成、制作完成与可扩展检查点；这些条件不新增渲染硬门禁或用户审批。旧核心报告缺少新凭据时仅作历史，不自动补造通过。
