## 1. 示例名单与目录

- [x] 1.1 把 `videos/general/compound-connect/` 整体移入 `styles/dark-proof/examples/compound-connect/`，保留当前 `outputs/` 作为 v4 基线；删除 `videos/general/compound-connect/` 旧路径。验证：两处路径不存在重叠，`git status --short` 只出现预期的新增样式示例源码。
- [x] 1.2 删除 `styles/dark-proof/examples/sample/`，包括被跟踪的源码与忽略的 `outputs/`、`assets/media/`；验证：`test -e` 返回不存在，`git ls-files styles/dark-proof/examples/sample` 为空，未使用 `git add -f`。
- [x] 1.3 把 `tests/helpers/examples.py` 的 `dark-proof` slug 改为 `compound-connect`；同步改写 `tests/works/examples/test_dark_proof_style.py` 的示例路径、1800 帧、11 条双语字幕、无旁白、`subtitleSafeArea`、声音配方 11 个资产与场景无 `refs/` 断言。验证：`uv run pytest tests/works/examples/test_dark_proof_style.py` 通过。
- [x] 1.4 更新 `AGENTS.md`、`README.md`、`styles/README.md` 的示例名单、标题、时长与 validate 命令；验证：`grep -rn "dark-proof/sample\|《样本》\|盲人摸象"` 不再命中当前示例与操作文档（历史归档除外），文档相对链接可打开。

## 2. 示例材料与文档

- [x] 2.1 确认新示例 `project.json` 仍为 general、1920×1080、30 fps、`style.id: "dark-proof"`，分镜 v8、1800 帧、无旁白、11 条双语屏幕字幕、8 个检查点、1230 帧唯一硬切。验证：`uv run m2v validate --project styles/dark-proof/examples/compound-connect` 通过。
- [x] 2.2 补齐 `README.md`、`HOWTO.md`、`SOUND.md`；在 `DESIGN.md` 增加参考拆解、借鉴分层、不借清单与 `visual-creative-direction.md` 链接；更新 `SOURCES.md` 的示例路径与边界；更新 `VERIFICATION.md` 的命令、路径、证据与已知限制。验证：`uv run pytest tests/common/test_doc_examples.py tests/types/general/test_storyboard_copy.py` 通过。
- [x] 2.3 确认 `assets/synthesize.py`、`recipe.json`、`fetch.py` 在新路径可恢复 11 个声音资产，摘要、采样率、声道与时长一致。验证：`uv run python styles/dark-proof/examples/compound-connect/assets/fetch.py`，随后 `uv run m2v prepare --project styles/dark-proof/examples/compound-connect` 通过。

## 3. 示例内容与风格证据

- [x] 3.1 按新规格复跑无字幕静读与微拍检查；对 S2/S3 共用计数尺、S4 回环未闭合、S6 曲线主导、S7 的 42 张纸、S8 口径小字、S9 谷粒线性、S10 的 4,950 来源逐项判断。验证：违反「示例内容与数学口径」「微拍密度」场景的项做局部修补并重渲染；仅审美偏好的项写入 `VERIFICATION.md` 已知限制。
- [x] 3.2 按参考风格契约产出 `outputs/style-reference.md`、三张并排基准、2 秒样片与独立子代理冷审记录；参考帧只留在 `refs/` 与评审证据目录。验证：材料齐全，八项指标均回填实际值与差值，冷审记录由隔离的子代理执行。
- [x] 3.3 重跑代表帧、硬切与字幕安全区检查；确认 1230 帧处只有单环/局部光，无粒子或全屏闪白。验证：`uv run m2v lookdev --project styles/dark-proof/examples/compound-connect --sheet 2 6.2 14 20 25.8 36 41 47 52 59` 与 40.9/41.0/41.1 秒边界逐张核对。

## 4. 验证与交付

- [x] 4.1 重跑 `uv run m2v render` 与 `uv run m2v qa`，记录 1800 帧、1920×1080、30 fps、时长、响度、字幕对比度、冻结帧与 claims 结果；旧 `delivery.json`/`provenance` 只作基线。验证：`qa.json` 为 pass，交付记录指向新路径。
- [x] 4.2 运行 `uv run pytest`、`uv run pytest -m "not slow"`、文档/示例卫生测试与 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check`。验证：无失败；示例媒体与 outputs 未被跟踪。
- [x] 4.3 检查暂存范围只含本次示例替换、文档、测试与规格；提交。验证：`git status --short` 无生成媒体、无旧示例残留，commit 包含源材料与文档。
- [x] 4.4 归档前直接修改 `openspec/specs/dark-proof-style/spec.md` 的 Purpose，把《样本》改为《接》；同步四份规格，运行 `openspec archive promote-compound-connect-dark-proof-example` 并提交归档结果。验证：`openspec validate --specs --strict` 通过，主规格不再出现 `dark-proof/sample`。
