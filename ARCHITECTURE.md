# 架构与模块职责

Material2Video 通过 Python 命令行准备和校验作品，使用 Remotion 完成渲染。代码按**通用代码、类型专属代码、具体作品代码**三层组织，类型之间只共享明确的公共能力。

## 代码分层

| 层 | 位置 | 说明 |
|---|---|---|
| 通用代码 | `src/m2v/core/`、`engine/`、`production/`、`reference/`、`type_system/`；`web/src/code-scene/`、`runtime/`、`contract/`、`production/`、`styles/`、`assets/` 与画幅/字体/帧率入口 | 不含任何具体视频类型的业务流程；类型目录、注册表、迁移与无声类型装配属于通用类型基础设施 |
| 类型专属代码 | `src/m2v/types/<type>/`；`web/src/types/<type>/` | 一个类型自己的材料、取数、准备、渲染、composition 与类型内共享模块 |
| 具体作品代码 | `videos/<category>/<type>/<slug>/`、`styles/<id>/examples/<slug>/` 下的 `scenes/`、`assets/` 与作品材料 | 作品内容，按路径契约存放；仓库只保留制作方法与共享资产 |

`src/m2v/types/route_common.py` 与 `src/m2v/types/route_schema.py` 是仅有的类型间共享模块，只被 `driving-route` 与 `road-trip` 使用：前者放两个路线类型都成立的真实路线校验与来源使用判定，后者放地点、来源使用等共享结构模型；两者都不含任一类型的私有材料形状。

## 模块边界

- `src/m2v/core/`：作品与工作区契约、路径、资产、指纹、安全策略和公共错误。它不包含具体视频类型的业务流程。`core/schema.py` 是材料结构校验的 Pydantic 基类与中文错误转换入口；`core/geodesy.py` 是路线球面距离的共享口径（geographiclib 零扁率球体）。
- `src/m2v/type_system/`：类型目录（`catalog.json`）、注册表、路径迁移与无声类型装配。类型目录同时登记可选的「类别 → 类型」归属（当前 `route-journey` 包含 `driving-route` 与 `road-trip`），类别只用于组织、规范作品位置与文档分组，不提供行为。统一入口、初始化、位置校验与文档生成消费这一层；它不导入类型实现。
- `src/m2v/types/`：各类型专属适配器。新类型从类型目录发现，再由适配器实现校验、准备、预演、渲染及可选评审。`driving_route/` 中 `materials.py` 负责请求/路线契约、绑定摘要与几何校验，`amap.py` 是路径 API 客户端，`fetch.py` 负责授权前置、原子保存与失败保护，`basemap.py` 负责概览拼接与跟随瓦片走廊、内容寻址目录、逐块摘要与本地记录；Pillow 只用于瓦片处理。离线生命周期不导入取数或取图路径，也不需要 Key。`route_common.py` 只含两个类型都成立的真实路线判定（定位精度、步骤连续性、成本、城市与行政区），不导入任何类型私有逻辑；`road_trip/` 在它之上增加多日编排、链式取数、每日底图、时间轴、程序化音床与有声渲染，`fetch.py`/`basemap.py` 同样只被在线命令导入。金融历史材料迁移位于 `financial/migration.py`。
- `src/m2v/types/general/code_scenes/config.py`：代码场景入口校验、录制配置与确定性打包；`capture.py`：逐帧采集、片段缓存与编码验收；`worker.py`：pure-time 分块采集子进程入口。录制配置只在作品 opt-in 时注入全局时间轴与纯模式，未声明时保持既有形状。`src/m2v/engine/remotion/segments.py` 负责 `--jobs` 的分帧区间渲染、逐段验收与无损拼接，不改变单进程路径。
- `src/m2v/types/general/sound_synthesis.py`、`sound_library.py`、`soundtrack.py`：分别负责常见音效目录及确定性拟音、双来源音效登记与离线复核、分镜声音编排；共享 `engine/audio.py` 只处理音频信号与立体声混音，不决定音效选型或许可。
- `src/m2v/core/styles.py`：解释 `styles/<id>/style.json`，负责风格发现、作品兼容校验和内容指纹；不依赖类型实现。general 打包器只消费已校验入口，风格不修改业务流程。
- `src/m2v/engine/`：Remotion 构建、渲染会话、音视频、字幕、缓存、质量检查和输出验收；不应依赖类型私有业务规则。`engine/perf.py` 用 psutil 采样进程树内存；`engine/qa.py` 的冻结帧硬判定交给 ffmpeg `freezedetect`，采样帧只负责测量项；`core/fonts.py` 用 fontTools 读取 cmap 并切字体子集。
- `src/m2v/production/`：制作合同、证据依赖、追加式状态、独立评审包及基线保留；制作编排可调用类型采集器，core 不反向依赖该层，渲染不读取制作门作为导出条件。
- `src/m2v/reference/`：外部参考素材获取、页面详情解析、媒体摘要核验与用户授权的音轨提取。`ytdlp_adapter.py` 是 yt-dlp 提取入口；yt-dlp 无法处理平台签名时，`douyin.py` 才退回浏览器解析并留下明确日志。
- `src/m2v/cli.py` 与 `src/m2v/commands.py`：统一命令入口及通用命令编排；类型专属命令由类型模块提供。
- `web/src/`：Remotion 合成、通用代码场景运行时、共享动效组件、共享动效原语、字体与画幅契约。类型专属 composition 在 `web/src/types/<type>/`；作品场景代码保存在作品内容目录，不放进共享运行时或类型目录。`web/src/code-scene/motion-components/` 提供只依赖 `progress`/`easing` 的共享组件：L1/L2 入场与数据动效之外，还有 `text.tsx`（字体就绪后测量、CJK 换行）、`morph.tsx`（路径形变与遮罩）、`gauge.tsx`（圆弧进度）、`noise.tsx`（种子噪声漂移）、`charts.tsx`（纯时间安全折线/面积/坐标轴）、`timeline.tsx`、`pictogram.tsx` 与 `waveform.tsx`；`paths.ts` 封装 `@remotion/paths`，`styles.ts` 封装 `@remotion/animation-utils`，文本使用 `@remotion/layout-utils`，噪声使用 `@remotion/noise`，图表几何使用 `d3-scale`/`d3-shape`，`MarkerHighlight` 使用 `roughjs` 生成草图几何。作品与风格包只能通过 `m2v/code-scene` 使用，不直接 import 这些库。`web/src/types/driving_route/DrivingRoute.tsx` 只绘制当前帧，投影、累计距离、贴路位置、朝向、镜头与瓦片可见性在 `types/driving_route/route.ts` 中实现为纯函数；同一帧不依赖执行顺序或跨帧状态。配置普通道路底图时，概览常驻，z12 跟随瓦片按当前相机视口绘制并在结尾淡出；顶部两行标题、车辆旁里程与右下署名在屏幕空间叠加；市/县名使用路线材料中的行政区中心点绘制，市辖区不单独标注。`web/src/types/driving_route/layout.json` 是标题、内容区、相机与标签尺寸的跨语言单一来源。`web/src/code-scene/painter/` 是可选的二维 Canvas 绘制层：供需要辉光质感、高密度粒子与线条生长的场景使用，与 R3F 的 `Canvas` 区分，并输出同源的 DOM 量测代理与状态探针，使 Canvas 内容可被检查点量测。生产链路的确定性源码闸门不覆盖该目录，由测试对整目录执行同一检查。

