## Context

动机与范围见 [proposal.md](proposal.md)。现有 `driving-route` 把「一条路线、一个镜头时间轴、一条底图走廊、无音轨」写进了材料与实现：`materials.py` 只接受单起终点，`layout.py` 只有一个距离轴，`render.py` 走 `SilentRenderSpec` 并强制无音轨。`general` 有成熟的 TTS、字幕与混音引擎，但音效绑定 `scenes/narrationSegments`，地图能力不可用。

本变更要同时解决三件事：多日行程的表达、有声类型的生命周期、底图数据的体积。三件事都必须在材料层解决，否则会在实现阶段反复分叉。

## Goals / Non-Goals

**Goals:**

- 一个 `road-trip` 类型可制作任意天数、任意真实路线的竖屏地图游记。
- 旁白、字幕、音效与程序化音床进入正式契约，准备记录可追溯、渲染离线可复现。
- 每日底图独立生成，改旁白或时长不重新取数、不重新取瓦片。
- 准备记录体积可控（不内嵌全部瓦片），大行程不因 props 过大失败。
- 共享校验与绘制逻辑抽取后，`driving-route` 行为与测试不回归。
- 318 首例通过 Day 4 样片与全片两级验收。

**Non-Goals:**

- 不把 `road-trip` 做成 `general` 的代码场景；不复用 general 的分镜结构。
- 不导入照片、实拍或三维车；不做横屏版本。
- 不引入新的地图提供方或在线运行时底图。
- 不提供旧材料兼容分支。
- 本轮不实现；本文件只记录方案。

## Decisions

### 1. `trip.json` 是唯一编排材料，route 由它内部引用

类型目录只登记 `trip.json` 一份材料，因为 `catalog.json` 的材料 `file` 只允许单层文件名。每日路线放在 `routes/day-XX.json`，由 `trip.json` 的 `days[].route` 引用，不进入 `project.materials`。

准备指纹不能只依赖 `project.materials`：`prepare` 必须显式把每份 route、底图索引、每日底图清单、音床与母版登记为 `file:` 输入，`load_current_prepared` 才能在任何一份变化时判过期。

### 2. route v1 与视频时长解耦

每日 `route.json` 只记录几何、定位、行政区与采集记录；`requestDigest` 只覆盖 `dayId`、`destination`、`via`、`strategy`、`coordinateSystem`，**不覆盖旁白、卡片与时长**。

这样改旁白只触发 TTS 与时间轴重编译，不重新取数；底图走廊也按整条路线生成，与时长无关，改旁白不需要重取瓦片。取数只在起终点、via 或路线偏好变化时失效。

### 3. 链式取数，第 N 天起点取前一天终点

第 1 天从 `trip.start` 定位；第 N 天起点直接使用第 N-1 天 `route.endPoint`，不二次定位。离线校验日间衔接 ≤1 米，避免两次定位吸附不同位置造成断点。

318 需要「走 G318」而不是「最快路线」：trip 增加 `routePreference: "g318"`，fetch 使用避开高速的策略，并用 via 点把路线钉在泸定、新都桥、雅江、理塘、巴塘、芒康、左贡、邦达、八宿、然乌、波密、通麦、鲁朗、林芝、工布江达、墨竹工卡等节点。取数后检查关键节点落在步骤链上；不符合时调整 via，不手改几何，也不虚构路线。

第 1 天仍应用现有「起点前 5 公里主路」裁剪；第 2–7 天不裁剪，避免与前一天终点断开。

### 4. 底图：全局概览 + 每日概览 + 每日走廊

- 全局概览：整趟行程投影 bbox 的单张拼接，用于片头、日间转场与片尾。
- 每日概览：当天 bbox 与收束视口。
- 每日跟随走廊：当天 12× 跟随视口的并集，加开场推近与 landmark 视口、安全 margin。

