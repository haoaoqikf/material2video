## Context

`dark-proof` 的示例是 `styles/dark-proof/examples/sample/`，由《样本》58 秒版本构成；《接》位于 `videos/general/compound-connect/`，是同一风格、同一参考片结构下的 60 秒 v4 版本。风格包指纹明确跳过 `examples/` 子树（`tests/works/examples/test_dark_proof_style.py::test_example_changes_do_not_touch_package_fingerprint`），因此替换示例不需要改风格包版本。示例名单由 `tests/helpers/examples.py` 单点维护，但 `AGENTS.md`、`README.md`、`styles/README.md`、四份规格和暗场测试各自还有路径引用，必须一起改，否则文档测试与示例卫生测试会漂移。

## Goals / Non-Goals

**Goals:**

- 把《接》的源材料完整迁入 `styles/dark-proof/examples/compound-connect/`，删除《样本》目录及其引用。
- 让新示例满足 `dark-proof` 规格的示例合同：60 秒/1800 帧、10 场、11 条屏幕字幕、8 个检查点、1230 帧唯一硬切、112 BPM 原创配乐、可恢复声音、参考风格证据与独立冷审。
- 让规格、文档、测试与固定示例名单只描述《接》，不再描述大象、3/1000 或 58 秒版本。
- 保持风格包组件、tokens、GUIDE、1.2.0 版本与指纹不变；示例改动只影响示例自身准备。

**Non-Goals:**

- 不重新设计《接》的十场结构、镜头、文案或数学口径；只有当前候选不满足示例合同的场景才做最小修补。
- 不新增风格组件、不调整 tokens、不升级风格版本。
- 不把参考片画面、字幕、音轨或文案写入示例、风格包或渲染输入。
- 不保留《样本》的兼容路径或“旧示例别名”。

## Decisions

### 1. 移动而不是复制

`videos/` 是内容目录且不被版本控制跟踪，直接把 `videos/general/compound-connect/` 整体移到 `styles/dark-proof/examples/compound-connect/`，包括当前 `outputs/` 作为 v4 基线证据；移动后删除旧路径，避免两份同源作品并存。生成媒体仍不入库，移动后的 `outputs/` 只作为本地证据，提交前由 `.gitignore` 排除。

替代方案：复制源材料、保留原作品。优点是原作品可继续独立维护；缺点是同一题材、同一风格出现两份事实来源，示例名单与验收口径会分叉，且用户明确要求“提升”而非“另存”。

### 2. 新示例沿用 slug `compound-connect` 与标题《接》

不改成 `sample` 或 `connect`。`compound-connect` 与已有的 `count-ledger/examples/compound-interest` 区分清楚，也保留了作品 ID、分镜 scene id 与音效配方中的既有命名；标题《接》由 `storyboard.json` 的 `title` 与屏幕字幕承担，不写进目录名。

### 3. 规格按当前作品实际内容改写，不把《样本》要求原样套用

《样本》的 58 秒、1740 帧、13 条字幕、10 个检查点、600 帧硬切、3/1000、标准误、盲人摸象与大象几何都只属于《样本》。本变更把「示例作品」改名《接》，把时长/字幕/检查点/硬切改为 1800/11/8/1230，把数学口径改为 42 折、棋盘、100 节点网络与 21×，并删除大象要求。`dark-proof` 的组件、色板、运动、光效与 112 BPM 节奏要求保留，只去掉《样本》专属的计数。

替代方案：新增一条《接》要求、保留《样本》要求。缺点是规格会同时要求两个已不存在的示例，归档后主规格自相矛盾。

### 4. 当前 v4 候选是基线，但示例合同仍是门禁

《接》的 `VERIFICATION.md` 记录了第二轮无字幕静读的待完成项（S2/S3 共用底部计数尺、S4 回环未闭合、S6 曲线不够主导、S7 的 42 张纸未标清、S8 口径靠小字、S9 谷粒看起来线性、S10 的 4,950 无可见来源）。本变更不重做十场，但晋升后必须按新规格重跑验证：若这些项导致「示例内容与数学口径」「微拍密度」或「参考风格证据」场景失败，就在对应场次补可见来源或微事件；只做局部修补，不改场次结构。若只是审美偏好且不违反规格，则写入示例 `VERIFICATION.md` 的已知限制，不阻塞晋升。

