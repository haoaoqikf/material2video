# road-trip-video

## Purpose

以真实道路与多日行程制作竖屏地图游记：单一 `trip.json` 编排材料、链式取数、每日底图、每日镜头与卡片、中文旁白、字幕、音效与程序化音床，并提供离线、可复现、带音频验收的渲染链路。首例为 318 国道成都到拉萨七天。

## Requirements

### Requirement: 多日地图游记类型与材料

系统 MUST 登记 `road-trip` 类型，通过统一 init、validate、prepare、preview、render 入口处理作品，首版 MUST 使用 1080×1920 竖屏、30 fps、约 180 秒，其他类型行为保持不变。`road-trip` MUST 属于 `route-journey` 类别，作品标准位置 MUST 为 `videos/route-journey/road-trip/<slug>/`。作品 MUST 只有一份 `trip.json` 编排材料；每日路线 MUST 放在 `routes/day-XX.json`，由 `trip.json` 的 `days[].route` 引用，MUST NOT 进入作品材料清单。材料 MUST 包含起终点、天数、每日目的地与 via、旁白、卡片、音效、事实来源与来源使用依据；MUST NOT 接受手填的总里程、每日时长或起终点坐标，这些 MUST 从路线材料派生。带数值的事实 MUST 同时登记来源标识，没有来源的事实 MUST NOT 进入画面或旁白。旧版本材料 MUST 被明确拒绝，不提供兼容分支。

#### Scenario: 初始化并处理游记作品
- **WHEN** 用户初始化 `road-trip` 作品
- **THEN** 系统写出 `trip.json` 模板，作品标准位置为 `videos/route-journey/road-trip/<slug>`，无需伪装成 general 或 driving-route

#### Scenario: 显式平铺路径被拒绝
- **WHEN** 用户指定 `videos/road-trip/<slug>` 初始化或定位 `road-trip` 作品
- **THEN** 系统拒绝该非规范位置并给出 `videos/route-journey/road-trip/<slug>`；已有作品可用 `m2v relocate` 迁移

#### Scenario: 手填派生字段
- **WHEN** `trip.json` 声明总里程、每日时长或起终点坐标
- **THEN** 校验失败并指出该字段必须由每日路线派生

#### Scenario: 无来源事实
- **WHEN** 卡片事实带 `value` 但缺少 `sourceId`
- **THEN** 校验失败并指出具体事实

#### Scenario: 不支持的材料版本
- **WHEN** `trip.json` 或任一日 `route.json` 的 `schemaVersion` 不受支持
- **THEN** 系统在准备前明确拒绝并指出版本

### Requirement: 链式多段取数与来源隔离

系统 MUST 提供 `m2v road-trip fetch`，第 1 天从行程起点定位，第 N 天起点 MUST 直接使用第 N-1 天路线终点，MUST NOT 二次定位；日间衔接 MUST 在 1 米容差内。取数 MUST 按 via 顺序规划并合并步骤，步骤之间 MUST 满足现有 25 米连续性规则，via 点 MUST 落在步骤链上。`routePreference: "g318"` MUST 通过避开高速策略与 via 节点尽量保持国道走廊，取数后 MUST 校验关键节点；不符合时 MUST 失败并指出缺口，MUST NOT 手改几何或虚构坐标。凭据 MUST 只从 `M2V_AMAP_KEY` 读取，MUST NOT 写入材料、日志、异常或临时文件；来源使用依据三项确认未全部为真或 `mapTiles` 不为真时 MUST 在发起网络请求前失败。全部路线 MUST 先在内存中完整校验再原子写入，任一步失败 MUST 恢复全部旧路线，不发布半份材料。

#### Scenario: 日间无缝衔接
- **WHEN** 第 N 天路线以第 N-1 天终点为起点取数
- **THEN** 两份材料的衔接坐标在 1 米内，校验通过；重新定位或吸附过远时明确失败

#### Scenario: 偏离 G318
- **WHEN** 取数结果未包含声明的关键国道节点
- **THEN** fetch 失败并报告缺失节点，要求调整 via，不保存新路线

#### Scenario: 取数失败
- **WHEN** 任一日的定位、算路或行政区请求失败
- **THEN** 全部旧路线保持不变，不留下半份材料或临时文件

