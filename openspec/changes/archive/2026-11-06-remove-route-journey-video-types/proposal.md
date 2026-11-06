## Why

`videos/route-journey/` 下的两个作品不再需要，而 `driving-route` 与 `road-trip` 两个视频类型只服务于这些作品。继续保留会留下没有消费者的地图取数、底图、专用渲染与制作文档，扩大维护面，并让类型目录、命令入口和规格继续暴露已经放弃的能力。

## What Changes

- 删除 `videos/route-journey/` 下的全部作品与产物（内容目录，本就不入库）。
- 移除 `driving-route` 与 `road-trip` 两个视频类型的全部实现：Python 适配器、材料、取数、底图、布局、渲染与准备链路；前端 composition、契约页与模型。
- 删除统一入口中只服务这两个类型的 `m2v driving-route`、`m2v road-trip` 子命令及其分发分支。
- 删除类型目录中的两个类型登记与随之为空的 `route-journey` 类别；类别机制本身保留。
- 删除只被这两个类型使用的共享模块 `route_common.py`、`route_schema.py`、`core/geodesy.py`，并清理 `mercantile`、`geographiclib`、`@turf/*`、`d3-geo` 依赖。
- 删除两个类型的测试、测试夹具与只测其实现的地理数学测试。
- 删除当前能力规格 `driving-route-video`、`road-trip-video`，并更新 `modular-video-production`、`article-workspace`、`video-production-workflow` 中把这两个类型当作现状的描述。
- 删除两份类型制作指南与本地相关工作目录，更新 README、ARCHITECTURE、项目规划、Skill 路由与 OpenSpec 项目语境。
- 保留 `openspec/changes/archive/` 下的历史变更记录，不改写历史。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `driving-route-video`：整个能力移除。
- `road-trip-video`：整个能力移除。
- `modular-video-production`：类型清单、初始化示例与统一制作入口不再包含两个路线类型；类别登记能力保留。
- `article-workspace`：分类类型的路径示例改为抽象类别，不再引用已删除的类型。
- `video-production-workflow`：内置类型指南名单移除两个路线类型。

## Impact

- 内容目录：`videos/route-journey/`（1.3 GB，未入库）。
- 后端代码：`src/m2v/types/driving_route/`、`src/m2v/types/road_trip/`、`src/m2v/types/route_common.py`、`src/m2v/types/route_schema.py`、`src/m2v/core/geodesy.py`、`src/m2v/cli.py`、`src/m2v/commands.py`、`src/m2v/core/video_config.py`、`src/m2v/engine/contract_page.py`、`src/m2v/type_system/catalog.json`。
- 前端代码：`web/src/types/driving_route/`、`web/src/types/road_trip/`、`web/roadtrip.html`、`web/src/Root.tsx`、`web/src/video-config.*`、`web/vite.config.ts`、`web/package.json` 与锁文件。
- 测试：`tests/types/driving_route/`、`tests/types/road_trip/`、`tests/helpers/driving_route.py`、`tests/helpers/road_trip.py`、`tests/common/test_geodesy.py` 及共享测试中的类型清单断言。
- 文档与规格：两份制作指南、`README.md`、`ARCHITECTURE.md`、`docs/PROJECT_PLAN.md`、`.agents/skills/material2video/` 的类型路由与路径说明、`openspec/config.yaml` 与相关规格。
- 依赖：移除 `mercantile`、`geographiclib`、`@turf/distance`、`@turf/helpers`、`d3-geo`、`@types/d3-geo`。
