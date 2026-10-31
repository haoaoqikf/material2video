## 1. 类型与材料

- [ ] 1.1 在 `types/catalog.json` 登记 `road-trip`（描述、summary、plan、skillGuide、`trip.json` 模板），并在 `cli.py` 注册适配器；`m2v types` 与 `init` 能输出并写出模板。
- [ ] 1.2 在 `core/video_config.py` 与 `web/src/video-config.json` 增加 `road-trip` 固定 30 fps，`default_fps("road-trip")` 有测试。
- [ ] 1.3 实现 `trip.json` v1 校验：单一材料、天数与 day id 唯一、route 路径固定 `routes/day-XX.json`、不出现手填里程/时长/坐标、事实必须带 `sourceId`、音效四选一、音乐必须为程序化音床配置。
- [ ] 1.4 实现每日 `route.json` v1 校验：steps 首尾连续 25 米、端点一致、第 1 天定位点 ≤1 公里、第 N 天起点与前一天终点 ≤1 米、via 落在步骤链上、`acquisition` 不含 Key。
- [ ] 1.5 抽取 `src/m2v/types/route_common.py`（sourceUsage、geocoded place、steps 连续性、cost/cities/行政区），`driving_route/materials.py` 委托后错误文案与现有测试不变。
- [ ] 1.6 材料与注册测试：`tests/road_trip_helpers.py`、`tests/test_road_trip_materials.py`，覆盖模板一致、占位拒绝、链式衔接、事实来源、未知字段。

## 2. 多段取数

- [ ] 2.1 实现 `road_trip/fetch.py`：第 1 天 geocode，逐天按 via 顺序调用 `AmapClient.drive`，第 N 天起点取前一天 `endPoint`。
- [ ] 2.2 实现 `routePreference: "g318"`：避开高速策略 + via 节点校验；取数后检查关键节点落在步骤链上，不符合时失败并指出缺口。
- [ ] 2.3 实现全局行政区去重、`cities` 与 `administrativePlaces` 合并，保持现有行政规则（市辖区不单列）。
- [ ] 2.4 实现原子写入：先组装并全量校验，再快照旧文件、逐份替换，失败恢复全部旧文件；Key 不出现在材料、日志、异常与临时文件。
- [ ] 2.5 `m2v road-trip fetch` 命令分发与测试：链式起点、via、回滚、无 Key、授权门禁、传输失败、取数期间材料变化。

## 3. 多段底图

- [ ] 3.1 实现 `road_trip/basemap.py` 的全局概览、每日概览、每日跟随走廊；复用现有瓦片下载、拼接、内容寻址与原子替换。
- [ ] 3.2 走廊计划不读取旁白或时长；相同路线与 layout 版本生成相同清单摘要，并有确定性测试。
- [ ] 3.3 支持按天 `basemapStyle: road|satellite`，瓦片尺寸与来源署名沿用现有约定。
- [ ] 3.4 实现每日 2200 与全片 6000 块 / 500 MB 预算；超限失败并报告实际值，不静默降 zoom。
- [ ] 3.5 实现 `index.json` 与每日 `manifest.json`；复用已有目录不重复下载，失败清理本次新文件并保留旧索引。
- [ ] 3.6 `m2v road-trip basemap` 命令分发与测试：概览、走廊、样式切换、上限、复用、原子性、缺块报告。

## 4. 时间轴、相机与前端

- [ ] 4.1 实现每日帧分配：最小帧加里程加权余量、最大余数法、口播不截断、600 秒硬上限，并有确定性测试。
- [ ] 4.2 实现旁白/卡片/音效锚点解析：day-start、day-arrival、segment-start/end、landmark、trip-start/end 到全局帧。
- [ ] 4.3 实现 `roadtrip/camera.ts`：每日开场推近、12× 跟随、当天概览收束、末日渐次收束到全局；Day 4 在 72 拐窗口平滑切到 14×。
- [ ] 4.4 从 `DrivingRoute.tsx` 抽 `driving/MapLayer.tsx`，先抽取不改行为；`DrivingRoute.test.tsx` 全量回归通过。
- [ ] 4.5 实现 `RoadTrip.tsx` 与 `roadtrip/` 纯函数层、章节卡、数据卡、Day ribbon、字幕层；贴路、朝向与整像素平移复用现有函数。
- [ ] 4.6 在 `Root.tsx` 注册 `RoadTrip` composition；契约页按材料分派或新增独立入口，layout check 能驱动该 composition。
- [ ] 4.7 前端测试：帧→day 映射、日边界相机连续、倍率切换、字幕安全区、卡片不遮挡、markup 无 data URI、同帧确定性。