走廊生成不读取旁白或时长，因此同一份路线与 layout 版本生成相同清单。prepare 用编译后的逐帧相机复核「可见瓦片 ⊆ 已存瓦片」，缺块直接失败并报告坐标，不静默降 zoom。

上限：每日沿用 `MAX_CORRIDOR_TILES=2200`；新增全片预算（建议 6000 块、500 MB），超限失败并报告实际值。卫星与普通底图按天切换，瓦片尺寸与来源授权沿用现有约定。

### 5. 准备记录只存路径，渲染注入本地资源基址

`driving-route` 首例的 `prepared.json` 达 50–75 MB，原因是全部瓦片内嵌为 data URI。七天行程照搬会到数百 MB，Remotion props 传递与内存都不可接受。

改为：

- props 只保存 `overview.path`、`followTiles[].path` 与摘要；
- 渲染时起 `LocalServer(project_root, cors=True)`，把 `assetBase = server.base_url + "/"` 注入临时 props，与 `explainer_render` 的 `mediaBase` 同机制；
- 前端只挂载当前视口瓦片（`selectVisibleTiles`），用 `delayRender` 等待当前可见瓦片解码，不预载全片；
- 准备输入登记 `file:assets/basemap/road-trip/index.json` 与每日 `manifest.json`，不登记数千条 tile 摘要；
- prepare 后检查 `prepared.json` 体积，超过 50 MB 警告、80 MB 失败。

离线守卫允许 localhost；静态根不扩大，仍只暴露作品目录。

### 6. 有声类型手写生命周期，复用共享引擎

`road-trip` 不走 `SilentTypeSpec`：其 `prepare` 忽略音色、渲染强制 `assert_no_audio`。仿照 `general/adapter.py` 组合 `VideoType`：

- 直接复用：`tts.settings/resolve/preparation/scene_audio`、`subtitles.cues_from_words`、`audio.concatenate/mix/master/mux`、`sound_synthesis`、`render_pipeline.metadata_confirm/write_provenance/write_report`、`core.delivery.export_once`、`core.preview.window`。
- 自己实现：以 day/segment 为单位的旁白与音效锚点解析、每日帧分配、`has_audio(prepared)`、字幕 cue 的全局帧换算。
- 不使用：`explainer_prepare.prepare`、`soundtrack.validate/mix`、`audio_policy.declared_audio`，这三处强绑 general 的 scenes 结构。

### 7. 时间轴：口播优先，里程加权分配余量

每日最小帧 = 章节卡 + 前导 + 全部口播帧 + 段间停留 + 数据卡 + 收束 + 尾留白。口播永不截断。

若总最小帧小于 `targetSeconds`，余量按当天路线里程加权，用最大余数法分到整数帧，保证相同输入得到相同结果。若总最小帧超过目标，直接采用最小帧；超过 600 秒硬上限则失败。`targetSeconds` 是软目标，不是必须精确命中的数值。

### 8. 相机：每日独立时间轴，终点收束到概览

每天内部：章节卡覆盖 → 8× 推近到 12× → 12× 跟随 → 当天概览收束。最后一天收束到全局概览。

- 跟随段相机平移对齐整像素，底图与标签共享重采样相位；
- Day 4 在 72 拐窗口把倍率平滑提到 14×，倍率序列是静态 layout 常量，不引入随机；
- 所有状态只依赖 `frame` 与 props，不依赖上一帧；
- 日切换只在当天数组内完成，不跨天同时挂两套瓦片。

### 9. 声音：旁白、字幕、音效、程序化音床