#### Scenario: 凭据缺失
- **WHEN** 未设置 `M2V_AMAP_KEY`
- **THEN** 在任何网络请求前失败并指出环境变量名

### Requirement: 每日底图与离线渲染

系统 MUST 提供 `m2v road-trip basemap`，生成全局概览、每日概览与每日跟随瓦片走廊，并支持按天切换普通与卫星底图。走廊 MUST 按当天整条路线与静态 layout 生成，MUST NOT 依赖旁白或视频时长；相同路线与布局版本 MUST 生成相同清单摘要。系统 MUST 为每日走廊、全片瓦片数与字节数设置上限，超限 MUST 失败并报告实际值，MUST NOT 静默降低缩放。索引与清单 MUST 原子更新，失败 MUST 保留旧底图。准备记录 MUST 只保存底图路径与摘要，MUST NOT 内嵌瓦片或概览的 data URI；准备 MUST 用编译后的逐帧相机复核可见瓦片是否已全部存在，缺块 MUST 失败并报告坐标。渲染 MUST 通过本地静态服务注入资源基址，只挂载当前视口可见瓦片，全程 MUST 不发生外部网络请求。

#### Scenario: 改旁白不重取瓦片
- **WHEN** 只修改旁白或时长后重新准备
- **THEN** 底图走廊与清单保持不变，准备直接复用，不触发重新取图

#### Scenario: 缺块
- **WHEN** 编译后的相机在某一帧需要未保存的瓦片
- **THEN** 准备失败并报告缺失瓦片的坐标，要求重跑 basemap

#### Scenario: 体积控制
- **WHEN** 七天行程准备完成
- **THEN** `prepared.json` 不含 `data:image`，体积低于约定预算

#### Scenario: 离线渲染
- **WHEN** 断网且未配置地图凭据时执行 validate、prepare、preview、render
- **THEN** 全部使用本地材料与底图完成，不发生外部请求

### Requirement: 每日时间轴、相机与卡片

系统 MUST 为每天生成独立镜头段：章节卡、开场由 8× 推近到 12×、12× 匀速跟随、当天概览收束；最后一天 MUST 收束到全局概览。每日帧数 MUST 以口播长度与卡片停留为最小帧，MUST NOT 截断旁白；软目标余量 MUST 按当天路线里程加权并确定性分配。相机与卡片状态 MUST 只依赖当前帧、材料与静态布局，MUST NOT 依赖上一帧、随机数或挂钟。跟随段相机平移 MUST 对齐整像素，底图、路线与标签 MUST 共享同一重采样相位。允许在声明的地貌窗口平滑改变跟随倍率，倍率 MUST 来自静态布局而非逐帧计算。章节卡与数据卡 MUST NOT 遮挡字幕安全区，MUST NOT 越出画布。日间切换 MUST 只用当天数据完成，MUST NOT 同时挂载两天的瓦片。

#### Scenario: 口播优先
- **WHEN** 旁白总时长超过软目标
- **THEN** 成片时长随口播增长，不截断语音；超过 600 秒时准备失败

#### Scenario: 帧分配确定性
- **WHEN** 相同材料与布局重复准备
- **THEN** 每日帧数、章节卡窗口与音效锚点完全一致

#### Scenario: 卡片与字幕
- **WHEN** 章节卡或数据卡与字幕出现在同一帧
- **THEN** 卡片包围盒不与字幕安全区相交，字幕可读

#### Scenario: 倍率窗口
- **WHEN** 镜头进入声明的地貌窗口
- **THEN** 跟随倍率平滑变化，离开后恢复，画面不跳变

### Requirement: 旁白、字幕、音效与程序化音床

系统 MUST 要求至少一段非空旁白，音色 MUST 显式指定并按现有音色选择门禁绑定完整旁白摘要。旁白 MUST 通过共享 TTS 合成，首次需要联网，成功后缓存并供离线复用；合成失败 MUST NOT 写入准备记录。字幕 MUST 由共享断句规则生成，单条不超过 28 字，并按全片帧号烧录在安全区内。音效 MUST 支持内置提示音、确定性合成配方、登记音效 ID 与本地文件四选一，按天、段、到达或地标锚点定位；定位越界 MUST 失败。音床 MUST 来自确定性程序化合成或本地留证文件；程序化音床 MUST 记录生成器版本、种子与许可，并保证循环接缝连续。旁白讲话时音床 MUST 自动压低。母版 MUST 归一化到 −14 LUFS 与 ≤−1 dBTP，成片音频 MUST 为 AAC-LC、44.1 kHz、立体声 128k，音轨 MUST 严格裁至全片时长。系统 MUST NOT 使用 general 的 scenes 音效绑定或 `declared_audio` 判断本类型是否有音轨。

