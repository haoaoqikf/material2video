## 1. 内容与本地工作目录

- [x] 1.1 删除 `videos/route-journey/` 全部作品与产物。
- [x] 1.2 删除本地 `work/` 下只服务这两个类型的驱动路线工作目录。

## 2. 后端类型与命令

- [x] 2.1 删除 `src/m2v/types/driving_route/`、`src/m2v/types/road_trip/`、`route_common.py`、`route_schema.py` 与 `core/geodesy.py`。
- [x] 2.2 从 `cli.py` 移除两个适配器注册与 `driving-route`、`road-trip` 子命令；从 `commands.py` 移除分发分支。
- [x] 2.3 从 `core/video_config.py`、`web/src/video-config.*` 移除两个类型的帧率配置。
- [x] 2.4 从 `engine/contract_page.py` 移除只服务 road-trip 的契约页路径与静态服务。

## 3. 前端与 composition

- [x] 3.1 删除 `web/src/types/driving_route/`、`web/src/types/road_trip/` 与 `web/roadtrip.html`。
- [x] 3.2 从 `web/src/Root.tsx` 移除 `DrivingRoute`、`RoadTrip` composition；从 `web/vite.config.ts` 移除 roadtrip 入口。
- [x] 3.3 从 `web/package.json` 移除 `@turf/distance`、`@turf/helpers`、`d3-geo`、`@types/d3-geo` 并同步锁文件。

## 4. 类型目录与依赖

- [x] 4.1 从 `src/m2v/type_system/catalog.json` 删除两个类型登记与空的 `route-journey` 类别。
- [x] 4.2 从 `pyproject.toml` 移除 `mercantile`、`geographiclib` 并同步 `uv.lock`。

## 5. 测试

- [x] 5.1 删除两个类型的测试目录与 `tests/helpers/` 夹具、`tests/common/test_geodesy.py`。
- [x] 5.2 更新共享测试中的类型清单、初始化、迁移、可选评审与帧率断言，改为只覆盖仍在的类型或抽象类别。

## 6. 文档与 OpenSpec

- [x] 6.1 删除 `references/driving-route-video.md`、`references/road-trip-video.md`，更新 Skill 类型表、路由、路径、交付与溯源说明。
- [x] 6.2 重新生成 README、SKILL、项目规划中的类型清单，并清理手写的类型说明段落。
- [x] 6.3 更新 `ARCHITECTURE.md`、`docs/PROJECT_PLAN.md` 与 `openspec/config.yaml` 的项目语境。
- [x] 6.4 用本变更的规格增量删除两个能力，并更新 `modular-video-production`、`article-workspace`、`video-production-workflow`。

## 7. 验证与归档

- [x] 7.1 运行受影响的 Python 测试、前端测试与前端构建，确认类型目录、初始化与渲染入口无回归。
- [x] 7.2 检查暂存内容并提交实施结果。
- [x] 7.3 同步 `openspec/specs/` 主规格，归档变更并提交归档结果。
