## 研究范围与取证方式

本提案把类型默认风格定义为带修订号的公开参考集。整体标杆用真实成片或官方演示观察完成度及整体语言，专项参考用于明确的设计机制，官方规范提供语义与工艺依据。发布映射及工程绑定见 [design.md](design.md) 和 [默认风格规格](specs/type-default-style/spec.md)。

本轮于 2026-11-28 通过 `curl.exe` 请求原页及证据地址并记录跟随跳转后的 HTTP 状态。实际打开页面正文、官方截图和有序视频抽帧，以下时间码仅用于复找原作品的观察位置。摘要针对本轮收到的原始媒体、文档或明确标注的本地摘录。核对副本保存在系统临时目录 `m2v-style-2026-11-28`，原页和证据地址可用于复取，仓库提交只保留文字登记。正式验收应封存该轮实际使用的参考证据和摘要。

## 图文动效 · IBM 2x Grid Kinetic Typography

### 候选与取舍

选择 IBM 方向。品牌成片提供从开场到收束的一体化文字叙事，官方 Sequential 演示能单独核对焦点接力，网格和字体指南补足排版工艺。把这些观察转用于中文短片的句子层级、图文同排及阅读推进。成片中的商标、品牌文案与操作语气属于原项目。

Google Material 3 Expressive 作为候选。原页和头部视频均为 HTTP 200，抽帧见居中黑标题经空场和回转图标切到柔和彩场上的白色标题。它适合强调品牌情绪和界面状态，本类型优先选择更容易迁移到连续讲解的对齐和语句接力。[Google 原页](https://design.google/library/expressive-material-design-google-research) · [官方头部视频](https://storage.googleapis.com/gd-prod/media/17f2f91c-7c4d-4344-b112-0cb33ef88cc9_better_easier_emotion_UX_header_00_16x9.mp4)

### 默认参考清单

| id | role | url 与 HTTP | scope | observed | evidence | accessedAt | sha256 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ibm-lets-create` | 整体 | [Ryan Quigley 的 IBM《Let's create》原页](https://www.ryanquigley.work/ibm-letscreate) · 200 | 主句主导时的整体构图、阅读推进、跨句一致性与收束完成度 | Cursor 成片从浅底左侧的孤立光标开始，在同一左侧锚点依次排出短句，片尾以蓝色 IBM 标志收束。 | [原页内嵌的 Cursor 成片](https://player.vimeo.com/video/679271031?h=a284b519f8) · 200，抽帧覆盖开场、短句更替及片尾，定位点 00:03、00:19、00:23、00:26、00:28 | 2026-11-28 | 本地抽帧联图 `f8f549c0a2c9d5fb08b422db5c02247675aaf12b3ae27f953c6a94a0f96f3cbc` |
| `ibm-grid` | 专项 | [IBM Design Language · 2x Grid](https://www.ibm.com/design/language/2x-grid/) · 200 | 图文跨镜对齐、标题与支持内容在不同画面中的组织关系 | 指南用界面、印刷品和视频案例讲解如何以同一栅格组织文字与图形。 | 官方文档，Divisions of two 与 2x Grid for video | 2026-11-28 | 原页响应 `ea972870f3ac83e70a18f4260cbf1cc4ae8910e8ceae0a875da5a45c0dcef2dd` |
| `ibm-sequential` | 专项 | [IBM 动效指南](https://www.ibm.com/design/language/animation/tips-and-techniques/) · 200 | 揭示顺序、阅读方向及焦点依次交接 | Sequential 演示的灰色字母条被从左进入的彩条依次点亮，随后字块移位并回到待揭示状态。 | [官方 Sequential 原片](https://www.ibm.com/design/language/videos/animation/animation-tt-sequential-wide.mp4) · 200，抽帧覆盖起始、接亮、移位与复归，定位点 00:00.0、00:01.2、00:02.4、00:03.4、00:04.5 | 2026-11-28 | 原片 `0b1562ee397ba170e4a2e492f9501a3b6023a69b515edecf573dc4a5fc084c82` |
| `ibm-type-basics` | 规范 | [IBM Design Language · Type basics](https://www.ibm.com/design/language/typography/type-basics/) · 200 | 文本层级、对齐、阅读连贯性 | 文档以左对齐、调整行间距及主副标题的示例说明排版怎样帮助阅读。 | 官方文档，Flush left、Leading 与 Titles and subtitles | 2026-11-28 | 原页响应 `6a1a3ae438efa215be618f5324b1f661bc8cab5f05a0f9ed539edb93df261bf5` |

**证据缺口**　Cursor 与 Sequential 取点支持语句更替和先后顺序。中文断句、字幕同窗和小屏阅读需用本片画面验证。音频、原片缓动曲线及中间读停的细节无本轮证据。

## 数据演化 · Apple Keynote Presentation Style

### 候选与取舍

沿用用户指定的 Apple Keynote Presentation Style。Keynote 主题选择器同时展示简洁演示主题、彩色主题及纹理主题。选用简洁演示方向，便于观察图表、读数和讲解本身的层级。整套参考里，WWDC22 提供变化中的实际讲解，Keynote 官方指南提供演示页与图表对象实例，HIG 提供图表语义与可读性的依据。只使用主题截图会缺少图表演化过程，只使用 HIG 会缺少演示完成度证据。

### 默认参考清单

| id | role | url 与 HTTP | scope | observed | evidence | accessedAt | sha256 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `apple-wwdc-effective-chart` | 整体 | [WWDC22 · Design an effective chart](https://developer.apple.com/videos/play/wwdc2022/110340/) · 200 | 演示页的焦点和完成度、讲者与图示的分工、图表从铺垫到揭示的整体节奏 | 演示从讲者与标题分区切到黑底独立图形，并在讲解示例中先呈现空坐标框，再在同一图区揭示白色点列。 | [官方 SD 视频](https://devstreaming-cdn.apple.com/videos/wwdc/2022/110340/3/B5BDA6B6-597F-460B-A88C-959265B6715D/downloads/wwdc2022-110340_sd.mp4) · 200，续传 206，定位点 01:10、03:40、04:35、05:02、09:20、12:13 | 2026-11-28 | SD 原片 `2cfed6bdbe20b2165aa4348cff063137a8dff1c2bd1684122224b5bd57c81c31` |
| `apple-keynote-themes` | 专项 | [Keynote 官方主题指南](https://support.apple.com/guide/keynote/create-a-presentation-tan317e80e8c/mac) · 200 | 主题内页面语言的连贯性，标题及内容页如何共享视觉关系 | 主题选择器中简洁的白底和黑底卡片与彩色和纹理预览并列，正文将主题说明为预设的幻灯片布局组合。 | 官方文档 Create a presentation from a theme 及[主题选择器截图](https://help.apple.com/assets/6A89012DB8A442E3B007EABB/6A89012E7777AF96AB088730/en_US/f1c754de8900f4a168e6518950c9a42b.png) · 200 | 2026-11-28 | 截图 `c587679f2f4e0cc9a1eb169d1038ba03254ee5a5212a59741241c0b9414ed6b3` |
| `apple-keynote-charts` | 专项 | [Keynote 官方图表指南](https://support.apple.com/en-euro/guide/keynote/tan1a8924264/mac) · 200 | 演示页图表对象的选择及不同数据形态的呈现 | 图表选择器并排展示柱状、条状、折线和点状等图形，正文按图表种类说明插入和编辑方式。 | 官方文档 Add a column, bar, line, area, pie, donut, or radar chart 及[图表选择器截图](https://help.apple.com/assets/6A89012DB8A442E3B007EABB/6A89012E7777AF96AB088730/en_US/c44b827eab7d6dade3788548c4d3192f.png) · 200 | 2026-11-28 | 截图 `64217721d24b5b98c291870dc94fd52bdece5691e430c36fc08319b07474e871` |
| `apple-hig-charts` | 规范 | [Apple HIG · Charts](https://developer.apple.com/design/human-interface-guidelines/charts) · 200 | 图形标记、尺度、坐标轴、刻度、网格、注释与信息优先级 | 指南以带标注的柱状图解释图表构成，并分别讨论标记选择、坐标范围及解释性标签。 | 官方文档 Anatomy、Marks、Axes、Descriptive content 及 [Apple 提供的 Markdown 正文](https://developer.apple.com/design/human-interface-guidelines/charts.md) · 200 | 2026-11-28 | 官方 Markdown `0ebc57b531afb305b5e7cf1b4325fece56d10a36506b2c6258bcb0ebe7039a81` |

**证据缺口**　Keynote 截图只支持静态观察，实际数据变化的演示证据来自 WWDC22。引用的取点未覆盖 Keynote 软件的过渡机制。具体项目仍应取证核对数据口径、共同尺度和当前观看条件下的阅读效果。

## 三维空间 · NASA SVS Scientific Visualization

### 候选与取舍

NASA SVS 的经向天平动作品把全局、局部和受光状态放进同一个空间叙事，适合迁移到天体、构件或剖面的关系讲解。ESO 的 S2 比较适合借用「先交代复杂系统、再隔离目标」这一专项机制。其密集的轨迹开场和角落读数在小屏上的可辨性需要另查，因此由 NASA 成片担当整体标杆。NASA 的显示规范补充技术标记与对象、读数和单位的归属关系。

NASA SVS《Moon Phase and Libration, 2025》备选原页返回 HTTP 200，官方媒体直链 HEAD 返回 403。本轮该备选缺动态证据，移出默认集。[NASA SVS 原页](https://svs.gsfc.nasa.gov/5415/) · [探测的官方媒体](https://svs.gsfc.nasa.gov/vis/a000000/a005400/a005415/phases_2025_fancy_360p30.mp4)

### 默认参考清单

| id | role | url 与 HTTP | scope | observed | evidence | accessedAt | sha256 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `nasa-libration-longitude` | 整体 | [NASA SVS · Moon Essentials](https://science.nasa.gov/resource/moon-essentials-from-nasas-scientific-visualization-studio/) · 200 | 全景与近景的空间层级、连续状态、材质光照及科学解说的整体完成度 | 经向天平动成片同时展示地月轨道全景、月球局部和带轴线的球面视图，红白位置标识随轨道状态分离又接近。 | [NASA 官方经向天平动成片](https://assets.science.nasa.gov/content/dam/science/psd/earths-moon/video-thumbs/libration_longitude_1080p30.mp4) · 200，定位点 00:03、00:08、00:13、00:19、00:24、00:41、01:04、01:28 | 2026-11-28 | 原片 `6aaef5cf5bcf00d5914b1c880d5eaab8853699c0e162d3e04f4077daca0e8f98` |
| `eso-s2-orbit` | 专项 | [ESO · Animation of the orbit of the star S2](https://www.eso.org/public/videos/eso1825g/) · 200 | 从多轨线场景聚焦到单一轨道，保持空间锚点和动态读数归属 | 成片开场的密集轨道线让位给星场中央的单一椭圆，亮点沿轨道推进，左下读数同步变化。 | [ESO 官方成片](https://cdn.eso.org/videos/medium_podcast/eso1825g.mp4) · 200，定位点 00:01、00:05、00:10、00:15、00:20、00:27 | 2026-11-28 | 原片 `04113276d553c8d0503fd23c909e3012fe1e7fbc6209fcd4fd447745a812852b` |
| `nasa-display-standard` | 规范 | [NASA · Display Standard](https://www.nasa.gov/reference/appendix-f-vol-2/) · 200 | 技术标签、读数与单位归属，以及结构示意的可辨性 | 规范在 Labels、Numbers 和 Schematics 中分别说明标签靠近数据、读数显示相应单位、结构对象具备可识别标记。 | 官方文档 Appendix F 的 Display Components 相关小节。适用范围为显示可读性语义。 | 2026-11-28 | 原页响应 `488c51138ec635336d6b87ef68b9e97868907e9168ae67c91894114612ef1ace` |

**证据缺口**　NASA 多视图抽样覆盖空间关系与状态，ESO 抽样覆盖聚焦前后及轨道推进。镜头连续性的具体做法、不同画幅的标注遮挡和其他题材的比例读法应由对应作品实证。

## 迁移前的作品基线

| 范围 | 当前线索与复核起点 |
| --- | --- |
| 市值榜横跨排名交接的竖屏示例 | 黑底金属环、边缘光和等宽数字。先复核读数、图表与换榜时注意力的接续。[示例设计](../../../examples/data-evolution/global-market-cap-race-portrait/DESIGN.md) |
| 复利示例 | 蓝与琥珀玻璃、共享基线、逐年柱汇成终值，配原克隆声与双语字幕。先复核比较关系和图表揭示。[示例设计](../../../examples/data-evolution/compound-after-20/DESIGN.md) |
| 太阳系示例 | 深色背景、自然天体色和连续旅程，已有 Cassini 等专项证据。先复核远近视图接续和名称归属。[示例设计](../../../examples/spatial-3d/solar-system-journey/DESIGN.md) |
| 仓库本地作品内容根 | `videos/<type>/<slug>/` 当前发现 17 份工程清单，其中 v3／分镜 v9 的候选 6 部（数据 5 部、图文 1 部），另有使用旧类型或旧契约的 11 部。本轮环境未发现 `M2V_CONTENT_ROOT`。实际现役状态、重复项和其他内容根需按交付记录逐部确认。 |

本轮取证说明参考可复核。示例及现役工程的成片完成度由后续逐部对照验证，制作调整量按发现的差距估算。
