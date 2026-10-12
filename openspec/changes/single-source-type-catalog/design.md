## Context

动机见 proposal.md。设计只受三条既有约束支配：

1. **分层已经成立，必须保持**：实测 `core/` 与 `engine/` 对 `m2v.types.*` 的导入为零，依赖方向是 `cli → types → {core, engine}`。作品契约（`core/project.py`）不能为了查类型目录而反向导入 `types/`。
2. **已有可复用范式**：视觉原语目录以 `web/src/registry/registry.json` 为源、生成 Python 镜像并由 `tests/test_web_registry.py` 断言磁盘一致；`tests/conftest.py` 已把 `.agents/skills/material2video/scripts` 加入 `sys.path`，脚本可直接被测试导入。
3. **现有事实**：类型身份与材料同时存在于 `registry` 注册、`core/project.py` 的 `_TYPES`/`defaults`、`cli.py` 的 `init` 模板，以及 `README.md`、`SKILL.md`、`docs/PROJECT_PLAN.md` 三份文档；`m2v init` 目前对 `financial-timeseries` 有「写多个材料文件」的特例分支，其它类型写单文件。

## Goals / Non-Goals

**Goals:**

- 让「类型身份 + 材料入口 + 文档文案」只有一处可编辑的落点，且该落点同时服务于运行时、作品初始化与文档。
- 保持 `core/` 不依赖 `types/` 的分层。
- `m2v init` 对既有三个类型写出的文件名与内容逐字节不变。
- 文档漂移可被测试发现，而不是靠人记得同步。

**Non-Goals:**

- 不统一分镜契约的 Python / TypeScript 双写（`storyboard_v4.py` 与 `storyboardV4.ts` 各自校验同一契约），那是下一个变更。
- 不改变前端 composition 注册（`web/src/Root.tsx` 仍按画面需要手工登记 composition id）。
- 不为冻结的 `examples/` 集合开口子，也不改动示例本身。
- 不引入运行时包自省、不新增第三方依赖、不改 `project.json` 的 `schemaVersion`。

## Decisions

### 决策 1：单一来源是数据文件 `src/m2v/types/catalog.json`，而不是 Python 模块或各适配器

类型身份、材料入口与文档文案是**数据**，行为是**代码**。放进 JSON 后，文档生成器与一致性测试不需要导入任何适配器（也就不受 TTS、ffmpeg、Playwright 等重依赖影响），并能保留初始化模板的键序（`json.load` 保持插入顺序，重新序列化即逐字节稳定）。

- 备选 A：把字段加到各适配器构造的 `VideoType` 上（即现状的扩展）——身份与文案仍分散在三个文件，文档生成要导入全部适配器，且三份文档仍需手工同步。
- 备选 B：放在 `core/` 下的 Python 常量——违反分层（`core` 不应承载类型身份），且文档生成同样要导入。
- 备选 C：直接以 `web/` 侧的 JSON 为源（照搬原语目录方向）——类型是 Python 侧概念，源在 web 会让 `types/` 反向依赖前端工程。

### 决策 2：作品契约不再自带类型白名单，未知类型的判定收敛到 `registry.get`

`core/project.py` 移除 `_TYPES` 与 `defaults`：`create_project(directory, video_type, materials)` 由调用方（`cli`，从类型目录取材料入口）传入材料映射；`load_project` 不再校验类型名。未知类型仍**在渲染前失败**，但由 `registry.get` 报出「未知视频类型：X；运行 m2v types 查看可用类型」——比原来的「可用类型：a, b, c」更可操作，且文案也只有一处。

- 备选 A：让 `core` 读 `catalog.json`——破坏分层，且让底层承担类型身份。
- 备选 B：保留 `_TYPES` 只做「防止手改 project.json」——那第二处真源就还在，漂移依旧可能。
- 代价：`create_project` 是内部 API 的**破坏性变更**，仓库内 4 个调用点（`cli.py` 与两处测试夹具）同步更新。

### 决策 3：类型说明由目录提供，未登记的已注册类型显式标注而不是猜文案

`VideoType` 去掉 `description` 字段，`m2v types` 与 `registry.get` 的说明一律取类型目录。已注册但未登记的类型：`m2v types` 用一个显式标记列出（例如说明为「未在类型目录登记」），使用它的操作在渲染前失败。这样既保持「注册即可被 `m2v types` 发现」的既有扩展点语义（对应既有用例），又不允许缺失文案被静默当成空串。

### 决策 4：文档只重写带标记的生成块，块外人工文本保持人工维护

