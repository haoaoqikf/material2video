# 太阳系之旅 · 一镜到底设计

旧检查编号与报告仅保留为历史记录，不构成当前媒体评审体系的通过；本次未补造独立评审。
本轮合并设计记录和执行引用，未重新渲染或补造独立评审；历史观察只作原版本依据。来源与许可继续按 [SOURCES.md](SOURCES.md) 及既有登记执行。

## 全片原则

### 内容、画幅与配色方向

面向手机观看的入门观众，1920×1080、60 fps，统一制作。当前动态预算候选为174.55秒（10473帧），预算以高密度帧序列和量测复核，不要求播放；从太阳系上方开场，连续俯冲到太阳，再沿向外螺旋介绍15个站点/结构，每站给出身份与一个印象。比较明亮天文图鉴与深空旅行纪录片，采用后者：安静、好奇、逐步壮阔；图鉴方向适合数据比较，但会削弱本片的空间与探索感。

自然天体色、深黑背景、暖白正文和淡金导航；Noto Sans SC/Inter。主体在中央偏右，名称与一个短提示位于左侧，避免信息卡堆叠特征。侧向太阳光与少量环境补光保留轮廓，限制Bloom和景深，木星继续关闭Bloom。开场太阳、核心土星和结尾奥尔特云为三张构图基准；地球、土星、奥尔特云分别承担亲切、壮阔与遥远感。

### 核心体验与时间预算

| 条目 | 观察目标 | 失败现象 | 证据方法 |
|---|---|---|---|
| S01 连续穿行 | 离场、空间移动、抵达过程可辨，主体有观察时间 | 位移挤在短促加速中，天体像被快速变焦替换 | 全片动态粗预演、风险过程加密帧、当前实际相机测量与前后对照 |
| S02 自然承接 | 视线贯穿过场，方向与尺度变化有准备 | 半秒甩头、天顶附近朝向翻转、到站一闪而过 | 最远移动/最大转向/短停留全过程，三个hero、开场及结尾专项 |
| S04 独立天体空间关系 | 每次独立行星换站均表现为彼此分离的目的地；母星与卫星仍显出从属关系 | 独立行星以近景尺度同时出现或显得紧挨，如木星与土星构成伴星错觉 | 全片时间标注帧序列与风险加密帧；对照时间码、世界位置、屏幕尺度及母星—卫星关系。接触表仅作索引 |
| S05 转场信息密度 | 离场、跨站、接近各段时长与实际运动和信息相称，旅程连续且无重复等待 | 运动虽平滑但长时间没有新信息，重复拉远，或为了压缩而高速掠过 | 高密度帧序列结合逐帧相机/屏幕量测，逐段记录预算、目标尺度变化、相邻帧位移、停留时长与运动目的；不要求播放 |

#### 问题登记与当前版本关闭状态

| ID | 用户反馈与时间范围 | 当前已知事实 | 原因状态 | 关闭证据 |
|---|---|---|---|---|
| S04 独立行星挤靠 | 用户指出旧版镜头转向木星和土星时画面像两者紧挨；用户未提供精确时码。旧版留档重点复核范围为 110.35–125.00 秒，只作为查找线索，未确认它就是问题发生的准确区间。绑定旧版预演摘要 `86d08cd5…` | 旧压缩布局中木星轨道38、土星轨道51，中心间距约17.2世界单位；半径分别2.2和1.85，旧版无独立行星屏幕空间关系验收项 | 空间压缩与画面视角是待验证原因，不写成已定位根因 | **当前版已关闭**：绑定准备指纹 `5b3a1f5e…` 和交付 SHA `d96955bc…`。木星→土星 85.6–89.1 秒（帧5136–5346）全片序列及风险帧显示两个独立目的地分离；木星卫星、地球—月球仍显邻近。 |
| S05 过场等待过长 | 用户反馈天体之间部分过渡太慢；具体过场与精确时码通过新版高密度帧序列与量测定位。基线为同一旧版预演摘要 `86d08cd5…` | 旧版14段均为540帧（9秒），每段统一由1.5秒尾留白、5.5秒空间过场和2秒接近组成 | 统一预算可能造成无信息等待，是待验证原因 | **当前版已关闭**：绑定同一准备指纹和交付 SHA。10473帧/174.55秒的全片序列（0.5秒基线共1595样本）及转场加密帧逐段对照运动窗口与主体尺度，未见重复等待、回摆、瞬移或突兀甩头；采样间风险作为限制披露。 |