- 旁白：中文 edge-tts，首次 prepare 联网合成并缓存；失败不写准备记录。音色必须显式，按现有 `assistant-voice-selection` 门禁记录 rationale 与旁白摘要。
- 字幕：`cues_from_words` ≤28 字断句，按段起点换算全局帧，clamp 到段窗口；烧录结构与 `ArticleExplainer` 一致。
- 音效：四选一 `builtin` / `synthesis` / `assetId` / `sourceRef`，按 `anchor` 定位到 day-start、day-arrival、segment-start/end、landmark、trip-start/end。
- 音床：`road_trip/ambient.py` 生成 30 秒无缝循环，频率取循环长度整数分之一，seed 固定，记录生成器版本与 CC0；`audio.mix` 以 `loop` 铺满并按旁白 cue 自动 ducking。
- 母版：`audio.master(-14 LUFS, -1 dBTP)`；`mux` 输出 AAC-LC 44.1 kHz 立体声 128k；成片验收量测响度与真峰值。

### 10. 前端：抽取地图层，新建 roadtrip 纯函数层

- 从 `DrivingRoute.tsx` 抽 `driving/MapLayer.tsx`：底图、路线、端点、行政区标签；先抽取不改行为，用现有 `DrivingRoute.test.tsx` 做回归。
- 新建 `web/src/compositions/roadtrip/`：`model`（帧→day/localFrame）、`timeline`、`camera`、`layout.json`、`labels`、章节卡/数据卡/Day ribbon/字幕层。
- 契约页优先改为按材料字段分派，复用同一构建入口；若隔离风险更高，再新增独立 `roadtrip-contract.html`。
- 所有绘制只读 props 与静态 layout，`assetBase + path` 拼瓦片地址，不出现 data URI。

### 11. 共享校验抽取保持依赖方向

把 sourceUsage、geocoded place、steps 连续性、cost/cities/行政区的校验抽到 `src/m2v/types/route_common.py`，`driving_route/materials.py` 改为委托，公开函数与错误文案保持不变。共享底座不导入类型私有逻辑；只有两个真实类型出现相同需求时才抽取。

### 12. 与 vehicle-showcase 并行变更的归档顺序

`vehicle-showcase` 的影棚与车轮变更仍在进行中，本变更与其并行开发。两者都会修改 `catalog.json` 与文档生成区。

- 实施时共享文件只做追加，保留其现有未提交改动；
- 归档本变更时，`modular-video-production` 的类型清单按**当时实际已归档的类型**合并，不写死旧清单；
- 提交时用 hunk 级暂存只提交本变更相关内容；无法分离时停下说明，不夹带未完成的 vehicle 改动。

## Risks / Trade-offs

- **高德路线偏离 G318**：`highway-first` 会走雅康高速。用 `routePreference: "g318"` + 密集 via 约束；取数后校验关键节点。仍不满足时调整 via，不手改几何。风险是某些节点无法完全避免高速绕行，画面以实际返回为准，不宣称「每一米都是 G318」。
- **瓦片量与体积**：七天约 6000 块瓦片、数百 MB。每日上限 + 全片预算；超限失败。代价是超长行程可能需要减少 landmark 焦点或增大 margin。
- **渲染内存与时长**：5400 帧、只挂可见瓦片。先以 Day 4 样片实测；首版串行渲染，不启用多进程。
- **TTS 联网**：首次 prepare 必须联网。失败不写准备记录，缓存已成功段；后续离线复用。
- **音床接缝**：30 秒循环在 3 分钟内重复 6 次。频率取整数周期并重复渲染比对，避免循环点爆音。
- **共享文件混合提交**：与 vehicle-showcase 并行。提交策略见决策 12；无法分离时以停下说明为正确行为。
- **授权链**：高德 `sourceUsage` 三项确认与 `mapTiles=true` 是取数前置；音乐改为程序化音床后不再依赖外部曲目授权，但生成器与参数仍须留证。

## Migration Plan

- 新类型，不涉及旧材料迁移；`driving-route` 只做内部委托重构，材料版本、错误文案与画面行为不变。
- `catalog.json` 只追加 `road-trip` 条目；`sync_docs.py` 重新生成文档区。
- 首例 Day 4 样片与七天全片分两级验收；样片不通过不进入全片。
