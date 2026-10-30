## Why

用户希望制作小车沿真实高速从一个地点行驶到另一个地点的地图动画，并将其作为与金融时间序列同级的独立视频类型。以“上海→郑州”作为首个作品，建立可更换起终点、在线取数与离线成片分离的制作能力。

## What Changes

- 新增 `driving-route` 类型，提供独立材料、校验、准备、预演、渲染及可选评审入口，不借用 general 分镜。
- 新增 `m2v driving-route fetch --project <目录>`：通过高德定位端点并按高速优先规划路线，从 `M2V_AMAP_KEY` 读取凭据，保存不含凭据的路线材料。
- 新增简洁二维地图动画：北向地图、小车沿真实路线移动并平滑转向、已走路段亮起、镜头平稳跟随；1920×1080、60 fps、默认30秒、无音轨。
- 首例使用上海人民广场到郑州二七广场，显示“上海”“郑州”；默认开场3秒全程、中段24秒行驶、最后3秒拉远收束。
- 复用共享无声生命周期、渲染与完整候选验收，新增类型指南和相关回归。首版不做卫星/三维底图、完整在线路网、本地轨迹导入、旁白或音乐。

## Capabilities

### New Capabilities

- `driving-route-video`：真实高速路线采集、可追溯离线材料、确定性小车与镜头动画、无声交付和首例验收。

### Modified Capabilities

- `modular-video-production`：正式类型增加 driving-route，提供独立初始化及类型辅助命令，保留已移除类型的拒绝行为。
- `video-frame-rate`：自驾路线使用固定60 fps，金融和 general 保持原契约。
- `stage-guidance-routing`：自驾路线进入独立制作指南，不套 general 三阶段。

## Impact

后续实施影响 Python 类型目录、适配器与 CLI、Web composition、测试、README、ARCHITECTURE、制作 Skill、阅读路由和项目规划。共享模块保持现有依赖方向，不新增地图 SDK 或运行时在线底图依赖。

首例内容计划放在 `videos/driving-route/shanghai-to-zhengzhou/`，材料、响应快照和媒体不入库；共享代码、测试、指南纳入 Git，不新增或替换五个固定风格示例。本轮仅交付此目录下的提案材料与校验记录，不改实现、主规格或当前能力文档，不取数、不渲染、不归档；后续实施通过后按项目约定提交并自动同步归档。
