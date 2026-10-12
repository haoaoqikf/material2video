## 1. 基线与类型目录

- [ ] 1.1 用改动前的实现为三个类型生成初始化基线并记录逐文件摘要：`uv run m2v init --type article-narrative|financial-timeseries|general --project .gen/type-catalog-baseline/<type>`；验证：`.gen/type-catalog-baseline/` 下每个材料文件都有 sha256 记录，且 `git status` 不出现仓库内新增文件（`.gen/` 已被忽略）
- [ ] 1.2 新增 `src/m2v/types/catalog.json`，登记三个类型的名称、一句话说明、README 文案、规划文案、Skill 指导链接、材料入口（材料名、默认文件名）与初始化模板内容（模板 MUST 是 JSON 对象，不是转义字符串）；验证：文件可被 `json.load` 解析，且其中每个模板对象按 `json.dumps(ensure_ascii=False, indent=2)` 经 `Path.write_text` 落盘后与 1.1 基线文件逐字节一致（已用 `.gen/check_template_roundtrip.py` 预验证为 5/5 一致）
- [ ] 1.3 新增 `src/m2v/types/catalog.py`，提供严格加载与查询接口（登记项列表、按名查询、名称集合、材料映射、初始化模板），对缺字段、空文案、空材料、非法文件名的登记项报错；验证：新增用例覆盖合法目录与至少三种非法目录，非法目录在加载期即报错并指出问题字段

## 2. 代码侧收敛到单一来源

- [ ] 2.1 `src/m2v/types/registry.py` 的 `VideoType` 去掉说明字段，`registry.get` 在使用未登记类型时报错并给出登记指引，`m2v types` 仍能列出全部已注册类型；验证：`tests/test_project_cli.py` 中「注册自定义类型后出现在 `m2v types`」的既有用例语义保持通过
- [ ] 2.2 `src/m2v/core/project.py` 移除 `_TYPES` 白名单与 `defaults` 材料映射，`create_project` 改为接收材料入口参数，`load_project` 不再自带类型校验；验证：作品描述声明未知类型时，`m2v validate/prepare/render` 均在渲染前以「未知视频类型」失败并指向 `m2v types`，退出码为 2
- [ ] 2.3 `src/m2v/cli.py` 的 `init` 改为数据驱动：材料文件名与模板内容都取自类型目录，删除硬编码模板字典与 `financial-timeseries` 的多文件特例分支；`types` 的说明取自类型目录；验证：对三个类型各执行一次 `m2v init`，产物与 1.1 基线逐字节一致（含文件名、键序、缩进与结尾换行）——写盘沿用 `Path.write_text(json.dumps(..., ensure_ascii=False, indent=2) + "\n", encoding="utf-8")`，改用二进制或 `newline=""` 会让 Windows 上的 CRLF 变成 LF 而被判为不一致
- [ ] 2.4 更新仓库内 `create_project` 的调用点与三处适配器的 `VideoType` 构造；验证：`uv run pytest -m "not slow"` 全绿

## 3. 文档生成

- [ ] 3.1 在 `README.md`、`.agents/skills/material2video/SKILL.md`、`docs/PROJECT_PLAN.md` 的类型清单外加上成对生成标记；验证：三份文档各有一对标记，且块外人工文本（README 的示例集合说明、PROJECT_PLAN 的 `src/m2v` 目标条目、SKILL 的其余章节）未被包进块内
- [ ] 3.2 新增 `.agents/skills/material2video/scripts/sync_docs.py`，提供返回「文档路径 → 期望全文」的构造入口与写盘入口，任一文档缺少标记时抛错而不是跳过；验证：运行脚本后 `git diff` 为空（重新生成幂等）；临时删除任一标记后脚本报错并指出该文档

## 4. 一致性校验

- [ ] 4.1 新增 `tests/test_type_catalog.py`，断言类型目录与 `registry` 的名称集合双向一致（内置类型无漏登记、目录无孤儿登记项）且生成产物与磁盘逐字节一致；验证：用例通过；手工改动 README 中任一类型说明后该用例失败并指出文档路径
- [ ] 4.2 补一条断言确保 `m2v types` 输出的说明与类型目录同源（而不是另一处常量）；验证：用例通过，且改动类型目录中的说明后 `m2v types` 输出随之变化

## 5. 全量与交付验证

- [ ] 5.1 运行 README 记载的验收命令；验证：`uv run pytest`（含 slow）全绿，`uv run m2v types` 列出三个类型及其目录说明
- [ ] 5.2 复核既有作品与示例不受影响：对 `examples/keynote-baseline` 执行 `uv run m2v validate --project examples/keynote-baseline`；验证：材料校验通过，且既有作品不需要重新 prepare（材料与准备记录指纹未变）
- [ ] 5.3 更新 README 的视频类型章节说明与 Skill 的类型表说明，使「新增类型只在类型目录登记 + 实现行为」与实现一致；验证：两份文档中不再出现需要改 CLI 分发或作品契约白名单的表述，且与 `m2v types`、`openspec/specs/modular-video-production/spec.md` 描述一致

## 6. 归档与提交

- [ ] 6.1 把增量规格同步进 `openspec/specs/modular-video-production/spec.md` 主规格，并将变更目录移入 `openspec/changes/archive/`；验证：`openspec list` 无进行中变更，主规格包含本次新增的两条需求
- [ ] 6.2 提交本次代码、测试、文档与归档结果；验证：`git status` 干净，提交仅包含本变更相关文件（不含被忽略的产物、缓存与基线目录）
