# 三类默认风格调研

调研日期为 2026-11-28。先核查仓库契约，再按「信息载体＋移动观看＋可重复约束」比较各类的两个外部风格族。查阅原发布页、官方指南、原始图片和官方视频有序抽帧。下文逐条注明直接观察、发布者说明和证据缺口。抽帧时间为视频内秒数，稀疏采样只能证明可见状态及先后。未试听，也未运行项目渲染。原始媒体仅临时取证。推荐风格的英文名为项目规范名称，具体数值和禁用规则均是本项目拟定，实施时用原生样片核实。

## 仓库现状

- [类型目录](../../../src/m2v/type_system/catalog.json) v3 只有三类身份、说明和材料模板。[目录读取](../../../src/m2v/type_system/catalog.py) 在加载时验证目录版本及三类集合，初始化由 [scaffold.py](../../../src/m2v/standalone/scaffold.py) 复制独立模板。[作品加载](../../../src/m2v/core/project.py) 识别 project v3，明确拒绝 `style`，准备记录 v3 已用完整项目数据计算材料指纹。[schema.py](../../../src/m2v/core/schema.py) 提供严格结构校验，[validate.py](../../../src/m2v/core/validate.py) 提供手写基础校验，`src/m2v/core/` 下没有 `design_tokens*`。实际基础 CSS 令牌在 [web/src/styles/tokens.css](../../../web/src/styles/tokens.css) 等本地源码。Keynote 旧名的主规格只约束共享来源场景的实际令牌消费者。
- [主项目 CLI](../../../src/m2v/cli.py) 与 [独立 CLI](../../../templates/standalone/runtime/python/film_runtime/cli.py) 分工为委托与执行。[成片完整性](../../../src/m2v/engine/output_validation.py) 已核对解码与输出，独立的 [qa.py](../../../templates/standalone/runtime/python/film_runtime/engine/qa.py) 和 [qa_inspection.py](../../../templates/standalone/runtime/python/film_runtime/engine/qa_inspection.py) 才负责实片取样、冻结、字幕与音频等技术证据。开场、[总设计](../../../templates/standalone/DESIGN.md) 和 [场景设计](../../../templates/standalone/design/scenes/opening.md) 是起步材料。测试分散在类型目录、合约、QA、评审和三个示例，文件与后续验证见 [design.md](design.md)。
- 旧 [add-style-registry](../archive/2026-10-26-add-style-registry/design.md) 采用 `style.json` 发现、可选 `project.style`、`m2v/style` 导入和整包缓存摘要。随后有 `vibe-night`、`vibe-fable`，又从示例抽出 `doc-archive`（档案与信息叠加）、`count-ledger`（可数物证和状态）、`deep-journey`（深空连续旅程），再加 `dark-proof`（深色论证）。这些能力曾是可选择的包。可核对[三包提案](../archive/2026-10-29-add-three-style-packages-and-migrate-examples/proposal.md)、[寓言规格](../archive/2026-10-28-add-vibe-fable-style-and-examples/specs/vibe-fable-style/spec.md)和[暗场规格](../archive/2026-11-02-add-dark-proof-style-and-sample/specs/dark-proof-style/spec.md)。
- `ef0cac84` 在[当时的五类统一](../archive/2026-11-07-unify-five-video-types/proposal.md)时删除 `style-registry`、`vibe-fable-style`、`dark-proof-style`、`doc-archive-style`、`count-ledger-style`、`deep-journey-style` 和 `vibe-night-style` 主规格，删除 CLI `m2v styles` 与旧包入口。`openspec/specs/style-registry/` 在本机为空，Git 在该路径下没有当前受控文件。参见[注册表移除增量](../archive/2026-11-07-unify-five-video-types/specs/style-registry/spec.md)。`visual-expression-inspiration` 曾明确写自由采用、融合、自创或跳出，`8d63612a` 删除主规格；资料见[历史增量](../archive/2026-11-07-deepen-style-research-workflow/specs/visual-expression-inspiration/spec.md)。本提案采用固定默认和可验证约束，旧包的设计可用于理解遗留项目。

### AI 现在还能在哪自选风格或标杆

下表分清直接授权、沿工作流传递的自由度、具备输入能力的工具和仍可保留的创作选择。行号对应调研时仓库。