## 契约与文档

- `web/src/code-scene/chart-geometry.ts` 统一 D3 点列曲线，共享图表、金融图表和风格包复用；业务轴、节奏和风格参数仍由调用方维护。SDK 的 `diagram`、`math`、`icons` 子入口分别提供 ELK 一次性布局与静态绘制、KaTeX 本地排版与就绪、Lucide 静态命名图标，按引用打包；不经通用入口加载整套外部表达库。公式 WOFF2 由 `fonts/registry.json` 登记，依赖安装后通过既有恢复机制进入忽略目录，代码场景打包时核验。
- `web/src/transitions.json` 是 general 场景转场名称、呈现与方向的跨语言真源；Python 校验与准备、Web 官方 TransitionSeries 合成及 G5 中性投影共同消费。转场重叠与字幕仍由准备阶段的全局时间窗决定。LocalServer 在默认同源与显式 CORS 模式下均支持已有单段 Range 处理，跨域头只在后者发出。

- `src/m2v/type_system/catalog.json` 是类型清单、类别归属与初始化模板信息的来源；README 和 Skill 中标记的类型清单由同步脚本按类别生成。类别只组织类型，不作可执行类型；类型目录或制作门/审核策略修改后运行 `python .agents/skills/material2video/scripts/sync_docs.py` 重新生成，`--check` 只验证、不写入。作品规范位置由类别派生：分类类型为 `videos/<category>/<type>/<slug>/`，未分类类型为 `videos/<type>/<slug>/`。
- 新增视频类型只在两处落地：先在 `src/m2v/type_system/catalog.json` 登记类型（含可选类别归属）、材料入口、初始化模板与文案，再实现该类型的适配器。共享入口不按类型名硬编码分发，类型清单由目录生成。
- `web/src/frames.json` 与 `web/src/video-config.json` 分别是画幅/字幕几何和帧率的跨语言来源；Python 经 `core/frames.py`、`core/video_config.py` 读取，制作合同与类型校验复用同一入口。
- 路线几何的纯数学层使用成熟库：Python 侧 `mercantile` 负责 Web Mercator 与瓦片索引、`geographiclib` 负责球面距离；Web 侧 `@turf/distance` 负责距离、`d3-geo` 负责投影。相机、贴路、平滑、标签与瓦片可见性仍是项目特化逻辑。
- `core/source_imports.py` 是字面量引用提取和本地路径解析的公共接口；构建输入与制作证据分别决定遍历范围、摘要和保守绑定策略。
- `core/media_policy.py` 是画面素材来源元数据与采用状态的单一判据，由 general 导入/准备和共享台账/审计消费；只校验数据和已记录的用途结论，不联网或自动解释法律条款。未知许可与未核实提示，明确禁止与条件未满足阻断。声音、字体与路线使用依据仍由各自契约处理。
- `production/workflow.py` 定义门、阶段、范围、检查处理器及顺序依赖，`production/policy.py` 定义风险与审核策略；状态计算、CLI、自动检查和文档生成消费这些定义。`production/sampling.py` 维护风险步长和强制边界，`production/evidence_images.py` 使用已有 Pillow 批量派生尺寸，`production/timing.py` 生成风险时序试验并校验复用过程。评审包字段由 `production/reviews.py` 的构建器统一投影到打包、粗片播放器与文档示例。`production/media_evidence.py` 只核验动态核心过程片段能否解码、视频流时长是否覆盖检查窗，不判断内容，供报告导入与状态查询共用。
- `.agents/skills/material2video/scripts/sync_docs.py` 生成类型清单及检查点文档中的门表、风险表和审核人数表；用 `--check` 验证漂移，生成区不手工维护。同目录的 `guidance_docs.py` 校验阅读路由（`references/guidance-routes.json`）的目标、锚点、触发条件与字符预算，由 `sync_docs.py --check` 一并执行。
- 制作操作顺序由三份阶段指南维护，[production-workflow.md](.agents/skills/material2video/references/production-workflow.md) 只维护跨阶段返工、回退与基线规则；日常制作先读当前阶段及实际触发的专项。合同与证据结构在 [checkpoint-gates.md](.agents/skills/material2video/references/checkpoint-gates.md)，评审隔离与执行在 [subagent-review.md](.agents/skills/material2video/references/subagent-review.md)，全片复核、G5/G6、剪辑与传播在 [visual-review-rubric.md](.agents/skills/material2video/references/visual-review-rubric.md)，载体选择在 [visual-material-selection.md](.agents/skills/material2video/references/visual-material-selection.md)。自驾路线的取数授权、材料绑定与画面契约在 [driving-route-video.md](.agents/skills/material2video/references/driving-route-video.md)。其他入口通过链接引用。
- 项目级知识 skill：`.agents/skills/frontend-design/` 负责视觉方向、字体、构图、层级与反模板判断，`.agents/skills/motion-design/` 负责运动设计与帧驱动动效。两者固定上游提交，上游正文原样保留，视频语境差异集中在各自 `ADAPTATION.md`；主 Skill 只负责在方案、制作、验收阶段调度，它们不改变代码分层、渲染契约、审核轮次或门禁。
- `web/src/code-scene/motion.ts` 是相机与原语共用的命名缓动来源；原语要求显式缓动，不得各自复制曲线。
- `openspec/specs/` 描述已实现行为，`openspec/changes/` 保存尚在进行的变更。命令和用户流程说明由 README 与 Skill 分别承担入口和操作手册职责。
- `videos/`、`refs/` 及 `styles/<id>/examples/<slug>/` 下的示例媒体是内容或派生产物，不属于共享代码模块；风格包只提供表现层，示例子树不进入包指纹，共享清单和组件不得引用示例；嵌套示例仍按独立作品执行导入边界。具体入库约束见 [AGENTS.md](AGENTS.md)。