## 5. 音频与字幕

- [ ] 5.1 接入共享 TTS：显式音色、旁白摘要绑定、逐段合成与缓存；失败不写准备记录。
- [ ] 5.2 生成字幕 cue：≤28 字断句、全局帧换算、段窗口 clamp；`prepared.json` 的 `subtitles` 与 props 一致。
- [ ] 5.3 实现音效来源解析（builtin/synthesis/assetId/sourceRef）与锚点定位，输出 `audio.Effect`。
- [ ] 5.4 实现 `road_trip/ambient.py` 程序化音床：30 秒无缝循环、整数周期频率、固定种子、生成器版本与 CC0 留证；重复生成摘要一致。
- [ ] 5.5 实现 `concatenate → mix（含 ducking、envelope、silence）→ master`，母版登记为准备输入。
- [ ] 5.6 实现 `mux` 与音频验收：AAC-LC、44.1 kHz、2 声道、−14 LUFS、≤−1 dBTP；preview 从母版切出对应区间。
- [ ] 5.7 音频与字幕测试：音效定位、ducking、音床接缝、母版响度、preview 切片、无音轨判断。

## 6. 渲染与验收

- [ ] 6.1 实现 `road_trip/render.py`：`current`、`prepared_check`、`layout_check`、preview/render、`delivery.export_once`。
- [ ] 6.2 准备记录只存底图路径与摘要；渲染注入 `assetBase`，前端只挂可见瓦片；`prepared.json` 无 `data:image` 且 <50 MB。
- [ ] 6.3 实现 `has_audio(prepared)`，正式成片按 `expect_audio=True` 验收，不依赖 general 的 `declared_audio`。
- [ ] 6.4 实现溯源与性能报告：材料与底图摘要、音色与语速、母版摘要、候选绑定。
- [ ] 6.5 集成测试：2 天合成 fixture（fake 取数/TTS/瓦片）端到端通过 init→fetch→basemap→prepare→preview→render。
- [ ] 6.6 渲染测试：候选复用、输入变化失效、音频缺失失败、帧数/尺寸/帧率验收、重复渲染确定性。

## 7. 文档与类型清单

- [ ] 7.1 新增 `.agents/skills/material2video/references/road-trip-video.md`，登记 `guidance-routes.json`，`test_doc_examples.py` 可达性通过。
- [ ] 7.2 更新 `README.md`、`docs/PROJECT_PLAN.md`、`SKILL.md` 生成区与 `openspec/config.yaml` 类型清单；`sync_docs.py --check` 通过。
- [ ] 7.3 更新 `tests/test_general_type.py` 的类型集合断言与 `tests/test_type_catalog.py` 相关预期。
- [ ] 7.4 检查 `ARCHITECTURE.md` 的依赖方向说明，确认共享抽取未扩大类型私有依赖。

## 8. 318 首例与交付

- [ ] 8.1 完成 7 天 `trip.json`：停靠点、via、旁白、卡片、音效、事实来源、`sourceUsage` 与音色选择记录；旁白总长约 380–450 字。
- [ ] 8.2 落实 `M2V_AMAP_KEY` 与授权后执行真实 fetch，核验 G318 关键节点、日间衔接、里程与行政区；记录材料摘要，不将内容入库。
- [ ] 8.3 生成底图并核对每日走廊、概览、卫星/普通切换与全片预算。
- [ ] 8.4 完成 Day 4 单日样片（芒康→八宿，约 30 秒）：1080×1920/30 fps、AAC-LC 音频、字幕安全区、轨迹贴路、72 拐变倍率、prepared <50 MB、无外网请求。
- [ ] 8.5 对 Day 4 样片执行独立子代理视觉评审，关闭全部必改项后进入全片。
- [ ] 8.6 准备并渲染七天全片（约 5400 帧），通过画面、音频、响度、候选绑定与确定性验收。
- [ ] 8.7 对全片执行独立评审与 QA，记录评审包、代表帧、响度量测与发布说明。
- [ ] 8.8 运行 `uv run pytest --full`、前端测试/类型检查/构建、`openspec validate --specs`；检查暂存内容不含 Key、作品、生成媒体，按决策 12 只提交本变更相关改动。
- [ ] 8.9 归档变更：同步 `openspec/specs/road-trip-video/`、`modular-video-production`、`video-frame-rate` 主规格，移入 `changes/archive/`，单独提交归档结果。
