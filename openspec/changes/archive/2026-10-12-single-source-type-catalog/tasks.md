## 1. 基线与类型目录

- [x] 1.1 用改动前的实现为三个类型生成初始化基线并记录逐文件摘要：`uv run m2v init --type article-narrative|financial-timeseries|general --project .gen/type-catalog-baseline/<type>`；验证：`.gen/type-catalog-baseline/` 下每个材料文件都有 sha256 记录（`sha256.json`），且 `git status` 不出现仓库内新增文件（`.gen/` 已被忽略）——文章类型这一份基线记录了「模板被外层文件名键包裹」的缺陷现状，用于确认本次该类型产物只发生这一处预期变化
- [x] 1.2 新增 `src/m2v/types/catalog.json`，登记三个类型的名称、一句话说明、README 文案、规划文案、Skill 指导链接、材料入口（材料名、默认文件名）与初始化模板内容（模板 MUST 是 JSON 对象，不是转义字符串）；验证：文件可被 `json.load` 解析；金融与通用类型的模板按 `json.dumps(ensure_ascii=False, indent=2)` 经 `Path.write_text` 落盘后与 1.1 基线逐字节一致（已预验证 4/4）；文章类型的模板登记为修正后的 v4 分镜对象，顶层即 `version/schemaVersion/fps/width/height/title/...` 且不含外层 `storyboard.json` 键
- [x] 1.3 新增 `src/m2v/types/catalog.py`，提供严格加载与查询接口（登记项列表、按名查询、名称集合、材料映射、初始化模板），对缺字段、空文案、空材料、非法文件名的登记项报错；验证：用例覆盖合法目录与 8 种非法目录（版本不符、空类型表、重复类型、空文案、非法类型名、空材料表、越界文件名、空模板），非法目录在加载期即报错并指出问题字段——另发现并修正一处字段映射错误（目录中的 `skillGuide` 对应属性 `skill_guide`），修正前加载随包目录直接 `TypeError`

## 2. 代码侧收敛到单一来源

- [x] 2.1 `src/m2v/types/registry.py` 的 `VideoType` 去掉说明字段，`registry.get` 在使用未登记类型时报错并给出登记指引，`m2v types` 仍能列出全部已注册类型；验证：`tests/test_project_cli.py` 中「注册自定义类型后出现在 `m2v types`」的既有用例语义保持通过；未登记类型的说明显示为「未在类型目录登记」而不是空串，新增用例覆盖
- [x] 2.2 `src/m2v/core/project.py` 移除 `_TYPES` 白名单与 `defaults` 材料映射，`create_project` 改为接收材料入口参数，`load_project` 不再自带类型校验；验证：作品描述声明未知类型时，`m2v validate/prepare/render` 均在渲染前以「未知视频类型」失败并指向 `m2v types`——实测三条命令退出码均为 1，与改动前一致（未知类型是 `M2VError`，退出码 2 只用于 `init`/`migrate` 的类型错误与参数解析错误）
- [x] 2.3 `src/m2v/cli.py` 的 `init` 改为数据驱动：材料文件名与模板内容都取自类型目录，删除硬编码模板字典与 `financial-timeseries` 的多文件特例分支；`types` 的说明取自类型目录；验证：对三个类型各执行一次 `m2v init`，`financial-timeseries`（3 个材料）与 `general`（1 个材料）的产物与 1.1 基线逐字节一致（实测 4/4 OK；另核对三个 `project.json`：除随机 `id` 行外文本逐字节一致，键序与 `materials` 相同），`article-narrative` 的 `storyboard.json` 顶层为 v4 分镜字段（`version/schemaVersion/fps/...`）且 `uv run m2v validate` 不再报出「不支持 v4 之前分镜」（剩余报错均为占位内容待填写）——写盘沿用 `Path.write_text(json.dumps(..., ensure_ascii=False, indent=2) + "\n", encoding="utf-8")`
- [x] 2.4 更新仓库内 `create_project` 的调用点与三处适配器的 `VideoType` 构造；验证：`uv run pytest -m "not slow"` 全绿（实测 887 passed, 4 skipped, 14 deselected）
- [x] 2.5 新增初始化产物的回归用例：断言三个已登记类型的材料文件顶层结构与各自契约一致（文章类型顶层为 v4 分镜字段、不含文件名键包裹），并对文章类型断言 `m2v validate` 不报出结构包裹导致的错误；验证：用例通过；把目录中文章模板改回包裹形态后两条相关用例均失败（实测变异验证：`assert {...} <= {'storyboard.json'}` 与「被文件名键包裹」两条断言各失败一次），还原后 21 项全绿