## 测试分层

测试目录与代码分层对应，避免所有用例平铺在 `tests/`：

| 目录 | 覆盖范围 |
|---|---|
| `tests/common/` | 通用代码：作品契约、渲染引擎、制作合同、参考素材、类型目录、文档生成、字体与样式基础设施 |
| `tests/types/<type>/` | 单个类型的材料、取数、准备、时间轴、渲染与命令边界 |
| `tests/works/examples/` | 具体示例作品：示例清单、媒体备案、示例专属生成器与风格示例校验 |
| `tests/helpers/` | 跨层共用的测试夹具与固定清单；测试模块通过 `helpers.*` 导入，不互相导入 |

新增用例放入其覆盖范围对应的目录；只为某个类型服务的夹具放进该类型测试目录或 `tests/helpers/` 的具名模块，不把类型私有逻辑写进 `tests/common/`。

## 依赖方向

类型基础设施（`type_system/`）只依赖 `core/`；类型适配器依赖 `type_system/`、`core/` 与 `engine/`；共享层不反向导入类型实现或作品代码。`types/` 内只有 `route_common.py` 被两个路线类型共享，其他模块不得跨类型导入。

general 的 `scene_events.py` 维护幕内事件校验和音效定位规则；prepare 解析实际时间后，将事件帧表交给场景配置，将同一份音效起点交给混音并输出事件清单。Web SDK 只查询注入的幕内帧，不反向采集事件或改写音轨。

Web 渲染层只读取准备阶段提供的契约与输入，不承担 Python 侧材料校验或类型选择。类型 composition 只依赖 `web/src` 的共享运行时，不依赖其他类型的 composition；`road_trip` 复用 `driving_route` 的地图纯函数是唯一的类型间前端依赖。

新增或拆分模块时，优先保持代码分层与这一依赖方向，并让每项规则只有一个权威来源。
