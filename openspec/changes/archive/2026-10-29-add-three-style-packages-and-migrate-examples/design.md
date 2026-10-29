## Context

动机见 [proposal.md](proposal.md)。仓库已有完整的风格注册链路（`styles/<id>/style.json` → 清单校验 → 准备指纹 → general 场景显式导入），以及 `styles/examples/<style-id>/<slug>/` 这个保留目录。三个固定示例目前没有声明风格，可复用表现层与题材内容混在一起；顶层 `examples/` 又是另一套固定的示例集合。用户已确认最终 5 个风格、三个新 ID（`doc-archive`、`count-ledger`、`deep-journey`）、迁移现有作品并抽取组件、作品内容放 `styles/examples/<style-id>/<slug>/`。

## Goals / Non-Goals

**Goals:**

- 三个示例的可复用表现层成为正式风格包，其他 general 作品可通过 `style.id` 选择。
- 三个作品迁入对应风格示例目录，保留原有题材、分镜、素材、数学、旁白、声音与验证记录。
- 仓库只剩一套示例位置：`styles/examples/`；顶层 `examples/` 及其固定集合规则删除。
- 在规格与文档中明确三层边界：通用能力、风格能力、视频专属能力。
- 5 个风格包、5 个风格示例均可查询、校验、准备与回归。

**Non-Goals:**

- 不新增视频类型、CLI 命令、分镜字段、制作门、审核轮次或导出门禁。
- 不改变 `style.json` 结构、包发现规则、包指纹语义或 general 录制契约。
- 不把题材数据、媒体、数学、逐场编排、旁白或声音放进风格包。
- 不重写三个作品；保留其现有内容与验证证据，只抽取可复用表现层。
- 不保留顶层 `examples/` 的兼容入口、别名或迁移工具。

## Decisions

### 1. 三层能力边界

- **通用能力**：v8 代码场景、录制与缓存、素材与声音、字幕、风格注册、路径与工作区。与具体风格、题材无关，放在 `src/m2v/`、`tests/`、`.agents/skills/`。
- **风格能力**：色板语义、字号阶、版式分区、可复用组件、动效规则、GUIDE。放在 `styles/<id>/`，不携带题材内容。
- **视频专属能力**：题材数据、数学、逐场编排、文案、媒体、旁白、声音、示例脚本。放在 `styles/examples/<style-id>/<slug>/`，不进入包指纹。

只有被多个风格或作品需要且与题材无关的能力才上收 `src/`；风格包不反向依赖作品。

### 2. 作品放 `styles/examples/<style-id>/<slug>/`，不放进包内

`styles.py` 的包指纹覆盖包内所有文件。示例若放进 `styles/<id>/`，改示例会让所有选了该风格的作品准备失效。保留目录既满足“集中到风格之下”，又让示例改动只影响自己。风格发现继续跳过 `styles/examples/`。

### 3. 三个新包不登记 assets

`explainer_render.layout_check` 当前把所有风格包 `assets` 当字体检查，登记非字体纹理会失败。三个包统一使用宿主 `M2V Sans` / `M2V Inter`；`deep-journey` 的星场、光照、行星材质全部程序化。题材纹理仍留在示例 `assets/media/`，按素材 ID 使用。若未来确需包内纹理，先单独立项修共享能力。

### 4. 3D 组件走 `m2v/code-scene`，并限定录制模式

`deep-journey` 组件通过 `m2v/code-scene` 导入 `THREE`、`Canvas`、`useFrame`、`useThree`，不直接裸导入 `three` / `@react-three/fiber`；正式包测试的 import 白名单只允许 `react`、`m2v/`、`./`。`pure-time` 静态闸门禁用 `useFrame`，因此使用逐帧回调的 3D 组件只服务顺序录制示例；示例不得声明 `capture.mode: "pure-time"`。

### 5. 内容要求从通用规格迁入对应风格规格

