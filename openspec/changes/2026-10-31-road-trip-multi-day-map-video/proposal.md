## Why

用户要制作一部 318 国道川藏南线七天进藏的**纯地图游记**，并明确要求旁白、音效与字幕。现有类型都无法承载：

- `driving-route` 是单条路线、30/60 秒、无音轨、单时间轴，材料契约里没有「天」「旁白」「音效」的位置；
- `vehicle-showcase` 是影棚里的三维车，与真实路线和游记无关；
- `general` 的有声能力完整，但地图取数、瓦片走廊与贴路相机无法复用，重新实现会把两套地图逻辑分叉。

需要新增一个独立类型，把多日行程、真实路线、每日底图、旁白与声音合成一条可复现的离线制作链路，并以 318 首例验证。

## What Changes

- 新增 `road-trip` 类型：作品只有一份 `trip.json` 编排材料，按天引用 `routes/day-XX.json`；固定 1080×1920 竖屏、30 fps。
- 新增 `m2v road-trip fetch`：按天链式取数，第 N 天起点直接取前一天终点，用 via 点钉住 G318 走廊，全量校验后原子写入，失败回滚。
- 新增 `m2v road-trip basemap`：全局概览、每日概览与每日跟随瓦片走廊；走廊覆盖与旁白时长无关，支持按天切换普通/卫星底图。
- 新增每日时间轴：章节卡、里程加权帧分配、每日开场推近与 12× 跟随、收束到当天概览，末日渐次收束到全程。
- 新增声音链路：中文旁白（edge-tts）、烧录字幕、克制音效与确定性程序化音床；复用共享 TTS、字幕与混音引擎，不套用 general 的 scenes 音效绑定。
- 准备记录只保存底图路径与摘要，不内嵌 data URI；渲染时用本地静态服务注入资源基址，只挂载当前视口瓦片。
- 抽取共享路线校验与地图绘制层，`driving-route` 改为委托，行为与材料契约不变。
- 首例制作 318 国道成都→拉萨七天、约 3 分钟成片；作品内容、底图与成片不入库。

不提供旧版本兼容或迁移工具；不改变 `driving-route`、`vehicle-showcase`、`general` 的现有契约。

## Capabilities

### New Capabilities

- `road-trip-video`：多日行程材料、链式取数、每日底图、每日相机与卡片、旁白/字幕/音效/音床、有声渲染验收与首例。

### Modified Capabilities

- `modular-video-production`：正式类型增加 `road-trip`，提供独立的初始化、统一生命周期与 `m2v road-trip fetch/basemap` 辅助命令。
- `video-frame-rate`：`road-trip` 固定 30 fps，其他类型保持原契约。

## Impact

- 受影响代码：新增 `src/m2v/types/road_trip/`、`src/m2v/types/route_common.py`；修改 `cli.py`、`commands.py`、`core/video_config.py`、`types/catalog.json`、`driving_route/materials.py`、`driving_route/amap.py`、`driving_route/basemap.py`、`engine/contract_page.py`；新增 `web/src/compositions/RoadTrip.tsx`、`web/src/compositions/roadtrip/`、`web/src/compositions/driving/MapLayer.tsx`；修改 `Root.tsx`、`video-config.json`、`vite.config.ts`。
- 受影响材料：新增 `videos/road-trip/<slug>/trip.json` 与 `routes/day-XX.json`（作品内容，不入 Git）。
- 受影响文档：新增 `references/road-trip-video.md`，同步 `guidance-routes.json`、README、PROJECT_PLAN、SKILL 生成区、`openspec/config.yaml`。
- 渲染成本：约 5400 帧、每日独立瓦片走廊，底图数量随天数增长；以 Day 4 样片实测，不预设吞吐承诺。
- 不涉及：其他类型的材料与画面、风格包、固定示例集合、三维车渲染。