| 位置 | 原文摘录 | 现行含义与拟改 |
| --- | --- | --- |
| `openspec/specs/three-video-types/spec.md` | 「三类仅决定制作指导和默认目录」「不提供类别或风格层」 | 无类型风格默认。改为类型额外指定视觉规范，目录和类型路由维持单层 |
| `openspec/specs/reference-style-transfer/spec.md:33–35` | 「自主选择标杆」「助手 MUST 自主选择并说明具体参考用途」 | 直接授权自选。改为读取类型整体标杆 |
| 同文件 `:49–58` | 「用户明确或助手主动采用并承诺」「自主融合风格」 | 允许作者承诺和融合整体方向。改为固定整体目标加专项证据 |
| `openspec/specs/keynote-design-system/spec.md:7–8,52,70–72` | 「配色、排版、构图与动效由作品代码自行设计」「通用作品需要新的视觉风格」 | 本地执行权限缺少上游风格约束。保留本地实现并受生效规范约束 |
| `openspec/specs/independent-subagent-review/spec.md:59–61` | 「世界级风格开放品质与明确采用」「不强制苹果或其他固定品牌风格」 | 评审跟随作者所选。改用各类型规范有效范围 |
| `.agents/skills/material2video/SKILL.md:9,32,36` | 「代表场景试制建立实际视觉方向」「比较同场景设计后集中打磨」「世界级品质与风格开放」 | 顶层路由引到案例选方向。入口先解析生效规范，比较设计仍可进行 |
| `.agents/skills/material2video/references/stage-research.md:7,18,28` | 「以整片为单位调研叙事结构、视听语言和关键镜头」「需要选案时先小范围比较」「用户选定的整体风格覆盖受影响画面」 | 无用户指定时靠调研／试制定方向。改为试制证明固定方向中哪种方案最有效 |
| `.agents/skills/material2video/references/reference-video-analysis.md:5,16,18–24,104–106` | 「选择具体标杆」「可先筛出 3～5 个」「原创融合不要求复制全部特征」 | 整体与专项都能现场选。整体固定，筛选仍用于专项 |
| `.agents/skills/material2video/references/stage-design.md:11` | 「用新内容核对选定风格能否跨场迁移」 | 下游接受已选风格。更新为验证生效规范跨场适用 |
| `.agents/skills/material2video/references/scene-design.md:65,77,98` | 「优先展开可能改变全片结构、衔接或风格的片段」「与实际标杆仍有关键差距就继续处理」「原始要求与选案」 | 保留机制和画面解法选择，目标按规范与授权 |
| `.agents/skills/material2video/references/design-samples.md:9,27` | 「同轮实际目标对照通过」「AI 图片可以辅助构思、风格讨论和参考研究」 | 样品入口未固定默认目标；保留参考研究和原生交付边界 |
| `.agents/skills/material2video/references/production-workflow.md:9,31,36` | 「参考与内容不适合分别补查、修制作或重选方向」「比较实质不同的主体造型、构图、布光或表达机制」 | 返工存在重选风格的解释空间。保留重新选画面解法及专项补查 |
| `.agents/skills/material2video/references/video-revision.md:28` | 「先回到具体参考、深入拆解和本片转化」 | 修订复用／补查参考，补充生效风格与用户授权的来源 |
| `.agents/skills/material2video/references/visual-review-rubric.md:7–21` | 「苹果官网仅说明品质高度，不是指定风格或每部作品的必选参考」「每片选择实际可查看、适合方向的优秀作品」 | 主要的风格开放条文。数据类改为 Apple Keynote 指定风格，独立评审保留世界级标准 |
| `.agents/skills/material2video/references/review-contract.md:10,39–41` | 「所选风格的世界级成片完成度」「原始用户要求优先于作者转化」 | 评审目标的默认来源尚未约束。加入固定整体基准，继续保留用户优先和试制／正式分阶段判据 |
| `.agents/skills/material2video/references/review-protocol.md:35,45,87` | 「references 列出实际参考媒体路径」「用户明确允许换基准或改变采用目标时」 | 请求可提交任意目标，已有用户改靶保护。加入默认基准和授权绑定 |
| `.agents/skills/material2video/references/subagent-review.md:19` | 「世界级品质与风格开放」 | 修改评审锚点，保留隔离和真实观察 |
| `.agents/skills/material2video/references/visual-material-selection.md:111` | 「色彩、清晰度、文字、镜头运动和转场按整片视觉语言协调」 | 素材选择依从上游视觉语言；体裁、原始档案与政策约束照用 |
| `templates/standalone/RESEARCH.md:5,9`、`templates/standalone/DESIGN.md:9` | 「选定风格以世界级完成度为目标」「随研究与实际实现确定共同语言和选案」 | 起步材料保留现选方向的措辞，应改为先引用默认规范和已授权覆盖 |
| `src/m2v/production/review_tasks.py:27,40–43` | 「正式关键帧按所选风格」「不是固定风格」「实际标杆和原要求只在同轮对照中读取」 | CLI 生成提示接受开放风格。更新通用盲看提示和对照包目标 |
| `src/m2v/production/reviews.py:329–339,355` | 「按 conditions 区分整体品质标杆、专项目标与备选/历史比较媒体的用途」 | 提示区分用途，尚未要求自带类型标杆身份 |
| `src/m2v/cli.py:39,52–54,114–117`、`src/m2v/core/project.py:78–81` | 「列出内置视频类型」「初始化作品目录」「获取、校验抖音参考素材并提取授权音轨」「project.style 已移除」 | 当前没有风格选择 flag。通用参考获取和评审请求可承载作者选择，获取操作本身不指定整体风格 |

