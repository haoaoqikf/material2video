## Why

`openspec/specs/` 是「已实现行为」的权威描述，但其中一批需求仍在描述**已经删除**的机制：第三方组件分类接入、vendored 弹簧求解器、旧整页组件几何、`figures.js` 动效路径、分镜迁移程序，以及早已被 v3 契约取代的字段与版本号。规格与实现不一致时，它就不再能作为验收依据——读者会照着已删除的机制实现，或者以为某条判据还有机检守着。

本次变更不改产品行为，只把主规格改回描述**当前真实行为**：把已废止机制的需求标记移除，把版本号、字段归属、判据口径与措辞对齐到实现。同批的代码与文档清理见 `docs/PROJECT_PLAN.md`／README 的同步修正。

## What Changes

- **移除整条已废止能力** `deterministic-third-party-adapters`（7 条需求）：第三方组件分类表、`FrameSyncedCssAnimation` 帧同步包装、代表组件适配闭环都随整页组件路径删除；`web/src/third-party/` 不存在且被架构禁止。仍活的白名单与确定性适配规则由 `code-driven-scenes` 覆盖，删除本能力不丢活需求。
- **修正版本号**：`remotion-renderer` 的「版本 2 渲染契约」→ 版本 3（`CONTRACT_VERSION = 3`、`bridge.ts` `version: 3`）；`frame-driven-motion` 里「通过版本 2 渲染契约逐帧求值」同步。
- **移除已删除的运行机制需求**：`frame-driven-motion` 的「弹簧曲线由物理参数给定」「外部动效依赖随仓库分发且可追溯」（全仓库 `spring/阻尼/过冲/damping` 零命中）；`keynote-design-system` 的环形停位数、载荷不比问题小、临场焦点类名迁移、动效语汇上限（引用已删的 `figures.js`）、`IDLE_TOKENS` 账本、幕级 `layout` 字段（v3 无此字段，`data-layout="lower"` 不可达）。
- **移除没有实现的判据**：`frame-driven-motion` 的「入场轨迹可量测且不退化」把「过冲不超过全程的 10%」列为位移判据并配了「停不稳」「过冲过大」两个场景，但现行机检（`a2v/motion.py` 的 M0–M4）没有任何过冲或残余位移判据（全仓库对「过冲」「overshoot」「收敛时刻」零命中，`Entrance` 无相应字段）；曲线是单调的三次缓出，过冲不是可达的失败模式。该条改写为「入场轨迹可量测且判据可实现」，其余判据逐字保留。
- **移除不可达分支**：`frame-driven-motion` 的「动效是帧的纯函数」去掉「秒为单位的弹簧时间输入」前提（运行时不再有秒↔帧换算）；`declarative-video-scenes` 的「共享页面生成画面」去掉「未启用预设时不取档」场景；`keynote-design-system` 的「图形基元与状态语汇」去掉「未启用预设的页面」前提与同名场景，「重点面上的墨色由设计层给出」去掉「只在未启用预设的样式表里定义的令牌」分支，「动效不得在帧边界上瞬跳」把「交给弹簧入场」改为受控配方。
- **移除已删除的能力需求**：`article-workspace` 的「迁移保护」（无任何迁移代码；`storyboard-v3-contract` 已规定不提供迁移命令）。
- **修正字段与口径**：`article-workspace` 生成入口目录位置（在仓库 `web/.gen/` 下，非「解析自工作区根」）；`font-coverage` 去掉 `narration` 例（v3 显式拒绝字符串 `narration`）；`font-subsetting` 判据统一到「画面实际注册的字体资产」；`semantic-motion-timeline` 明确 `before/after/relation` 可选；`visual-direction-pipeline` 修正情绪/风格包归属 `directingBrief`；`article-to-storyboard` 去掉 `narration` 与 `data.figure.kind` 场景；`cinematic-directing` 去掉不存在的「未声明风格包」分支；`render-provenance` 别名 `/__a2v__/` → `/__a2v_web__/`。
- **修正措辞与前提**：`declarative-video-scenes`、`react-component-registry` 的 Purpose 去掉旧架构用词（能力标识与文件夹名保留）；`keynote-design-system` 中「未启用预设的既有作品逐字节不变」的**作品前提**在 v3 强制 `visual.preset` 后已不存在，改为描述仍成立的**作用域性质**。
- **清理目录残留**：删除空的 `openspec/specs/storyboard-scene-tree-migration/`（无 `spec.md`、未跟踪、`openspec list --specs` 不列出）。

## Capabilities

### New Capabilities

无。本次变更只修正既有规格，不引入新能力。

### Modified Capabilities

- `deterministic-third-party-adapters`: 整能力移除（7 条需求全部描述已废止的第三方组件接入机制）。
- `remotion-renderer`: 「版本 2 渲染契约」改为版本 3。
- `frame-driven-motion`: 移除弹簧曲线与外部动效依赖两条；移除「入场轨迹可量测且不退化」里没有实现的过冲与残余位移判据；「动效是帧的纯函数」去掉秒↔帧换算前提；动效量测条目的契约版本号与旧措辞修正。
- `keynote-design-system`: 移除 7 条已失效需求（含「图形基元与状态语汇」的未启用预设前提）；修正预设作用域类需求的表述前提；修正基元清单棘轮类需求；「重点面上的墨色由设计层给出」与「动效不得在帧边界上瞬跳」去掉不可达分支与弹簧措辞。
- `article-workspace`: 移除「迁移保护」；修正生成入口目录位置。
- `font-coverage`: 去掉把 `narration` 当作「当前不渲染字段」的例子。
- `font-subsetting`: 缺字机检的判据来源统一到画面实际注册的字体资产。
- `semantic-motion-timeline`: 「beat 必须描述前后状态」明确前后状态字段为可选。
- `visual-direction-pipeline`: 修正视频级视觉策略与导演简报的字段归属。
- `article-to-storyboard`: 两个场景去掉已删除字段；Purpose 与措辞去旧概念。
- `cinematic-directing`: 去掉不存在「未声明风格包」分支的末句。
- `render-provenance`: 共享资产别名与「网页」口径改为现行构建输入口径。
- `declarative-video-scenes`: Purpose 去旧架构措辞；「共享页面生成画面」去掉不可达的「未启用预设时不取档」场景，改写为「共享画面路径与预设必填」（需求其余部分逐字保留）。
- `react-component-registry`: Purpose 去旧架构措辞（需求本身保留）。

## Impact

- **规格**：`openspec/specs/` 下 14 个能力目录、1 个空目录删除；归档后主规格与实现一致。
- **行为**：无变化。规格文本改动均为对齐已实现行为，不改变校验器、渲染路径或验收口径。
- **代码**：同批清理删除了 `a2v/constitution.py`、若干零引用符号与 Web 侧死代码；其中 `a2v/source_policy.py` 的第三方分类表挂载分支（永远读不到 `web/src/third-party/catalog.json`）随之删除——当前输入下 `scan()` 输出不变。这些改动不引入新能力，因此**不在本变更的规格 delta 内**，规格只反映删除后的行为。
- **文档**：README、`docs/PROJECT_PLAN.md`、`.agents/skills/article2video/references/**` 同步修正，`references/third-party-components.md` 与 `references/figure-catalog.md` 两份墓碑文档删除。
- **依赖**：无新增或移除。
