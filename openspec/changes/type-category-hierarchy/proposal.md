## Why

现有六个视频类型在类型目录、`m2v types`、初始化路径和文档清单中是平铺的。`driving-route`（自驾路线）与 `road-trip`（多日地图游记）共享「真实道路 + 地图镜头 + 离线成片」的定位，却只能并列展示；随着类型增多，平铺清单既难发现同族能力，也让作品目录无法体现归属。

用户要求新增「路线旅程」大类，把这两个小类归入其中，并把父子类别做成项目级的通用设计，而不是一次性的文案分组。

## What Changes

- 类型目录升级为 `schemaVersion: 2`：新增顶层 `categories`（`id`、`title`、`description`），每个类型可声明唯一的 `category`。
- 新增类别 `route-journey`（「路线旅程」），成员为 `driving-route` 与 `road-trip`；其余类型保持未分类。类别只用于组织与发现，不是可执行类型，不能 `init`。
- 作品规范位置跟随类别：分类类型为 `videos/<category>/<type>/<slug>/`，未分类类型仍为 `videos/<type>/<slug>/`。
- `m2v init` 按规范位置创建作品；显式路径必须是该类型当前规范路径，旧的平铺分类路径明确拒绝并给出正确位置。
- `m2v relocate` 从「只迁移 `videos/<slug>`」扩展为「把 `videos/` 下任意非规范位置的统一契约作品迁移到当前规范位置」，因此旧的 `videos/driving-route/<slug>`、`videos/road-trip/<slug>` 也能迁移。
- `m2v types` 的每条记录增加 `category` 与 `categoryTitle`；直接以类别名调用 `init`/类型操作时，报错列出子类型。
- README、Skill、项目规划的类型清单按类别分组生成；未分类类型归入「未分类」。
- 同步更新路径契约、类型参考文档、OpenSpec 规格与测试。

不保留类型目录 v1 兼容分支，也不自动搬移已有作品；已有分类类型作品须显式执行 `m2v relocate`。

## Capabilities

### New Capabilities

无新增能力域；父子类别作为类型目录与工作区契约的一部分实现。

### Modified Capabilities

- `modular-video-production`：类型目录新增类别登记；规范作品位置、init、relocate、`m2v types` 与文档生成跟随类别。
- `article-workspace`：工作区规范路径与逐作品迁移按类别推导。
- `driving-route-video`：标准作品位置改为 `videos/route-journey/driving-route/<slug>`。
- `road-trip-video`：标准作品位置改为 `videos/route-journey/road-trip/<slug>`。

## Impact

- 代码：`src/m2v/types/catalog.py`、`catalog.json`、`registry.py`、`commands.py`、`cli.py`、`types/relocation.py`、`core/workspace.py` 注释、`.agents/skills/material2video/scripts/sync_docs.py`。
- 文档：`README.md`、`docs/PROJECT_PLAN.md`、`SKILL.md` 生成区、`ARCHITECTURE.md`、`openspec/config.yaml`、`references/paths.md`、`references/driving-route-video.md` 及 OpenSpec 规格。
- 测试：`tests/test_type_catalog.py`、`tests/test_project_cli.py`、`tests/test_driving_type.py` 及路径断言。
- 内容：仓库内 `videos/driving-route/*` 与 `videos/road-trip/*` 需在本地执行 `m2v relocate` 迁移；内容不入库，不随本次提交。
- 不涉及：类型行为、材料格式、渲染契约、帧率、风格包与示例集合。
