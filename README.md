# Material2Video（材料成片）

面向短视频的离线制作工具链，采用**通用代码、类型专属代码、具体作品代码**三层组织，并保持统一的制作入口。代码分层、模块职责与依赖方向见 [ARCHITECTURE.md](ARCHITECTURE.md)；项目当前能力见下方类型目录；制作流程和类型契约由 [material2video Skill](.agents/skills/material2video/SKILL.md) 及其参考文档维护。

## 当前视频类型

<!-- generated:type-catalog:start -->
**路线旅程**：以真实道路为骨架的路线与旅程影像：单段自驾行程与多日地图游记。
- `driving-route`：真实高速优先驾车路线、竖屏普通道路地图、无注记路网与市/县行政区标注、小车沿路行驶与 12× 平滑镜头跟随；顶部两行“模拟行程”标题，已行驶里程随车显示，在线取数与离线成片分离，1080×1920、30 fps、无声交付。
- `road-trip`：真实国道走廊、多日行程、每日章节卡与数据卡、旁白字幕音效与程序化音床；1080×1920 竖屏、30 fps、有声交付。

**未分类**
- `financial-timeseries`：股票、指数及 crypto 日线材料（含 USD/CNY 历史汇率折算）、假设投资计算、30 fps 暖近黑「持仓对账单」手机竖屏双层趋势曲线、主体优先标题、本金/期末市值收束区与可选 design 档案，完整候选自动验收。
- `general`：v8 全画布代码场景讲解：作品自行设计横屏或竖屏画面的配色、构图与动效，支持原文或主题输入、带来源留证的媒体导入、双来源音效库与本地音床，成片最长 600 秒。
- `building-construction`：以 v2 材料驱动、多镜头与构件级步骤的三维住宅建造示意；60 秒、1920×1080、30 fps、无音轨，默认机位可见入口与主要门窗。
- `vehicle-showcase`：本地汽车模型、自动环绕、影棚灯光与视觉疾驰；固定 1920×1080、30 fps、无声。
<!-- generated:type-catalog:end -->

风格示例：[从电报到大模型](styles/doc-archive/examples/american-science-milestones/README.md)、[复利](styles/count-ledger/examples/compound-interest/README.md)、[太阳系之旅](styles/deep-journey/examples/solar-system-journey/README.md)、[折叠](styles/vibe-night/examples/fold/README.md)、[鸽子的迷信](styles/vibe-fable/examples/pigeon/README.md)与[让积累，参与下一次](styles/dark-proof/examples/compound-connect/README.md)（40秒R5：数字、单个寓言、表格、折线、柱形与公式连续论证；[近期创作复盘](styles/dark-proof/examples/compound-connect/CASE_STUDY.md)，无旁白、无配乐，仅事件音效）。各示例的设计、来源、制作状态与验证见示例目录及其 `DESIGN.md`、`SOURCES.md`、`VERIFICATION.md`；当前能力与目录约定见[风格包目录](styles/README.md)。

