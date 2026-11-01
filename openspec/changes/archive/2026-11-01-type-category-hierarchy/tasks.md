## 1. 类型目录

- [x] 1.1 `catalog.json` 升级 `schemaVersion: 2`，新增 `categories` 与 `category` 字段；登记 `route-journey`（路线旅程）并归入 `driving-route`、`road-trip`。
- [x] 1.2 `catalog.py` 增加 `Category`、`Entry.category`、`workspace_parts()`、`Catalog.categories()/category()/types_in()/uncategorized()`；校验类别 id、空类别、未登记引用与类别/类型同名。
- [x] 1.3 `registry.get` 对类别名给出「类别不是视频类型」并列出子类型。
- [x] 1.4 `m2v types` 每条记录输出 `category` 与 `categoryTitle`。

## 2. 路径与迁移

- [x] 2.1 `m2v init` 按 `workspace_parts()` 落盘；显式相对路径必须等于规范路径，旧的平铺分类路径明确拒绝并给出正确前缀。
- [x] 2.2 作品位置校验按类别推导规范位置，错误提示 `m2v relocate`。
- [x] 2.3 `relocate` 支持 `videos/` 下任意非规范位置的统一契约作品，目标由类别推导；保留备份、冲突保留与重试。
- [x] 2.4 更新 `cli.py` 帮助、`workspace.py` 注释与迁移结果文案。

## 3. 文档

- [x] 3.1 `sync_docs.py` 按类别分组生成 README、Skill 表格与项目规划清单，未分类归入「未分类」。
- [x] 3.2 更新 `ARCHITECTURE.md`、`openspec/config.yaml`、`references/paths.md`、`references/driving-route-video.md` 及 README 中的路径示例。
- [x] 3.3 更新 `openspec/specs` 对应主规格（归档阶段完成）。

## 4. 测试与验证

- [x] 4.1 `test_type_catalog.py` 覆盖类别解析、校验失败、`m2v types` 字段、分类初始化路径、文档分组、schemaVersion 2。
- [x] 4.2 `test_project_cli.py` 覆盖分类类型的 `init` 拒绝平铺路径与 `relocate` 迁移平铺类型目录。
- [x] 4.3 更新受路径影响的类型测试。
- [x] 4.4 运行 `uv run pytest`、`uv run python .agents/skills/material2video/scripts/sync_docs.py --check`。
- [x] 4.5 检查暂存内容并提交本次改动；不包含 `videos/` 内容。