#### Scenario: 旁白缺失
- **WHEN** `trip.json` 没有任何非空旁白
- **THEN** 校验失败，提示 road-trip 为有声类型

#### Scenario: 音色未指定
- **WHEN** 旁白已写但未指定音色且命令行未覆盖
- **THEN** 准备在合成前失败，提示选择音色或使用 `--voice`

#### Scenario: 旁白修改
- **WHEN** 修改任一段旁白文本
- **THEN** 旁白摘要变化，旧音色选择与旧准备失效，要求重新判断与准备

#### Scenario: 音床循环
- **WHEN** 30 秒程序化音床铺满三分钟成片
- **THEN** 循环点无可闻爆音，母版响度与真峰值达标

### Requirement: 有声渲染验收与候选复用

正式导出 MUST 生成画面后混入母版音轨，MUST NOT 使用强制无音轨的静音管线。导出 MUST 验证总帧数、尺寸、帧率、时长、音频流编码与声道，并量测集成响度与真峰值；任一不达标 MUST 拒绝交付。预演 MUST 允许局部帧窗口，并从母版切出对应音频区间；预演 MUST NOT 覆盖正式成片。准备记录 MUST 绑定材料、路线、底图索引与清单、音床、母版、实现与渲染器摘要；任一项变化 MUST 要求重新准备。正式导出 MUST 复用有效候选，失败 MUST NOT 覆盖已有成片。溯源 MUST 记录音色、语速、母版摘要、底图摘要与候选绑定。

#### Scenario: 正式成片
- **WHEN** 渲染七天全片
- **THEN** 成片包含音频流，帧数、尺寸、帧率、时长、响度与真峰值全部通过验收

#### Scenario: 局部预演
- **WHEN** 预演 Day 4 的 30 秒窗口
- **THEN** 画面与音频都只覆盖该窗口，写入 `outputs/previews/`，不影响正式成片

#### Scenario: 音频缺失
- **WHEN** 准备记录没有母版音轨却执行正式导出
- **THEN** 导出失败，不生成无声成片冒充有声交付

#### Scenario: 材料变化
- **WHEN** 准备后修改路线、底图、旁白、音色或实现
- **THEN** 旧准备失效，导出要求重新准备

### Requirement: 318 首例与制作完成

首例 MUST 使用成都到拉萨的七天川藏南线行程，总长约三分钟、5400 帧左右，包含片头、七天章节与片尾；旁白 MUST 为中文纪实口吻，总长约 380–450 字，每天只讲一个地貌特征。画面 MUST 包含真实路线、已走与未走轨迹、行政区标签、每日章节卡、数据卡与字幕；数据卡中的海拔等事实 MUST 有登记来源。Day 4 MUST 包含怒江七十二拐窗口与倍率变化；Day 3 MUST 包含金沙江进藏节点。制作完成 MUST 先生成 Day 4 单日样片并通过技术验收与独立视觉评审，再进入全片；全片 MUST 具备当前候选的技术证据、独立评审与发布说明。作品材料、底图、音床与成片 MUST 不进入版本控制；共享代码、测试与文档 MUST 进入版本控制。

#### Scenario: Day 4 样片未通过
- **WHEN** 样片的贴路、倍率、字幕安全区或音频验收存在未关闭的必改项
- **THEN** 不得进入七天全片渲染

#### Scenario: 全片验收
- **WHEN** 七天全片候选进入制作完成判定
- **THEN** 复核轨迹与路线材料一致、日间衔接连续、旁白与字幕同步、响度达标、独立必改项全部关闭

#### Scenario: 内容不入库
- **WHEN** 提交本变更
- **THEN** 只包含类型代码、前端、测试与文档，不包含作品材料、底图、音床或成片