在三份文档中用成对 HTML 注释标记（起止各一行）包住类型清单：`README.md` 的「当前视频类型」条目、`SKILL.md` 的类型表格行、`docs/PROJECT_PLAN.md` 的类型条目。生成器只替换标记对之间的内容，`README` 中「三个固定示例为……」这类人工段落、`PROJECT_PLAN` 中 `src/m2v` 那条非类型目标都留在块外。**标记缺失时生成器必须报错而不是跳过**，否则「生成成功」会变成假象。

- 备选 A：整文件生成——会覆盖人工维护的内容，不可接受。
- 备选 B：只写一致性校验、不做生成——能发现漂移，但没有单一来源，改动仍要手抄三遍。

### 决策 5：生成器落在 `.agents/skills/material2video/scripts/sync_docs.py`

与既有 `sync_catalog.py` 同级，`tests/conftest.py` 已把该目录加入 `sys.path`，测试可直接 `import sync_docs` 并调用其 `build_outputs()`（返回「绝对路径 → 期望全文」映射）逐字节比对，无需在测试里另写一套拼装逻辑。写盘沿用仓库既有风格：临时文件 + `replace`。

### 决策 6：修掉 `article-narrative` 初始化模板的包裹缺陷，而不是把它固化进单一来源

实施中发现一处既有缺陷：`cli.py` 的 `init` 对非金融类型走「把整个模板字典写进单文件」的分支，而文章类型的模板字典本身是 `{"storyboard.json": {<v4 分镜>}}`，于是写出的 `storyboard.json` 顶层是文件名键而非分镜字段，`m2v validate` 直接报「不支持 v4 之前分镜」（实测退出码 1）。金融走多文件分支写的是内层内容，通用模板本身没有外层键，因此只有文章类型受影响；既有测试只覆盖金融的 init 产物，缺陷长期未被发现。

单个来源的构造流程会把这个模板原样录入目录，等于**把缺陷永久固化**。因此本变更顺手修正：目录登记内层 v4 分镜对象，`init` 对文章类型产出可直接校验的作品，并新增初始化产物用例守住（把目录改回包裹形态即失败）。

- 代价：文章的 init 产物不再与改动前逐字节一致，这是本次唯一有意的产物变化，已写入 proposal、spec 与 tasks。
- 备选：原样登记、另开变更修复——会让单一来源带着已知错误存活，且新类型作者会照抄错误形态。

## Risks / Trade-offs

- [初始化模板从 Python 字面量搬到 JSON 后产物不再逐字节一致] → **已实测**：把三个类型的模板对象收进目录、读回后用现有写法逐文件落盘，5 个材料文件 5/5 与改动前基线逐字节一致（键序、缩进、中文与结尾换行均保持）。结论是这条风险只取决于两件事：模板必须是 JSON 对象而非字符串，且写盘必须走与现在相同的文本模式路径。
- [换行风格随写盘方式改变] → Windows 上 `Path.write_text` 在文本模式下把 `\n` 翻译成 `\r\n`，实测基线文件均为 CRLF；若新实现改用二进制写入或 `newline=""`，产物会在 Windows 上变成 LF 而被逐字节比对判为不一致。因此 `init` 的写盘 MUST 沿用 `write_text(json.dumps(..., ensure_ascii=False, indent=2) + "\n", encoding="utf-8")`，并把「三个类型 init 产物与基线逐字节一致」作为完成条件。
- [生成块标记被人删除后生成器静默跳过，造成「已同步」的假象] → 生成器在任一文档缺标记时抛错；一致性测试覆盖该分支。
- [`create_project` 签名变更被仓库外的调用方依赖] → 该项目无对外发布的 Python API 契约（`pyproject` 未声明库用途），且 README 只宣传 `m2v` 命令；在变更说明与提交信息中标注为内部 API 变更。
- [`m2v types` 对未登记类型输出标记文案，可能被误读为可用类型] → 标记文案明确写「未在类型目录登记」，且使用该类型的操作在渲染前失败并给出登记指引。
- [修复文章初始化模板会改变既有产物] → 这是有意修复，已记录在 proposal 的 What Changes、spec 的「初始化材料立即可用」需求与 tasks 2.3/2.5；验收条件是「金融与通用逐字节一致 + 文章可直接校验通过 + 新增用例在改回包裹形态时失败」。
- [文档生成的表格/列表排版与现有风格不一致] → 生成器输出严格复用现有行的写法（`- \`name\`：说明` 与 `| \`name\` | 指导 |`），并以「重新生成后 `git diff` 为空」作为验收条件。

## Migration Plan

单次提交完成，无数据迁移：作品目录、材料格式、分镜结构与渲染契约均不变，既有作品不需要重新 `prepare`。回滚策略为还原该提交——由于 `catalog.json` 只承载原本散落的常量，回滚不产生残留状态。