替代方案：先完全重做《接》再晋升。成本高，且用户要求晋升的是当前这条视频；先晋升、再按规格门禁修补更符合“把这条视频变成正式例子”的意图。

### 5. 参考风格证据沿用同一参考片，但不复制素材

《接》的 `SOURCES.md` 已登记抖音 `7692873023291963558`《重复》作为结构参考。晋升后按[参考风格契约](../../../.agents/skills/material2video/references/reference-style.md)补 `outputs/style-reference.md`：从 `refs/` 采样参考帧、从成片同叙事位置取本片帧，做三张并排基准与 2 秒样片，由独立子代理冷审。参考帧、音轨、字幕只进入评审证据目录，不进入示例或风格包。

### 6. 测试只改名单与示例断言，不放宽卫生规则

`tests/helpers/examples.py` 把 `dark-proof` 的 slug 改为 `compound-connect`；`test_dark_proof_style.py` 保留组件集合、版本、tokens、指纹隔离与导入闸门断言，示例部分改为断言 1800 帧、11 条双语字幕、无旁白、场景使用 `subtitleSafeArea`、声音配方 11 个资产、场景不引用 `refs/`。示例媒体、输出与缓存仍由 `test_example_hygiene.py` 的通用规则覆盖，不为新示例增加例外。

### 7. 删除旧示例时同时删除其生成目录

`styles/dark-proof/examples/sample/` 的源码文件由 `git rm` 删除；`outputs/`、`assets/media/` 等忽略文件随目录一起删除，避免留下可被误认为当前示例的旧证据。历史记录保留在 OpenSpec 归档与 git 历史中，不复制到新示例。

## Risks / Trade-offs

- [当前 v4 有未关闭的静读问题] → 晋升验收按规格场景逐条复核；失败项做局部微事件或可见来源修补；不把“技术 QA 通过”当作理解通过。
- [规格中仍散落 `dark-proof/sample` 引用] → 全仓 `grep -rn "dark-proof/sample\|《样本》\|盲人摸象"` 清点，文档测试与示例名单测试兜底。
- [移动目录后旧绝对路径写入交付记录] → 移动后重新 `validate`/`prepare`/`render`/`qa`，旧 `delivery.json`、`provenance` 只作基线，不作为当前证书。
- [参考风格证据需要参考片本地文件] → 若 `refs/` 已清理，先按既有参考素材获取流程恢复；不用成片替代参考侧证据。
- [删除示例后测试仍读旧路径] → 先改 `tests/helpers/examples.py` 与 `test_dark_proof_style.py`，再删除目录，最后跑文档与示例卫生测试。

## Migration Plan

1. 改名单与测试，让 `compound-connect` 成为 `dark-proof` 的唯一示例。
2. 移入源材料，删除 `sample/`，更新 README、AGENTS、styles README。
3. 按新规格重跑 validate/prepare/lookdev/render/qa；补齐 README/HOWTO/SOUND/参考拆解/风格证据。
4. 跑文档、示例卫生、暗场测试与默认测试层；检查暂存范围并提交。
5. 提交后同步 `openspec/specs/`（含直接修改 `dark-proof-style` 的 Purpose），归档变更并提交归档结果。

回滚：若晋升验收失败且无法在局部修补内关闭，保留 `compound-connect` 源材料在 `videos/general/` 的备份（移动前复制到内容目录外的临时位置），恢复 `sample/` 目录与名单即可回到旧示例；不新增兼容代码。

## Open Questions

无。当前需要决定的范围已在规格与上述决策中固定；剩余问题（具体补哪几个微事件、哪张参考帧并排）属于实施中的证据选择，不改变规格或任务结构。