旧版135秒是问题基线，不作为本版本验收结论。220.5秒与统一540帧段间预算属于上一版历史数据，不作为新版目标。新版分别核定站内离场、跨站、接近和观察时间；以动态粗预演对应的高密度帧序列、屏幕/路径量测确认空间关系清楚、过程可辨且没有重复等待后锁定预算，不按统一秒数套用。总片长仍遵守600秒上限。站点/过场窗口须连续覆盖，不把赶路计入hero观察时间。

### 时间与运动实现

全片仍为单幕、同一个三维世界，无切换、叠化和硬切。原始路径相接只是基础；`flight.ts` 对跨镜头位置作帧驱动的对称时间滤波，诊断、粗预演和正式画面使用同一个求值器。视线按离站后段到到站前段的完整窗口进行固定端点四元数插值，避免移动目标导致最短弧分支翻转。正式相机FOV为44度，开场55度在末2秒平缓归一，不在各站反复变焦。

速度隆起贯穿整个阶段，不再把位移挤到中间40%。远入与远出点沿近景同侧延伸，避免旧版近乎垂直升到天顶后翻转。主序天体仍按半径与方位角向外螺旋排布；跨站路径升离黄道面。当前交付已增大独立行星的布局分离，重点木星和土星中心间距由约17.2增至26.3世界单位；木星—木卫二、地球—月球及土星—土卫六卫星局部轨道保持不变。全片时间标注序列覆盖完整片长，基线每0.5秒一帧，并在hero、镜头交界与风险处按0.1秒间隔加密；序列复核显示木星→土星等独立行星过场空间分离清楚，代表卫星关系保留。三个hero代表静帧符合构图意图。土星跨环平面弧按旅行方向使用，所有相机路径均重新复核。

粗预演使用同一相机、简化球体、目标画幅、低帧率与临时声音；无需播放或试听音色。逐段记录离场/跨站/接近时长、画面空间关系、运动目的及重复等待。逐帧诊断与实际画面共用相机求值器，记录位置速度、加减速、转向、FOV变化、天体安全余量与每个镜头的主体屏幕尺度；量测仅提示运动风险，不自动判审美。静帧检查构图和空间关系，密集时间标注帧序列结合量测复核动态节奏；接触表仅作索引。每条证据记录注明实际方法、版本、时间范围和采样限制。证据覆盖充分时可关闭对应问题，不将采样间瞬时运动或主观听感描述为已验证。用户针对当前具体问题与片段的反馈可补充记录，但不构成播放门禁。

### 声音

当前服务返回晓晓Warm、News/Novel标签，适合温暖导览，基于完整旁白重新选择；保留−2%及既有停顿，无需试听。先核查旧音轨：原音乐床gain−30dB，讲话包络还压低10dB，且低频为主；对照独立轨与旧成片量测后记录结果，不以设置单独宣称根因全部查明。

原创配乐按当前分镜时长生成score.wav采用同一旋律主题，开场缓慢建立、内行星温暖、巨行星增强、外行星疏朗、末尾收束。中频旋律提升小扬声器可感知性；音乐源归一到−18LUFS，混入增益−2dB，讲话时沿用共享−10dB包络，观察窗恢复。实际混音后检查，不把固定差值当听感保证。只在土星与日球层两处保留少量音效，所有太空声音为艺术设计；统一制作保持−14LUFS/−1dBTP。

### 参考与风险

2026-10-19重新访问核对NASA太阳系概览、奥尔特云资料及Cassini土星逆光资料：
- https://science.nasa.gov/solar-system/ ：天体身份、由内向外的介绍顺序。
- https://science.nasa.gov/solar-system/oort-cloud/facts/ ：推测性外层结构与尺度边界。
- https://science.nasa.gov/photojournal/the-day-the-earth-smiled/ ：土星环层次、暗面与逆光关系。