## 3. 文档生成

- [x] 3.1 在 `README.md`、`.agents/skills/material2video/SKILL.md`、`docs/PROJECT_PLAN.md` 的类型清单外加上成对生成标记；验证：三份文档各有一对标记，且块外人工文本（README 的示例集合说明、PROJECT_PLAN 的 `src/m2v` 目标条目、SKILL 的其余章节）未被包进块内——`git diff` 显示三份文档各只新增两行标记，原有类型行逐字未动
- [x] 3.2 新增 `.agents/skills/material2video/scripts/sync_docs.py`，提供返回「文档路径 → 期望全文」的构造入口与写盘入口，任一文档缺少标记时抛错而不是跳过；验证：运行脚本后 `git diff` 为空（实测 `--check` 与写回模式均报「一致，无需改动」，退出码 0），标记缺失/重复/顺序颠倒四种形态各抛错并指出该文档（用例覆盖）；写回时保留各文件原有换行符，保证跨平台幂等

## 4. 一致性校验

- [x] 4.1 新增 `tests/test_type_catalog.py`，断言类型目录与 `registry` 的名称集合双向一致（内置类型无漏登记、目录无孤儿登记项）且生成产物与磁盘逐字节一致；验证：用例通过（21 项）；手工在 README 生成区内加一个类型后该用例失败并指出 `README.md`（实测变异验证），还原后复跑全绿
- [x] 4.2 补一条断言确保 `m2v types` 输出的说明与类型目录同源（而不是另一处常量）；验证：用例断言 `m2v types` 的「类型 → 说明」映射与目录登记项完全相等，任一处改动都会失败；另补一条用例把金融类型自带的两份文件清单（`financial.MATERIALS` 与适配器内的入口断言）与目录绑定，防止第三处副本分叉

## 5. 全量与交付验证

- [x] 5.1 运行 README 记载的验收命令；验证：`uv run pytest`（含 slow）全量 926 项、922 通过、4 跳过、0 失败，退出码 0（直接落盘日志计数，不经管道以免掩盖退出码）；`uv run m2v types` 列出三个类型及其目录说明；文档一致性演示：往类型目录临时加一个类型后 `sync_docs.py --check` 以退出码 1 报出三份文档漂移，重新生成后三份文档各多一行目录文案，随后按字节还原
- [x] 5.2 复核既有作品与示例不受影响：对 `examples/keynote-baseline` 执行 `uv run m2v validate --project examples/keynote-baseline`；验证：材料校验通过（4 个叙事阶段、1080 帧/36.0s），且 `uv run m2v status` 报告 `prepare: current`、`preview: current`——说明改动后重算的准备指纹与改动前写入 `outputs/prepared.json` 的指纹一致，既有作品不需要重新 prepare
- [x] 5.3 更新 README 的视频类型章节说明与 Skill 的类型表说明，使「新增类型只在类型目录登记 + 实现行为」与实现一致；验证：两份文档中不再出现需要改 CLI 分发或作品契约白名单的表述（新增段落明确写出「统一入口不按类型名硬编码分发，作品契约也不维护类型白名单与材料映射」），README 项目结构补上类型目录、Skill 新增「新增视频类型」小节；`sync_docs.py --check` 仍报一致，`m2v types` 与主规格描述一致

## 6. 归档与提交

- [x] 6.1 提交实现：代码、测试、三份文档、类型目录与本次规划产物（tasks 全为 `- [x]` 之后）；验证：`git status` 只包含本变更相关文件，不含被忽略的产物、缓存与基线目录——提交 `86cd660`，21 个文件（新增 `catalog.json`、`catalog.py`、`sync_docs.py`、`test_type_catalog.py`）
- [x] 6.2 归档并提交归档结果：把增量规格同步进 `openspec/specs/modular-video-production/spec.md` 主规格，再将变更目录移入 `openspec/changes/archive/`；验证：`openspec list` 报「No active changes found」，主规格由 4 条需求增至 7 条（新增「类型的单一登记来源」「初始化材料立即可用」「文档中的类型清单由类型目录生成」），`openspec validate --specs --strict` 25 项通过；同步时据实修正增量规格中一处与实测不符的表述——「未知类型在渲染前失败」原写「退出码为材料或参数错误」，实测未知类型走 `M2VError`、退出码为 1，已改为「执行或门禁失败（1）」，该改动随本次归档一起提交