`article-explainer` 中“三个固定示例”的详细内容契约属于视频专属，不是通用能力。用 `## REMOVED Requirements` + Reason/Migration 迁出，写入各新风格规格的「示例作品（视频专属，不属于包）」Requirement；`article-explainer` 只保留通用「随附风格示例集合」要求。`count-ledger` 的详细行为继续引用既有 `compound-interest-explainer-video`，不复制。

### 6. 示例的旁白与字幕契约按风格分别定义

不照抄 `vibe-fable` 的“无旁白 + `screenSubtitles`”要求：`doc-archive`、`count-ledger` 无旁白、文字画在场景内；`deep-journey` 保留旁白与共享字幕层。三者都不因成为风格示例而新增屏幕字幕要求。

### 7. 迁移顺序：先回接、再移动、最后删除

先在原 `examples/<slug>/` 位置把场景改为导入新风格组件，保持各自 `validate` / `prepare` 通过；再更新 `.gitignore` 与路径守卫；然后只 `git mv` tracked 文件到 `styles/examples/<style-id>/<slug>/`；最后删除顶层 `examples/`。不整目录移动：旧 `outputs/` 合计约 17.4G 且存在权限受限目录，旧产物本地清理。

### 8. 测试口径集中到 catalog

`tests/example_catalog.py` 继续作为唯一名单来源，改为 `styles/examples/<style-id>/<slug>/` 的 5 个示例；`test_examples_strict.py` 迁移为 `test_style_examples_strict.py`，保留通用不变量与三片内容契约。题材专属测试（复利、太阳系、科学里程碑）保留在各自测试文件，不改成风格测试。新增每包测试复用 `test_styles.py` / `test_vibe_night_style.py` / `test_vibe_fable_style.py` 的模板。

## Risks / Trade-offs

- [删除顶层 `examples/` 造成路径与回归断裂] → 先回接、再迁移、最后删除；分阶段跑 validate/prepare 与定向测试。
- [17.4G 旧产物与权限受限目录拖慢迁移] → 只 `git mv` tracked 文件，旧 `outputs/` 留在原处本地清理。
- [3D 组件与 `pure-time` 冲突] → 3D 示例走顺序录制；组件通过 `m2v/code-scene`，不裸导入。
- [包内误带题材内容] → 包只接收 props 与 tokens；测试检查包内无作品 slug、题材字面量、金额/天体常量。
- [新包登记 assets 触发字体检查失败] → 三个包不登记 assets；纹理留在示例。
- [OpenSpec MODIFIED/REMOVED 遗漏 Scenario 导致校验失败] → 完整复制原 Requirement 与全部 Scenario；REMOVED 写 Reason/Migration。
- [测试与文档路径漂移] → `example_catalog.py` 单一名单；统一搜索 `examples/` 残留；`sync_docs.py --check`。
- [迁移后代表帧与旧版有差异] → 记录有意差异；旧验证记录只作历史，不声称逐像素不变。

## Migration Plan

1. 创建 OpenSpec 变更并写 proposal/design/tasks/delta specs，通过 `openspec validate`。
2. 建三个风格包骨架（清单、tokens、GUIDE），确认 `m2v styles` 返回 5 个包。
3. 抽取组件并在原 `examples/<slug>/` 位置回接，保持三个作品 `validate` / `prepare` 通过。
4. 更新 `.gitignore`、路径守卫、catalog 与测试常量。
5. 只 `git mv` tracked 文件到 `styles/examples/<style-id>/<slug>/`；移动或重生成被忽略媒体；旧 `outputs/` 本地清理。
6. 删除顶层 `examples/`。
7. 迁移测试与文档，跑定向测试、全量非 slow、slow（3D/录制）。
8. 独立评审与代表帧对照，记录未验证项。
9. 提交；任务全完成后同步 `openspec/specs/` 并归档。

## Open Questions

- `vibe-night-style` 是否需要随“5 个包/5 个示例”补充措辞；当前未发现数量断言，实施时复核。
- `article-workspace` 的工作区根推导在代码中只有 `commands.py` 的路径守卫；实施时用测试确认 `styles/examples/<style-id>/<slug>/` 的产物归属，必要时补最小逻辑。