这些是事实及视觉对照入口，不意味着已观看所有运动/声音参考，也不是素材入片授权。纹理来源与许可见SOURCES.md；配乐/音效为原创合成CC0。所有天体大小、距离、亮度、自转和外层粒子为艺术示意；奥尔特云未直接观测证实。平台遮挡未实测，手机检查不宣称官方安全区。

剩余限制：抽样帧之间的瞬时运动不能由0.5秒基线样本完全证明；QA claims字段只覆盖镜头窗口且自动`visibility=not-evaluated`，内容可见性由当前静帧复核记录，不宣称机器判定；口播自然度、误读及音乐感染力未验证。相机路径、速度、转向与穿越有10473帧技术量测；冻结画面、字幕配置、响度和同步检查通过。阶段与问题证据记录于当前交付目录visual-notes.md，并绑定实际准备指纹和文件摘要。全流程不要求播放视频、连续收听声音或试听音色。

### 后续设计与评审应用（2026-10-23，非重制记录）

本节仅示范后续采用[分层精修](../../../.agents/skills/material2video/references/production-workflow.md#分层精修)和[诊断适用性](../../../.agents/skills/material2video/references/visual-review-rubric.md#诊断测试与适用性)的方式；未新增试制、候选比较或成片复核，不改写既有交付结论。

- 设计重点：以接近、观察、离开及跨尺度关系建立探索感；核心尺度段落投入更多，普通介绍允许克制，抵达后的观察可保持静止。
- 评审重点：按完整移动与观察窗口判断速度、辨认和尺度回报，不按固定运动密度要求持续推拉；一镜到底是本片目标，空间表达要求源于该目标，不推广为所有视频必须立体。
- 返工取舍：压缩过场需同时检查是否损失空间定位、期待和壮阔感；无用途飞行仍需处理，不能用作者声称“沉浸”关闭问题。音乐感染力未试听时仍属于未验证范围。

### 视觉事件设计示范（后续制作指导）

按[设计记录](../../../.agents/skills/material2video/references/stage-plan.md#设计记录)补充后续制作思路。本节未试制、未重渲染，不改写已有成片验收结论；不代表当前视频已经实现下列事件。后续明确启动重制时，逐场表「可见事件」栏链接本节，并先验证完整窗口粗样。

#### 土星环：从局部结构到所属天体

| 部分 | 画面状态 | 观众认识 |
|---|---|---|
| 初始状态 | 近处仅见局部环带，保留导航线索；程序化画面仍属示意 | 识别局部结构，暂不掌握整体尺度 |
| 变化 | 镜头沿环带移动，逐渐公开弧度与空间关系 | 获得形状与方向线索，而非空白赶路 |
| 预期 | 不要求错误判断；已知土星身份也可继续观察 | 期待理解环与球体怎样相连，不靠猜天体名称 |
| 揭示 | 拉远到能同时辨认环带与土星球体的关系 | 将局部结构放回完整天体，形成尺度认识 |
| 结果 | 保留整体及必要名称供观察 | 理解环绕关系，不能误以为与其他独立行星贴靠 |

镜头的信息职责：逐步公开环与球体的关系，避免只做连续缩放。完整窗口覆盖近景线索、整体显现及停留，沿用本片手机验收尺寸；若只感觉镜头移动却未新增尺度或关系认识，应改信息公开顺序。风险加密采样继续检查快移、主体出画与行星挤靠；具体速度和观察时间在后续粗样中确定，不声称现有版本已通过本项。

### 视觉力量设计适用性（后续制作指导）

本节按[设计记录](../../../.agents/skills/material2video/references/stage-plan.md#设计记录)记录后续制作指导，未新增试制、未重渲染，不改写当前成片、旧评审或交付结论。下列方向是待比较候选，不预定采用；明确启动重制后才按同一事件三机制、代表画面与完整粗样验证。

- 旅行的尺度感优先用可辨认天体、远近参照、遮挡与观察窗口建立。对同一天体关系，可比较近景到全貌、侧向显露空间、稳定视点下的尺度参照，不把拉远距离或粒子数量当效果证据。
- 以土星环或结尾尺度回看等实际重点选择适用项，单独比较力量机制；不要求每个站点都三案竞争、突然反转或持续加速。
- 空间规模与必要主体身份同时保留，避免大世界使天体退成不可辨点。静止观察允许成立，完整动态窗口由辨认与情绪需要决定；沿用本片有声契约，不将灰度或去文字测试当所有站点通用门禁。

## 逐场设计表

以下是唯一逐场执行与验收索引。共享规则全片声明，具体窗口与行为以本行及其可编辑来源为准；修订后须实际复查，表格不代表当前已通过。

| 镜头 | 原场景帧窗 [起,止) | 对象、变化与目标 | 实现引用与验收 |
|---|---|---|---|
| aerial-dive（A） | 0–360 | sun：从太阳系上方连续俯冲到太阳，无切换。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=aerial-dive]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| sun-station（B） | 360–714 | sun：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=sun-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| sun-to-mercury（B） | 714–924 | mercury：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=sun-to-mercury]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| mercury-station（B） | 924–1329 | mercury：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=mercury-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| mercury-to-venus（B） | 1329–1539 | venus：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=mercury-to-venus]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| venus-station（B） | 1539–1929 | venus：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=venus-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| venus-to-earth（B） | 1929–2139 | earth：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=venus-to-earth]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| earth-hero（A） | 2139–2676 | earth：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=earth-hero]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| earth-to-moon（B） | 2676–2886 | moon：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=earth-to-moon]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| moon-station（B） | 2886–3280 | moon：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=moon-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| moon-to-mars（B） | 3280–3490 | mars：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=moon-to-mars]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| mars-station（B） | 3490–3908 | mars：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=mars-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| mars-to-ceres（B） | 3908–4118 | ceres：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=mars-to-ceres]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| ceres-station（B） | 4118–4448 | ceres：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=ceres-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| ceres-to-jupiter（B） | 4448–4658 | jupiter：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=ceres-to-jupiter]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| jupiter-station（B） | 4658–5136 | jupiter：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=jupiter-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| jupiter-to-saturn（B） | 5136–5346 | saturn：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=jupiter-to-saturn]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| saturn-hero（A） | 5346–5925 | saturn：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=saturn-hero]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| saturn-to-uranus（B） | 5925–6135 | uranus：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=saturn-to-uranus]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| uranus-station（B） | 6135–6534 | uranus：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=uranus-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| uranus-to-neptune（B） | 6534–6744 | neptune：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=uranus-to-neptune]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| neptune-station（B） | 6744–7165 | neptune：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=neptune-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| neptune-to-pluto（B） | 7165–7375 | pluto：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=neptune-to-pluto]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| pluto-station（B） | 7375–7787 | pluto：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=pluto-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| pluto-to-kuiper（B） | 7787–7997 | kuiper：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=pluto-to-kuiper]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| kuiper-station（B） | 7997–8318 | kuiper：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=kuiper-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| kuiper-to-heliopause（B） | 8318–8618 | heliopause：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=kuiper-to-heliopause]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| heliopause-station（B） | 8618–9082 | heliopause：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=heliopause-station]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| heliopause-to-oort（B） | 9082–9322 | oort：空间过场：抬升到黄道面上方，目标从远处持续接近。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=heliopause-to-oort]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| oort-hero（A） | 9322–9894 | oort：站点：2秒接近、旁白绕行、2秒缓离；前置空间过场独立预算。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=oort-hero]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |
| oort-tail（A） | 9894–10473 | oort：收尾：继续向外，太阳成为亮点。 | [storyboard.json](storyboard.json) / scene=solar-journey / content.props.shots[id=oort-tail]；[journey.tsx](scenes/journey.tsx)；按[体验条件](#核心体验与时间预算)核对主体认回、方向连续与观察时间 |

历史默认检查点 solar-journey-cp 仅覆盖场景帧 [5221,5251)，不代表上述31镜头完整验收。全片与内部镜头须由当前媒体独立终审覆盖；本轮未补造这类观察。相机采用 linear 的全片匀速跟踪规则，具体路径与时点以各 shots.camera 为准，画面内对象使用自身代码曲线。