### 三个示例的视觉基线

| 作品 | 当前设计记录 |
| --- | --- |
| `data-evolution/global-market-cap-race-portrait` | 黑底偏轴金属环、冷暖边缘光、等宽数字，主舞台切到排名卡片，手机右侧和底部有暗区，无音轨。[DESIGN.md](../../../examples/data-evolution/global-market-cap-race-portrait/DESIGN.md) |
| `data-evolution/compound-after-20` | 蓝与琥珀玻璃、共享零线、逐年柱归两塔，原克隆声与双语字幕。[DESIGN.md](../../../examples/data-evolution/compound-after-20/DESIGN.md) |
| `spatial-3d/solar-system-journey` | 深黑、自然天体色、暖白和淡金，侧光、小补光，连续旅程，单列 Cassini、Blue Marble 等专项依据。[DESIGN.md](../../../examples/spatial-3d/solar-system-journey/DESIGN.md) |

## 共用规范尺度

下列像素是以短边 1080 为基准的设计单位，实现用 `S = min(width, height) / 1080` 乘出实际像素。字号斜线次序在各条注明。横、纵安全边距分别按画幅宽、高的百分比计算，遇字幕或已登记的平台叠加区采用两者中更严格的文字安全区。留白为稳定画面的画布面积中未被文字、数据标记和主体占用的比例，以机检可识别的角色几何或区域估计，复杂实拍和体积背景由独立评审判断清静区域，不能按背景色占比冒充。全出血素材可越安全区，关键信息不可越界。色板用 sRGB，强调数量只数项目绘制并承担强调语义的不同色，同一颜色的透明变化不重计。来源本色、字幕、依法或按既有规则需要的标识按其职责检查。必要正文以项目本地登记的 M2V Inter（拉丁）及 M2V Sans（中文）为默认，字体与许可仍按 [registry.json](../../../fonts/registry.json) 本地恢复。色彩不单独承担关键语义。

入场和退出秒数按实际输出 fps 用共享时序规则量化。这里的常规范围受现有分镜场长、声音、字幕和事实语义约束；如候选无法达到必要阅读窗口，应调该场编排或补证。硬切记 0 秒。播放单位或运动代表物理量时用真实模型或带标记的时间映射，装饰缓动不得改变模型。分别查看原尺寸与约 393 px 宽缩放帧，必要文字和数值在小屏稳定态必须可读。

## 图文动效 · IBM 2x Grid Kinetic Typography

### 候选与证据