通用视频的创作方法（视觉事件、导演设计、逐场设计与验收）集中见[视觉创意导演方法](.agents/skills/material2video/references/visual-creative-direction.md)；看图诊断见[看图诊断与形象判据](.agents/skills/material2video/references/explainer-design.md#看图诊断与形象判据)。

general 每场在目标确定后、动态实现前完成[逐场细节设计](.agents/skills/material2video/references/scene-detail-design.md)：在同一 `DESIGN.md` 编排主体、文字、图标/配角、光影点缀、镜头剪辑与声音，沿现有试制与审核分看关系成立及声明的表现目标，参考/重制比较同用途片段与基线；方法集中在[运动适配](.agents/skills/motion-design/ADAPTATION.md#逐场细节设计)。 dark-proof按段落选择硬切、动作匹配或对象延续，光效强弱与密度逐拍编排，不设全片固定次数上限。

制作载体选择见[素材选择规范](.agents/skills/material2video/references/visual-material-selection.md#视频优先与代码适用场景)；规则来源及文档维护边界见[架构说明](ARCHITECTURE.md#契约与文档)。类型清单、制作门及审核策略表由共享定义生成，运行 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` 可检查漂移。

讲解机制与实际表达复核已纳入制作指导：按需组织对象追踪、尺度变化、过程结果与回场，沿现有独立评审验证画面实际建立的关系；方法见[讲解设计](.agents/skills/material2video/references/explainer-design.md#四种讲解机制的执行方法)。注册风格和组件技术通过不代表成片表现通过。

general 讲解制作在现有逐场记录和时间线上协调贯穿对象、连续行为、画面事件与适用声音，并检查完整变化和观察窗口；具体方法见[贯穿对象、事件和完整动作](.agents/skills/material2video/references/explainer-design.md#贯穿对象事件和完整动作)。场景可声明 `content.props.capture.timebase: "global"` 获取全片时间，把连续行为写成一条不依赖幕 ID 的状态轨迹，各镜头只取景；声音与画面共用幕内事件，并用事件密度、增益、淡化与不同素材表达语义变化。写法见[全局时间与连续行为](.agents/skills/material2video/references/code-scene-runtime.md#全局时间与连续行为)与[声音语义](.agents/skills/material2video/references/article-media-and-sound.md#声音语义与事件化)。

可选 Canvas 绘制层的量测同步透明度、逐字显影、分组变换与裁剪，使用实际字形外框；完全不可见文字不会作为可见对象通过，部分裁剪明确报告失败。最终像素遮挡与可读性仍需视觉复核，见[绘制量测边界](.agents/skills/material2video/references/code-scene-runtime.md#绘制量测的可见性边界)。

Painter 另提供离屏 `layer()` 整体合成与纯数值关键帧 `keyframeAt()`；`web/gallery.html` 是只在开发服务器提供的动态能力货架，含可回放固定种子模拟，不进入作品或生产构建。通用声音支持可选全片增益曲线与声音设计层静音窗口；长片的编年、论证链和侧面探索方法见[讲解设计](.agents/skills/material2video/references/explainer-design.md#长片叙事结构)。

代码场景可声明 `content.props.capture.mode: "pure-time"` 走纯时间采集：任意帧直接 seek，按块并行采集后无损拼接，预览与 lookdev 不再回放前缀；纯性由静态源码闸门与正序/倒序 PSNR 双重验证，失败明确拒绝。`render --jobs N` 可进一步按帧区间分进程渲染。默认仍为顺序采集、单进程；写法与限制见[纯时间采集](.agents/skills/material2video/references/code-scene-runtime.md#纯时间采集opt-in)。

代码场景另提供共享 L1/L2 动效组件，覆盖入场、数据、文本排版、路径形变、遮罩揭示、圆弧进度、有机漂移、纯时间安全图表、时间轴、象形图与波形。组件只接收 `progress`/`easing`，通过 `m2v/code-scene` 使用，不直接依赖外部库；外部几何库的选型与使用边界见[共享动效组件](.agents/skills/material2video/references/code-scene-runtime.md#共享动效组件)。

general 制作采用「方案确定 → 制作与迭代 → 最终验收」三阶段；核心表达明确后可先做低成本画面原型，再补齐正式扩展所需设计。G5 全片粗片由制作助手内部检查；固定先做完整试制独立盲审，通过后再扩展；最终由未参与前期评审的新代理检查当前全片。终审区分实现与设计问题，设计失败退回对应设计层并重新验证；用户目标优先，具体方案可调整。入口见[制作与迭代](.agents/skills/material2video/references/stage-iterate.md)。同一材料可由连续构图完善到动态实现，通过后保留并逐段扩展。选案按未决问题比较，不固定候选数量；检查工具按需调用，完整证据与制作完成条件仍须满足。具体见[完整段落试制与逐段扩展](.agents/skills/material2video/references/production-workflow.md#完整段落试制与逐段扩展)。

## 快速开始

general 可声明幕内事件，由动画、计数、视觉强调和音效共同引用同一帧；prepare 输出绑定准备指纹的 `outputs/events.json`，改事件后重新准备。声明见[幕内事件](.agents/skills/material2video/references/storyboard-schema.md#幕内事件)，SDK 用法见[事件查询](.agents/skills/material2video/references/code-scene-runtime.md#幕内事件查询)。

```powershell
uv sync
pnpm -C web install
uv run python fonts/fetch.py
pnpm -C web build
uv run playwright install chromium
uv run m2v types
uv run pytest tests/common/test_single_pass_delivery.py # 按改动选择相关快测文件
pnpm -C web test
```

测试按影响范围选择，文件和目录默认排除 `media` 与 `slow`。需要真实媒体或渲染时明确选择相关节点或相关文件中的标记：

```powershell
uv run pytest tests/common/test_single_pass_delivery.py # 相关快测
uv run pytest tests/types/general/test_article_sound.py -m media # 相关媒体验证
uv run pytest tests/types/general/test_general_silent_output.py::test_real_delivery_streams_and_candidate_reuse # 明确慢测节点
```

`media` 用例需要 ffmpeg 真实编解码，`slow` 用例需要 Chromium、完整渲染或长时等待。指定 `文件::测试名` 只放开该节点的成本层，`-m` 在选定范围内覆盖默认过滤；CI 日常运行默认快层。本地缺少示例媒体时相关用例按既有约定跳过。示例内容由作品制作与验收维护，通用测试保留共享契约与关键边界。

全仓完整回归（`uv run pytest --full` 或分组覆盖全集）仅限用户明确要求，或人工在依赖与字体已准备好的环境中执行正式发布验证。重构、提交和 OpenSpec 归档不自动触发全量；详细约束见 [验证与交付](AGENTS.md#验证与交付)。

统一入口以作品目录为唯一归属：

```powershell
uv run m2v init --type general --project <slug> # 创建 videos/general/<slug>/，项目与分镜均默认横屏
# 有自身旁白时，先按下文选音并保存；手动制作可在 prepare 指定 --voice。
uv run m2v prepare --project videos/general/<slug>
# 可选局部片段检查：默认前十秒或显式短窗口，不能替代全片生成
uv run m2v preview --project videos/general/<slug>
# render 每次生成一个全片候选并自动技术验收；制作完成还须有效证据与适用评审。m2v review 是可选工具。
uv run m2v render --project videos/general/<slug> [--jobs N] # N>1 为进程级分段渲染
uv run m2v relocate --project videos/<old-slug> # 迁移旧作品源文件与全部产物
```

general 作品未配置旁白、音乐和音效时，预览与正式成片均不含音轨；有任一声音声明则保留原混音与验收流程。

只有事件音效的作品也按同一母版响度与真峰值目标校验；稀疏音效在实测峰值余量内校正增益，保留事件之间的数字静音。

有旁白的制作流程为：材料审查 → 编排旁白 → **制作助手自动选择音色并保存** → 校验与时间轴准备 → 按需检查生成与修改 → 全片生成一次 → 验收与复核 → 交付同一文件。助手读取当前音色列表并按内容选择，用户明确音色优先；全流程不要求播放视频、连续收听声音或试听音色，按类型使用静帧/时间标注帧序列、路径与画面量测、字幕及时间戳核对和自动音频信号分析。用户无需试听确认；有自身旁白但缺少 `tts.voice` 时 `prepare` 会阻断，也可用 `--voice` 手动指定。无旁白作品无需选音。字段、溯源与迁移见[配音音色与节奏](.agents/skills/material2video/references/voice-and-rhythm.md#配音音色与语速)。

作品及其全部 `outputs/` 产物按类型与类别分层存放：未分类类型为 `videos/<type>/<slug>/`，属于类别的类型为 `videos/<category>/<type>/<slug>/`（例如 `videos/route-journey/driving-route/<slug>/`）。仓库自带风格示例（`styles/<style-id>/examples/<slug>/`）的全部产物写在示例目录下的 `outputs/`，同样不入库。`init` 的相对参数填写 `<slug>`，也可传入完整的规范相对路径；使用仓库外内容根时，传入 `--content-root` 或设置 `M2V_CONTENT_ROOT`。`relocate` 面向位于 `videos/` 下非规范位置的统一契约作品（如 `videos/<slug>/` 或旧的 `videos/<type>/<slug>/`），按类型目录中的类别迁移到规范位置，逐个备份后移动源文件和产物；同名冲突文件不覆盖目标，解决后可重试。无 `project.json` 的旧文章内容不属于此迁移命令。目录归属、内容根与默认输出见[目录约定与输出路径](.agents/skills/material2video/references/paths.md)。

`init` 会生成材料模板，通用类型还会按类型目录写入起步场景 `scenes/opening.tsx`。通用作品先确定画幅与视觉设计（作品 `DESIGN.md`）、写 `scenes/` 下的本地场景，再完成源文审查与分镜；金融与自驾路线各自沿用专用材料契约。各类型的材料、编排与画面规则见[文档导航](#文档导航)。

多场景作品的 `lookdev` 静帧采集失败时，错误会给出场景 ID、入口路径及原始原因，便于定位失败场景。

纯时间并行采集仅在整组边界验证通过后发布分块缓存；失败重试不会复用未放行分块，边界失败帧会保存在作品诊断目录，见[纯时间采集](.agents/skills/material2video/references/code-scene-runtime.md#纯时间采集opt-in)。

多日地图游记使用一份 `trip.json`，每日路线在 `routes/day-XX.json` 并由 `trip.json` 引用；填写行程、旁白、卡片与事实来源后，设置 `M2V_AMAP_KEY` 执行 `uv run m2v road-trip fetch --project videos/route-journey/road-trip/<slug>`，再按授权执行 `basemap` 生成概览与每日跟随瓦片。之后 `prepare / preview / render` 全程离线，准备阶段合成旁白、字幕、音效与 30 秒程序化音床。画幅固定 1080×1920、30 fps、有声；材料形状、命令与画面契约见[多日地图游记](.agents/skills/material2video/references/road-trip-video.md)。

自驾路线使用独立的 `request.json` 与 `route.json`：填写起终点与来源使用依据后，设置 `M2V_AMAP_KEY` 执行 `uv run m2v driving-route fetch --project videos/route-journey/driving-route/<slug>` 取得真实高速优先路线；确认授权并置 `mapTiles=true` 后可执行 `basemap` 生成普通道路或卫星底图。之后 `validate / prepare / preview / render` 全程离线。画幅固定 1080×1920 竖屏、30 fps、无音轨，默认 30 秒；顶部两行“模拟行程”标题，车辆旁显示里程，市/县行政区标签由渲染层绘制。取数授权、材料形状与画面契约见[自驾路线视频](.agents/skills/material2video/references/driving-route-video.md)。

可选风格机制独立于视频类型：`uv run m2v styles` 查询注册包，作品通过 `project.json` 的 `style.id` 选择；当前六个正式风格包与各自的规范示例见[风格包目录](styles/README.md)，示例子树不参与风格指纹。示例各附 `DESIGN.md` 与 `VERIFICATION.md`，`vibe-night`、`vibe-fable` 与 `dark-proof` 另附 `HOWTO.md`；技术检查与理解观察分开记录。general 场景可显式使用参数、组件和资产，选择风格不会自动换肤。无旁白作品可在字幕安全区内自绘屏幕字幕；讲解方法与六种画法见[讲解设计](.agents/skills/material2video/references/explainer-design.md)。契约见[风格接入](.agents/skills/material2video/references/style-pack.md)。

## 命令

运行 `uv run m2v --help` 查看当前命令；类型专属材料和制作流程见 [material2video Skill](.agents/skills/material2video/SKILL.md)。

仅当用户明确要求复用整条参考音轨时，使用 `m2v ref audio <参考目录> --project <作品目录> --user-authorized "<授权说明>"` 并在作品材料记录授权；参考作品默认不进入成片。

抖音参考素材抓取默认走 yt-dlp；平台要求签名或新鲜 cookie 时，可提供 Netscape cookie 文件 `m2v ref fetch <链接> --cookies <文件>`；yt-dlp 仍无法提取时自动退回浏览器解析并输出明确日志，`--headed` 可打开可见浏览器完成登录或验证。

架构边界与模块职责见 [ARCHITECTURE.md](ARCHITECTURE.md)。

通用视频支持键盘、火花、电流、掠过、碰撞和提示等常见音效：代码合成与第三方直链／本地文件导入统一登记，通过音效 ID 按帧定位，支持裁切、循环、淡化与左右声像。第三方素材须提供来源、作者及明确许可，准备与渲染离线执行。命令为 `m2v general sounds catalog|import|audit`；配方、分镜字段和制作检查见[媒体与音效](.agents/skills/material2video/references/article-media-and-sound.md#统一音效库)，[键盘与火花演练](styles/doc-archive/examples/american-science-milestones/assets/SOUND_EXERCISE.md)提供可复现配方。

代码场景可按需使用 ELK 自动图示布局、KaTeX 离线公式与 Lucide 静态图标；共享图表、金融折线和暗场风格复用 D3 点列几何。general 合成支持方向化滑动、擦除、中心圆形与时钟式转场，复用现有重叠帧窗口和字幕时间轴。接口、字体恢复、许可与例子见[外部表达组件与转场](.agents/skills/material2video/references/visual-components.md)。

外部素材的制作期检查另有两个只读入口：`uv run m2v assets report --project <目录>` 交叉核对登记、场景引用与 `SOURCES.md`，写 `outputs/assets-report.json`；`uv run m2v assets contact-sheet --input <候选>` 把视频按时刻抽帧或多张图片拼成带序号的接触表。两者不联网、不导入素材、不替代 `prepare` 与 `assets audit`，用法与读法见[素材检索与台账](.agents/skills/material2video/references/material-sourcing.md#6-导入与台账)。

general 画面素材按对象检索：公司、产品和生产过程先查相关官网栏目及官方账号，再按缺口扩展来源；公开媒体直链或本地文件统一导入。Pixabay 是唯一启用的图库 API，横竖方向只作候选排序偏好。素材记录支持来源类型、发布主体、内容描述、可用片段和采用依据；默认按「检查后未发现明确禁止当前用途即可采用」执行，未知许可与未核实只提示，明确禁止或条件未满足阻断准备和审计，不把未发现禁止表述为已获授权。规则与字段见[采用政策](.agents/skills/material2video/references/material-sourcing.md#5-采用政策与署名)及[导入契约](.agents/skills/material2video/references/article-media-and-sound.md#来源与采用依据字段)。

素材选择按用途排序：真实事件和具体产品优先可追溯原件，准确关系与过程优先代码；当前代理支持生图时，定制插画、海报等静态任务优先考虑 AI 图片，再找合适的开放库／图库。生成图片沿用本地素材导入，保存提示词、工具和输出记录，不作实拍证据；细则见[来源优先级](.agents/skills/material2video/references/visual-material-selection.md#按用途排序素材来源)与[生成记录](.agents/skills/material2video/references/material-sourcing.md#ai-图片生成与记录)。

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

- [material2video Skill](.agents/skills/material2video/SKILL.md)：按类型与任务/阶段调度，指向三份阶段指南与修订入口和按触发条件展开的专项参考。
- [Frontend Design](.agents/skills/frontend-design/SKILL.md)：项目级视觉设计与反模板知识；视觉方向、字体、构图、层级与自我批评，视频语境见[适配说明](.agents/skills/frontend-design/ADAPTATION.md)。
- [运动设计](.agents/skills/motion-design/SKILL.md)：项目级运动设计知识；情绪意图、运动人格、时长、缓动、编排与质量检查，帧驱动边界见[适配说明](.agents/skills/motion-design/ADAPTATION.md)。
- [阅读路由](.agents/skills/material2video/references/guidance-routes.json)：阶段、任务、条件参考与规则归属的结构化清单；`sync_docs.py --check` 一并校验目标、锚点与阅读预算。
- [视觉创意导演方法](.agents/skills/material2video/references/visual-creative-direction.md)：集中维护视觉事件、导演顺序、视觉力量、逐场设计与全片原则、逐场表与必要附件式 `DESIGN.md` 模板；反例与演练在[按需参考](.agents/skills/material2video/references/production-examples.md)。
- [视觉素材选择与使用](.agents/skills/material2video/references/visual-material-selection.md)：载体判断、素材检索、入片编排与替换复核。
- [素材检索与台账](.agents/skills/material2video/references/material-sourcing.md)：来源层级、检索词、候选评估卡、许可决策与 `assets report`/`contact-sheet` 操作。
- [看图诊断与形象判据](.agents/skills/material2video/references/explainer-design.md#看图诊断与形象判据)：症状→成因→改法、形象判据与主体尺度起点。
- [讲解设计](.agents/skills/material2video/references/explainer-design.md)：通用讲解画法、贯穿关系与长片章节递进。
- [代码场景运行时](.agents/skills/material2video/references/code-scene-runtime.md)：Painter、相机、数值轨道与动态能力货架。
- [媒体与音效](.agents/skills/material2video/references/article-media-and-sound.md)：本地素材、声音包络和主动留静。
- [ARCHITECTURE.md](ARCHITECTURE.md)：代码模块职责与依赖边界。
- [OpenSpec 规格](openspec/specs/)：已实现能力契约；[项目规划](docs/PROJECT_PLAN.md)：未来路线。

## 制作证据与状态

已有视频可通过制作助手的[修订入口](.agents/skills/material2video/references/video-revision.md)按修改意图继续制作：定位受影响场景与时间轴、保护旧版、复用有效方案和证据，实际查看局部修改效果并按[收敛判断](.agents/skills/material2video/references/production-workflow.md#再次全片生成前的收敛判断)汇总后生成下一全片候选，最后完整复核。入口串联现有命令，未新增修订 CLI 或自动影响分析器。

general 提供 G0–G6 检查点门、指定帧采集、DOM/布局量测、隔离评审包、粗片播放器、追加式制作历史与基线清理；`m2v status --history --json` 显示 production 制作状态。合同、评审覆盖、回退决策、`lookdev` 取点方式与完成条件分别见[检查点契约](.agents/skills/material2video/references/checkpoint-gates.md)、[独立评审](.agents/skills/material2video/references/subagent-review.md)、[制作流程](.agents/skills/material2video/references/production-workflow.md)和[视觉复核](.agents/skills/material2video/references/visual-review-rubric.md)；这些工具不新增导出门禁。新作品/后续重制适用制作合同 v2，v1 明确拒绝、不自动迁移；缺失独立证据不自动放行。重制保留原周期已验证的历史问题闭环，当前周期仍须独立取证；历史未闭环或损坏证据不会因切换周期而放行。

通用制作以三阶段指南为操作入口，设计记录采用全片原则、逐场表与必要附件。G4普通窗默认半秒采样，已声明动态风险按节拍加密并强制覆盖事件/状态边界；完整过程视频保留，多尺寸图批量派生。G3可用 `gates check --gate G3 --timing-reports <输出根内G4报告> ...` 复用当前实际过程；未复用时只为时序风险镜头及相邻上下文生成animatic。来源过期或缺少独立观察仍保持未完成。详见[检查点契约](.agents/skills/material2video/references/checkpoint-gates.md#时序证据的生成与复用)。

逐场设计先明确可见变化与注意力路径；无旁白先排讲解文字和阅读窗口，再安排有用途的配角。参考按观看任务配对，核心试制优先覆盖本轮最弱或未决关系；理解、表现、相对旧版收益及参考目标分别复核。方法见[逐场细节设计](.agents/skills/material2video/references/scene-detail-design.md)，沿用既有审核轮次与证据边界。

G4 再次失败会重开原检查点问题，保留已有归因和受保护版本引用，避免返工记录丢失。
