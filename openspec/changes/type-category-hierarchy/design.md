## Context

动机与范围见 [proposal.md](proposal.md)。类型目录已经是类型身份、材料入口与文档文案的单一来源（`src/m2v/types/catalog.json`），但「类别」不是一个现有概念：类型清单、`m2v types`、`m2v init` 的路径推导、`relocate` 的目标路径和文档生成都假设类型是唯一分层。

本次要加入的是一条**两级的固定层级**：类别 → 类型。类型仍是唯一可执行单位（有适配器、能 `init`、有材料与渲染生命周期）；类别只回答「这个类型属于哪一族」。不做任意深度的树，也不让类别继承或覆盖类型行为。

## Goals / Non-Goals

**Goals:**

- 「路线旅程」成为 `driving-route` 与 `road-trip` 的共同父类别。
- 父子关系进入类型目录这一单一来源，派生 `m2v types`、规范作品位置、`init`、`relocate` 与三份文档清单。
- 分类类型的作品目录体现类别：`videos/<category>/<type>/<slug>/`。
- 旧位置作品有明确、可重试、带完整备份的迁移路径。
- 不改变任何类型的材料、渲染、帧率与评审契约。

**Non-Goals:**

- 不支持类别嵌套、类别级材料、类别级渲染或类别级默认值。
- 不自动扫描并搬移已有作品；迁移由用户显式执行 `m2v relocate`。
- 不保留类型目录 v1 兼容读取。
- 本轮只登记 `route-journey` 一个类别，其余类型保持未分类。

## Decisions

### 1. 类别是目录数据，类型仍是唯一执行单位

`catalog.json` 顶层新增 `categories`，每个类别有 `id`、`title`、`description`；每个类型增加可选 `category` 字段指向类别 `id`。

- 成员关系写在类型上，而不是类别内的成员数组：一个类型最多属于一个类别，避免两份成员列表漂移。
- 类别必须至少有一个成员；类别 `id` 不得与任何类型名相同，避免 `--type` 和路径层级歧义。
- `registry.get("<类别 id>")` 不接受类别，报错列出其子类型。

替代方案是「类别拥有成员列表」或「多级树」。前者需要校验反向一致性；后者对当前规模没有收益，且会让规范路径与文档生成复杂化。

### 2. 规范位置由类别推导

新增 `Entry.workspace_parts()`：分类类型返回 `(category, type)`，未分类返回 `(type,)`。所有位置逻辑只消费这一处：

- 分类类型规范位置：`videos/<category>/<type>/<slug>/`；
- 未分类类型规范位置：`videos/<type>/<slug>/`；
- `init` 的 `<slug>` 参数直接落到规范位置；
- 显式相对路径必须与规范位置完全一致，否则报错并给出正确前缀；
- 作品级命令校验声明类型的位置，非规范位置提示执行 `m2v relocate`。

类别不进入 `project.json`：作品类型仍是叶子类型，材料与准备指纹无需变化。

### 3. `relocate` 从「旧 videos/<slug>」扩展为「迁移到规范位置」

现有 `relocate` 只接受 `videos/<slug>/`，目标固定 `videos/<type>/<slug>/`。改为：

- 来源必须位于工作区 `videos/` 下且含 `project.json`（迁移重试时允许只剩冲突文件，依据备份读取 manifest）；
- 目标由 `Entry.workspace_parts()` 推导；
- 来源已在规范位置时明确报错，不移动文件；
- 保留完整备份、冲突不覆盖、可重试；
- 找不到来源时，在 `videos/` 的两级和三级目录中查找同名已迁移作品并报告其位置。

这样旧平铺分类作品不需要单独脚本，也不引入兼容分支。

### 4. 文档生成按类别分组

`sync_docs.py` 从「遍历 entries」改为「遍历 categories → 成员，再输出未分类」。README 与项目规划使用类别标题加列表；Skill 使用「类别 | 类型 | 创作指导」三列表格。类别描述在 README 与项目规划中随标题展示。

生成区域仍以成对标记界定，重新生成必须幂等；未分类类型始终可见，不会被类别分组隐藏。

### 5. 不自动迁移已有作品

仓库内 `videos/driving-route/*` 与 `videos/road-trip/*` 是内容，不入库。代码变更后它们会被位置校验拒绝，错误信息给出规范位置与 `m2v relocate`。是否搬移、何时搬移由用户决定，避免未经确认复制大体积产物或占用双倍磁盘。

## Risks / Trade-offs

- **既有作品暂时不可用**：旧平铺分类作品在校验层失败，直到执行 `relocate`。错误文案必须直接可照做。
- **迁移备份占空间**：`relocate` 会完整复制一次作品（含 `outputs/`）。这是既有约定，本轮不改变；在文档中说明。
- **层级只有两级**：未来若出现第三级，需要新的目录版本与迁移；当前规模不值得提前设计。
- **类别描述展示有限**：Skill 表格只有标题列，类别描述只在 README 与项目规划出现；不为此新增重复字段。

## Migration Plan

1. 升级 `catalog.json` 到 `schemaVersion: 2`，登记 `route-journey` 与两个成员。
2. 更新 `catalog.py`、`registry.py`、`commands.py`、`relocation.py`、`sync_docs.py`。
3. 重新生成三份文档，更新路径契约与类型参考文档。
4. 运行默认测试；路径与迁移用例覆盖分类与未分类两种形态。
5. 用户对本地旧作品执行 `uv run m2v relocate --project videos/driving-route/<slug>`（或 `videos/road-trip/<slug>`）完成迁移。
6. 归档本变更，使 `openspec/specs/` 反映已实现行为。

## Open Questions

无。类别层级、目录是否嵌套与分组范围已由用户确认：目录嵌套，且本轮只建「路线旅程」组。
