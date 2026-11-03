## Why

`dark-proof` 的规范示例仍是《样本》（58 秒、3/1000、盲人摸象）。而 `videos/general/compound-connect` 的《接》是同一风格、同一参考片结构下更完整的一版：60 秒、10 场、10 种说明方式、唯一硬切 41.0 秒、11 条双语屏幕字幕、30 个事件、112 BPM 原创配乐，实际使用 1.2.0 的舞台、双语标题、屏幕字幕、论证图表、爆散与扩散环。用户要求把它提升为正式示例并删除旧示例；继续维护两条同风格、同参考片来源的完整作品只会让示例名单、素材恢复与验收口径分叉。

## What Changes

- **BREAKING** 把 `videos/general/compound-connect` 的源材料迁入 `styles/dark-proof/examples/compound-connect/`，并从 `videos/general/` 移除；生成产物在新路径重建，仍不入库。
- 删除 `styles/dark-proof/examples/sample/`，清理 README、AGENTS、styles README、测试与规格中的全部引用。
- 补齐示例合同：`README.md`、`HOWTO.md`、`SOUND.md`、`DESIGN.md` 的参考拆解与机器合同、`SOURCES.md` 边界、`VERIFICATION.md`；按参考风格契约补 `outputs/style-reference.md`、并排基准、2 秒样片与独立冷审记录。
- 更新固定示例名单：`tests/helpers/examples.py`、`tests/works/examples/test_dark_proof_style.py`、`AGENTS.md`、`README.md`、`styles/README.md`、`vibe-fable-style` 与 `video-frame-rate` 的示例场景。
- 规格按《接》的实际内容改写 `dark-proof-style` 的示例要求：60 秒/1800 帧、10 场、11 条屏幕字幕、8 个检查点、1230 帧唯一硬切；删除《样本》专属的 58 秒/1740 帧、13 条字幕、10 个检查点、盲人摸象/大象几何与 3/1000 数学口径，改为《接》的复利、42 折、棋盘与 100 节点网络口径。
- 风格包本体（组件、tokens、GUIDE、1.2.0 版本与指纹）不变；示例改动不影响风格指纹。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `dark-proof-style`: 规范示例由《样本》改为《接/compound-connect》；同步改写示例的时长、字幕、检查点、硬切、题材数学、光效与节奏要求，并删除大象几何等《样本》专属要求。
- `article-explainer`: 「随附风格示例集合」中的 `dark-proof/sample` 改为 `dark-proof/compound-connect`。
- `vibe-fable-style`: 「风格示例必须可校验并与包分离」场景中的 `dark-proof/sample` 引用改为新示例。
- `video-frame-rate`: 「固定示例」场景中的 `dark-proof/sample` 引用改为新示例。

## Impact

- 目录与文档：`styles/dark-proof/examples/{sample,compound-connect}/`、`videos/general/compound-connect/`、`README.md`、`AGENTS.md`、`styles/README.md` 及示例内的 DESIGN/SOURCES/VERIFICATION/README/HOWTO/SOUND。
- 测试：`tests/helpers/examples.py`、`tests/works/examples/test_dark_proof_style.py`，以及依赖示例名单的文档、文案与媒体卫生测试。
- 规格：`openspec/specs/dark-proof-style`、`article-explainer`、`vibe-fable-style`、`video-frame-rate`。
- 运行时代码不变；示例移动到新路径后必须重新执行 `validate`、`prepare`、`lookdev`、`render`、`qa`，旧《样本》的候选、QA 与并排证据随目录删除，不再作为新示例的依据。