1. **IBM 2x 栅格与工程化动效，入选。** 官方 2x 文档把画面基元按 2 的幂划分，动效指南要求保持主焦点、阅读方向和单轴运动。实际抽取 Sequential 动效的 0、0.5、1.2、2.4、3.4、4.5 秒：浅底中央纵横大留白，灰色 A–D 单行等距，蓝条从左进入，紫、粉、红随后依序接亮，之后字块移位并复归。构图固定而层级变化可读；抽帧支持先灰后彩、按序接力，不能量出原曲线。项目固定整体参考采用官方栅格／排版指南及该条 Sequential 媒体，颜色数量改为项目自身上限。[IBM 2x Grid](https://www.ibm.com/design/language/2x-grid/) · [IBM 动效指南](https://www.ibm.com/design/language/animation/tips-and-techniques/) · [Sequential 原片](https://www.ibm.com/design/language/videos/animation/animation-tt-sequential-wide.mp4)
2. **Google Material 3 Expressive。** 官方文章头部动图 0、0.7、1.5 秒是浅紫底、黑色居中粗标题；3 秒只见下方小环；5、8 秒白色两行标题处于大面积柔边彩色光团中，彩场明显变化。官方 motion 文档用物理弹簧区分用途。适合个性化 UI 和情绪表达，整段文字解说使用它的中心舞台和持续色域变化，主语句接力较难克制。[Google Design](https://design.google/library/expressive-material-design-google-research) · [官方动效说明](https://m3.material.io/styles/motion) · [头部原片](https://storage.googleapis.com/gd-prod/media/17f2f91c-7c4d-4344-b112-0cb33ef88cc9_better_easier_emotion_UX_header_00_16x9.mp4)

IBM 方向的网格和进入顺序适合文案、章节和抽象图形占主导的短片，小屏上优先交付一句话的阅读层次。品牌露出、代码语气和 IBM 演示的多色分配不移入项目。

### 可执行草案

- 浅底 `#F4F6F9` → 次要中性色 `#506070` → 主字 `#121820` 由亮到暗，可用 `#C8D0DB` 作线。强调在 `#0F62FE`、`#6929C4` 中每场最多 1 个，靠字号和实心边界明确主次。
- 主标题／次句／支持标签为 92／52／32，权重 700／600／500，最多两种字重同窗，主句至多两行。8 栏横屏，4 栏竖屏，横向安全边距 8%、纵向 9%，主要边缘对栅格，稳定态留白至少 35%。
- 图形采用纯色几何、线、箭头或下划线，每窗一组主句和最多两项支持；有量值时用直接标签与必要单位，图形不能抢走文字焦点。禁止伪代码装饰、渐变、描边字、单字拉伸、空转循环及多轴并发揭示。
- 入场 0.20–0.38 s，单轴裁切或位移，缓出；同语义接续 0.25–0.45 s，用同轴平移或硬切，离场缓入；组间隔 0.06–0.12 s，稳定读停至少 1.2 s。按实际语序揭示，禁弹跳或同时甩开多个读点。

## 数据演化 · Apple Keynote Presentation Style

### 证据与适用

- Apple 的 Keynote 官方主题选择截图可见白／黑简洁主题卡与同一界面内的彩色、纹理主题。图表选取截图可见同一网格内的二维条、折线与多色类别样式。官方文档明确主题配套颜色及字体，Magic Move 用跨页共享对象的连续变换承接状态。截图是静态，未实测 Keynote 软件对转场的默认秒数或缓动。[创建演示文稿](https://support.apple.com/guide/keynote/create-a-presentation-tan317e80e8c/mac) · [主题截图](https://help.apple.com/assets/6A89012DB8A442E3B007EABB/6A89012E7777AF96AB088730/en_US/f1c754de8900f4a168e6518950c9a42b.png) · [图表指南](https://support.apple.com/en-euro/guide/keynote/tan1a8924264/mac) · [图表选择截图](https://help.apple.com/assets/6A89012DB8A442E3B007EABB/6A89012E7777AF96AB088730/en_US/c44b827eab7d6dade3788548c4d3192f.png) · [Magic Move](https://support.apple.com/en-il/guide/keynote/tanff5ae749e/mac)
- Apple WWDC22《Design an effective chart》实际抽取 20、42、70、220、275、302 秒：70 秒构图左黑右实拍，标题与短句用白字分级；220 秒只留黑底中央一根亮蓝柱；275 秒左侧短标题和小图标围绕右侧空坐标框，302 秒版式保持并出现白色点列。支持「一屏一个揭示、把框架留给状态变化」，这些取点不足以量出转场曲线。WWDC 视频为固定整体演示参考，Keynote 官方截图与指南用于落实演示语言，HIG 用于坐标轴、刻度、网格、marks 和说明的语义校验。HIG 属于界面图表指导，视频规则由本项目提炼。[Apple WWDC22 原页及 SD/HD 下载](https://developer.apple.com/videos/play/wwdc2022/110340/) · [Apple HIG Charts](https://developer.apple.com/design/human-interface-guidelines/charts)
- 数据演化中的 Keynote 是用户明确指定的设计语言，使用上述可观察参考。旧条文「苹果官网仅说明品质高度」在通用审美意义上仍可用于其他作品的方法讨论，不能替代各类型正式整体基准。此方案采用简洁演示页族，Apple 的产品界面、素材、品牌标和商业字体均无需复制。

### 可执行草案

1. **双色底模式。** 默认浅底 `#F7F8FA`、主字 `#141518`、次字 `#515A68`、网格 `#D6DBE3`；已登记深底 `#101217`、主字 `#F5F7FA`、次字 `#ABB3BF`、网格 `#38414E`。浅底按底→线→次字→主字降亮，深底相反。默认用蓝（浅 `#0057C2`、深 `#66A8FF`），严格需要比较时另用琥珀（浅 `#8E4800`、深 `#FFB45E`）。同一帧最多 2 个强调色，普通系列及非焦点排名用中性色或不同线型。
2. **大字和字阶。** 本地 M2V Inter／M2V Sans，标题／主数／标签／轴刻度为 72／104／38／32，权重 650–750／650–750／500–650／450–550。数值启用等宽数字特性与统一小数精度，不加入 SF Pro、系统回退、装饰体或伪斜体。
3. **栅格留白。** 横屏 12 栏，竖屏 6 栏，横边距 8%、纵边距 9%，稳定态留白至少 28%。保持同一指标跨页对齐。竖屏市值示例继续在右／底平台遮挡带留安全空间；深底是该风格可登记模式。
4. **数据图形。** 单一主图使用平面条、线、点或同源分组。柱统一零线，负值显式向另一侧；对比窗共享数值范围和单位，线图确需非零轴时标出范围。最多 4 条浅参考网格线（不含基线）；主数值带单位，图形就近直标，确有必要才用图例。榜单可在精确直标和公共基线下省重复刻度。时刻、单位、排名和实际输入口径一致。幂次、截断或比例变化不得悄然隐藏。
5. **动效。** 进场 0.22–0.42 s 缓出，小幅位移或淡入；同一数据对象以身份连续，0.30–0.60 s 对象匹配缓入缓出，异主题硬切或 0.18–0.30 s 交叉淡化。柱长、读数、排名及尺度按同一数据模型和明确时间映射，纯演示进度无过冲，不暗示不存在的测量值。最终结果与必须比较的稳定窗各保留至少 1.4 s。
6. **信息与禁用。** 一屏一结论、一主图、最多两项辅助说明；完整排行榜可显示任务要求的条目，但只有一处主强调。禁立体透视条、反射玻璃／金属冒充量值、霓虹、装饰渐变和爆炸／翻牌式转场。数据源码、单位与标签都正确且画面达到整体完成度后才通过。

## 三维空间 · NASA SVS Scientific Visualization

### 候选与证据

1. **NASA SVS 数据驱动空间可视化，入选。** SVS《Moon Essentials》经 NASA Science 提供的经向天平动成片，实际抽 0.5、3、8、13、19、24 秒。黑底右侧青色环与地球中心是全景，左侧局部是月球近景，上部月球球体有轴线。轨道、读数或标签主要贴在对应图形附近，红、白位置标识可分别追踪，主体受光随状态变化。视图在各取点保持稳定，时序推进由物体移动表达。整体固定参考用该片与官方素材页。SVS 另一个《Moon Phase and Libration, 2025》正文可读，但直接媒体地址 403，未用它证明画面和运动。[NASA Science 原页](https://science.nasa.gov/resource/moon-essentials-from-nasas-scientific-visualization-studio/) · [经向天平动原片](https://assets.science.nasa.gov/content/dam/science/psd/earths-moon/video-thumbs/libration_longitude_1080p30.mp4) · [月相发布页](https://svs.gsfc.nasa.gov/5415/)
2. **ESO/SpaceEngine 天文电影式演示。** 实抽 S2 轨道动画 1、5、10、15、20、27 秒。1 秒稠密青线横穿星场，5 秒起独立椭圆位于中央，焦点小光点沿轨道进动，左下红色圆表与白色数值提供尺度，背景恒星纹理贯穿。视觉戏剧性较强，但小屏上的角落读数和开场线密度更适合专项证据。选择 NASA 的空间层级，更容易迁移到体积关系、结构剖面和非天文工程。[ESO 原页](https://www.eso.org/public/videos/eso1825g/) · [ESO 原片](https://cdn.eso.org/videos/medium_podcast/eso1825g.mp4)

### 可执行草案

- 技术底 `#080D14`、次层 `#92A1B3`、主字 `#F0F4F8` 由暗到明，最多两个测量或导引强调色 `#62C8D2`、`#FFC979`。主体维持自然材质或有记录的伪彩尺度，来源纹理不计强调色。使用可读的主光、补光与轮廓，抑制光晕。
- 对象名／结论／标尺为 64／44／32，权重 650／550／500。横 12 栏、竖 6 栏、安全边距 8%／9%。主对象运动范围不压文字，经常使用 7:5 横向主体／注释构图，竖屏堆叠。典型姿态保留至少 25% 安静区域，技术爆炸图的留白由实际构件和标注判定。
- 一对象或一组关系为主，至多两个同时解释的引线，选中构件高亮须有轮廓或清楚标签。保留空间锚点、明确相机与物体各自运动；比例、速度或时间压缩可能误导时按既有小字规则交代。结构比材质噪声优先。
- 标签进场 0.18–0.32 s 缓出；建立到揭示的镜头过渡 0.70–1.60 s，位置／视线平滑缓入缓出，模型运动按数据或已登记映射。远近交代后静读至少 1.2 s；断地点允许以明确切点及新锚点硬切。禁甩镜、滚转、无动机辉光、镜头污渍和 HUD 噪声，不用假尺度、错位物体或隐藏切换暗示连续空间。

## 证据边界与复核

可核对的原媒体 SHA-256 如下。实施时复取同字节或登记实际可核验的参考摘录及其摘要；如果来源变化，先报告缺证，由用户决定是否需要改变整体目标。Apple 视频按官方 HLS 640×360 档下载对应分段，只核对上述时点，正式分段或独立参考材料须补摘要并封存。

| 原媒体 | SHA-256 |
| --- | --- |
| IBM Sequential | `0b1562ee397ba170e4a2e492f9501a3b6023a69b515edecf573dc4a5fc084c82` |
| Google Material 3 Expressive 头部 | `ce08ad4460230d45dd46bbca4c812317b114b6787a56c2ece54799f42e2e2c8b` |
| Apple Keynote 主题截图 | `c587679f2f4e0cc9a1eb169d1038ba03254ee5a5212a59741241c0b9414ed6b3` |
| Apple Keynote 图表截图 | `64217721d24b5b98c291870dc94fd52bdece5691e430c36fc08319b07474e871` |
| NASA SVS 月球经向天平动 | `6aaef5cf5bcf00d5914b1c880d5eaab8853699c0e162d3e04f4077daca0e8f98` |
| ESO S2 原片 | `04113276d553c8d0503fd23c909e3012fe1e7fbc6209fcd4fd447745a812852b` |

Apple Keynote 应用 Magic Move 本轮为官方说明，实际动态观察来自 WWDC 演示。NASA 月相直链缺证，同机构的经向天平动已有实际动态。IBM 与 Google 已有官方短片的稀疏抽样，所有来源曲线和项目阈值仍需以适用原生试制校准。研究材料不构成项目成片的通过证据。

## 对用户的汇报摘要

建议默认采用 IBM 2x Grid Kinetic Typography（图文）、Apple Keynote Presentation Style（数据，用户已指定）及 NASA SVS Scientific Visualization（三维）。以类型目录映射和作品本地规范快照固定目标，用户指令才可覆盖。项目 v4、目录 v4、准备 v4，分镜保持 v9。量化 QA 与独立世界级评审均须通过。待确认两个待定风格，以及是否明确指定某部存量作品沿用已采用的原风格。提案所列视觉数值待原生验证，外部证据覆盖按各条记录。
