## Why

同一个「视频类型」事实（名称、说明、材料入口、初始化模板、文档文案）目前同时存在于 7 个地方，且没有任何一致性检查：代码侧有 `registry` 注册、`core/project.py` 的 `_TYPES` 白名单与 `defaults` 材料映射、`cli.py` 的 `init` 模板字典；文档侧有 `README.md` 的类型清单、`.agents/skills/material2video/SKILL.md` 的类型表格、`docs/PROJECT_PLAN.md` 的类型条目。

后果是双重的：新增类型要手工改 4 处代码加 3 份文档，漏改的报错还指向不了原因（漏 `_TYPES` 报「未知视频类型」，漏 `init` 模板被兜成「参数或材料错误」）；文档与代码之间只要有一次漏改就会长期不一致，而当前 891 项测试不会发现——没有任何用例读取这些文档。

仓库已经有一个可复用的成熟范式：视觉原语目录以 `web/src/registry/registry.json` 为单一来源，生成 Python 镜像 `src/m2v/core/catalog.py`，并由 `tests/test_web_registry.py` 断言「重新生成的产物与磁盘逐字节相同」。本次把同一范式用到视频类型上。

## What Changes

- 新增 `src/m2v/types/catalog.json` 作为视频类型的**单一来源**：登记每个类型的名称、一句话说明、README 用说明、规划用说明、Skill 指导文档链接，以及材料入口（名称、默认文件名、初始化模板内容）。
- 新增 `src/m2v/types/catalog.py`：类型目录的严格加载器与查询接口（登记项校验、按名查询、材料映射、初始化模板），未登记或格式错误的目录在导入期即失败。
- `VideoType` 只保留行为（`validate/prepare/preview/render` 与可选钩子）与名称；类型说明改由类型目录提供，`m2v types`、`registry.get` 的报错文案统一取自该来源。
- `core/project.py` 移除 `_TYPES` 白名单与 `defaults` 材料映射：`create_project` 由调用方传入材料入口，`load_project` 不再自带类型白名单，未知类型的判定与文案收敛到 `registry.get`（仍保证在渲染前失败）。
- `cli.py` 移除按类型名硬编码的 `init` 模板字典与 `financial-timeseries` 特例分支，改由类型目录写出材料模板；新增类型不再需要改 CLI。
- 修复 `init` 对 `article-narrative` 的既有缺陷：该类型的模板被外层文件键包裹，写出的 `storyboard.json` 顶层是 `{"storyboard.json": {...}}` 而不是分镜本身，导致刚初始化的文章作品校验失败（实测 `m2v validate` 报「不支持 v4 之前分镜」，退出码 1）。类型目录登记正确的 v4 分镜对象，`init` 产物可直接通过该类型校验。
- 三份文档中的类型清单改为**生成块**（带起止标记），由新脚本 `.agents/skills/material2video/scripts/sync_docs.py` 从类型目录重写：`README.md` 的「当前视频类型」、`SKILL.md` 的类型表格、`docs/PROJECT_PLAN.md` 的类型条目。
- 新增 `tests/test_type_catalog.py`：断言类型目录与 `registry` 名称集合一致、生成产物与磁盘逐字节一致、材料入口与初始化模板齐全；并保留「注册新类型无需改 CLI 分发」这一既有扩展点语义。
- **BREAKING**（内部 API）：`m2v.core.project.create_project` 新增必填的材料入口参数；仓库内调用点（`cli.py`、测试夹具）同步更新，作品目录与材料格式不变。

## Capabilities

### New Capabilities

（无。本次不引入新的视频类型或新的制作能力。）

### Modified Capabilities

- `modular-video-production`: 新增三条需求——类型身份、材料入口与文档文案必须在单一类型目录中登记并由代码派生；`m2v init` 为已登记类型生成的材料必须可直接通过该类型校验；README、Skill 与规划文档中的类型清单必须由该来源生成并可校验一致。

## Impact

- `src/m2v/types/catalog.json`、`src/m2v/types/catalog.py`（新增）；`src/m2v/types/registry.py`（`VideoType` 去掉说明字段、注册时校验目录登记）。
- `src/m2v/core/project.py`（移除 `_TYPES` 与 `defaults`）；`src/m2v/cli.py`（`init` 改为数据驱动、`types` 说明取自目录）。
- `src/m2v/types/{article,financial,general}/adapter.py`：类型构造参数随 `VideoType` 调整，行为实现不变。
- 文档：`README.md`、`.agents/skills/material2video/SKILL.md`、`docs/PROJECT_PLAN.md` 增加生成块；新增同步脚本。
- 测试：新增 `tests/test_type_catalog.py`；`tests/test_project_cli.py`、`tests/test_general_video.py` 更新 `create_project` 调用点；`tests/test_project_cli.py` 的类型扩展点用例语义保持不变。
- 契约与产物：项目 `schemaVersion`、材料格式、分镜结构、渲染契约、缓存键、成片输出与溯源字段全部不变；`m2v init` 对 `financial-timeseries` 与 `general` 写出的文件名与内容与本次之前逐字节一致，对 `article-narrative` 修正为可直接校验的 v4 分镜（原包裹层级是缺陷，见 What Changes）。
- 验证方式：`uv run pytest`（含新增类型目录与 init 产物用例）、`uv run m2v types`、对三个既有类型执行 `m2v init` 并逐一比对（金融与通用逐字节一致、文章可直接 `validate` 通过）、运行 `sync_docs.py` 后 `git diff` 应无变化。
