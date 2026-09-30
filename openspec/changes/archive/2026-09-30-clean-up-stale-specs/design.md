## Context

`openspec/specs/` 记录了 21 个能力、200 余条需求，但其中一批描述的对象已被删除：第三方组件分类接入与 `FrameSyncedCssAnimation`、vendored 弹簧求解器（`web/src/runtime/spring.ts`）、旧整页组件几何（`Loop` / `Exchange`）、`figures.js` 动效路径与 `api.progress`、`IDLE_TOKENS` 账本、分镜迁移程序。同时 contract 已从版本 2 走到版本 3、媒体清单从 2 走到 3，而规格里的版本号没跟着走。

motivation 见 `proposal.md`。约束来自两点：一是 `openspec/specs/` 的定位是「已实现行为的权威描述」，二是 `openspec` 的 delta 校验规则——`MODIFIED` **不得遗漏**主规格里已有的场景名（`openspec validate` 会直接报错，归档也会拒绝）。

## Goals / Non-Goals

**Goals:**
- 每个被改动的能力，其主规格在归档后只描述当前可达的行为。
- 有零引用证据的机制整条移除（第三方接入、弹簧、迁移、账本），不留空转需求。
- 版本号、字段归属、判据口径与实现逐条对齐。

**Non-Goals:**
- 不改产品行为：不改校验器逻辑、渲染路径、验收门槛或退出码。
- 不改能力标识与文件夹名（`declarative-video-scenes`、`react-component-registry` 名字是旧架构遗留，但改名会破坏引用与历史，只修 Purpose 措辞）。
- 不发明新需求来「填补」被删除的部分。

## Decisions

### 决策 1：场景名不可删，只能整条替换

`openspec validate` 对 `MODIFIED` 的约束是「不得遗漏主规格里已有的场景名」。因此：

- 只有**正文**需要改的条目（`font-coverage`、`font-subsetting`、`render-provenance`、`semantic-motion-timeline`、`visual-direction-pipeline`、`cinematic-directing`、`article-workspace`、`状态语汇覆盖每一种角色`、`组件自己拼出的颜色…`、`画面上的文字…`）走 `MODIFIED`，场景名逐字保留。
- **场景名本身**已失效的条目（`视觉表达受控`、`动效量测在验收流程里对任意作品生效`、`模块化设计令牌`、`设计语言的启用与兼容`、`帧驱动光晕的强度参数由设计层给`）走 `REMOVED` + `ADDED`，`ADDED` 用一个新的需求名。

  考虑过的替代：在同一 `MODIFIED` 里保留旧场景名、只改正文。被否决——场景名本身就在断言一个不可达状态（例如「未启用预设的页面不受影响」），留着它等于把已废止的行为写进当前规格。
  也考虑过 `REMOVED` + `ADDED` 用**同一个**需求名，被否决——归档时两条操作的先后顺序会让结果不可预期（可能先加后删，直接把需求删没），换新名可彻底避开这个歧义。

### 决策 2：`RENAMED` + `MODIFIED` 处理版本号改名

`remotion-renderer` 的需求名「版本 2 渲染契约」本身就是错误陈述，因此先用 `RENAMED`（`FROM` / `TO`），再对**新名**写 `MODIFIED` 携带完整正文与全部场景。名字保留版本号是刻意的：契约版本是这条需求的核心内容，改名比改正文更不容易被忽略。

### 决策 3：整条已废止的能力直接移除

`deterministic-third-party-adapters` 的 7 条需求全部以已删除的机制为对象。其中两条（依赖随仓库锁定、白名单视觉库的确定性规则）在 `code-driven-scenes` 里已有等价描述，所以整能力移除不会丢活需求。同理移除 `article-workspace` 的「迁移保护」——`storyboard-v3-contract` 已规定不提供迁移命令与回退。

### 决策 4：Purpose 直接改主规格

`openspec` 明确要求：delta 里不写 `## Purpose`，改既有能力的 Purpose 直接编辑主规格文件。因此 `remotion-renderer`、`declarative-video-scenes`、`react-component-registry`、`article-to-storyboard` 的 Purpose 是主规格直改，不出现在 delta 里。

## Risks / Trade-offs

- [需求改名会让别处对旧名的引用失效] → 全仓库只有 `frame-driven-motion` 正文提到「版本 2 渲染契约」，本次同批修掉；其余需求名没有跨文件引用。
- [`REMOVED` + `ADDED` 看起来像「删了再加」，评审时容易误读为功能反复] → 每个 `REMOVED` 都写了 `**Reason**` / `**Migration**`，并在 Reason 里点明「义务保留、只换口径」，`ADDED` 的名字也用可辨识的新名而不是同名。
- [直接改主规格 Purpose 绕过了 delta 审计] → 这是 `openspec` 的既定机制（delta 不支持 Purpose）；改动内容与四条 Purpose 的旧架构措辞一一对应，可在 `git diff` 里逐条核对。
- [删除空目录 `storyboard-scene-tree-migration/` 会丢掉「这里曾有一条能力」的线索] → 该目录未跟踪、无 `spec.md`，`openspec list --specs` 本来就不列出它；历史在 `openspec/changes/archive/2026-09-21-replace-page-components-with-scene-primitives/` 与 `2026-09-24-remove-legacy-storyboard-compatibility/` 里完整保留。

## Migration Plan

1. 写完 delta 与 Purpose 直改后 `openspec validate clean-up-stale-specs` 通过。
2. 归档：把 delta 应用到 `openspec/specs/`，变更移入 `openspec/changes/archive/<date>-clean-up-stale-specs/`。
3. 归档后复核主规格：旧需求名不再出现、未启用预设类场景不再出现、契约版本号一致。
4. 回滚策略：本次只改 Markdown 规格文本，`git revert` 单个提交即可完全回退，不涉及数据或产物。
