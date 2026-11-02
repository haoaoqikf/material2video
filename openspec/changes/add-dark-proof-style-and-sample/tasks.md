## 1. 研究与设计落点

- [ ] 1.1 把 `reference-analysis.md` 的摘要、不借清单、采用规则与八项指标写入 `styles/dark-proof/examples/sample/DESIGN.md` 的「参考拆解」区块；验证文件存在、包含八项指标表与至少 9 条采用规则。
- [ ] 1.2 写 `styles/dark-proof/style.json`、`tokens.json` 与 `GUIDE.md`：清单声明 `types:["general"]`、`frames:[1920×1080]`、不含 `requires.narration="none"`、不带字体与外部资产；验证 `uv run m2v styles --json` 返回 `dark-proof` 且字段完整。
- [ ] 1.3 在 `styles/dark-proof/components/` 实现舞台、巨型数字、点阵场、论证图表、计数器、双语标题、屏幕字幕、手绘描线与确定性工具；验证 `uv run pytest tests/common/test_styles.py -q` 与同帧两次录制字节一致。
- [ ] 1.4 写 `styles/dark-proof/examples/sample/project.json`、`storyboard.json` 与 `scenes/sample.tsx`：单幕、`targetSeconds: 58`、`durationFrames: 1740`、30 fps、无旁白、`style.id: "dark-proof"`、topic 输入每幕声明 `keywords`、屏幕字幕在安全区；验证 `uv run m2v validate --project styles/dark-proof/examples/sample`。
- [ ] 1.5 按设计文档的八拍表实现画面、数字与中文/英文文案：3/1000、均值摆动 33 点、n=3/10/100/1000、唯一硬切 20.0 秒、回归、盲人摸象、SE=σ/√n、四倍关系、回扣；验证 `uv run m2v lookdev --project styles/dark-proof/examples/sample --sheet 6 13 20 24 28 35 43 51 58` 的代表帧与设计一致，并用 `--motion 19.5 20.5` 核对唯一硬切。

## 2. 示例素材与声音

- [ ] 2.1 写 `styles/dark-proof/examples/sample/assets/synthesize.py`、`recipe.json` 与 `LICENSE.md`：原创确定性环境床与稀疏事件音，24 kHz PCM16 单声道、CC0-1.0、摘要固定；验证 `uv run python .../assets/synthesize.py` 后 `recipe.json` 摘要、时长、采样率一致，重复生成字节相同。
- [ ] 2.2 写 `SOUND.md`，登记“角色→assetId→参数→作用”，并让 `storyboard.json` 的事件音引用 `eventId`；`soundtrack.music` 显式写 `gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`；验证 `outputs/events.json` 的事件帧与音效起点一致。
- [ ] 2.3 写 `README.md`、`SOURCES.md`、`DESIGN.md` 与 `VERIFICATION.md`：说明选题、数学假设、无旁白、重建命令、已知限制与不入库产物；验证相对链接与命令可执行，观众文案不含仓库路径。
- [ ] 2.4 写 `HOWTO.md`：提供一个可复现练习（例如把 n=3 改为 n=12，或移动 20.0 秒硬切），写明修改位置、预期变化、验证命令与恢复方式；验证按练习修改后 `validate` / `lookdev` 通过并能恢复原状。

## 3. 测试与验证

- [ ] 3.1 新增 `tests/works/examples/test_dark_proof_style.py`：注册、清单、类型/画幅拒绝、组件确定性、指纹剪枝、示例无旁白、字幕安全区、风格包不引用示例；验证 `uv run pytest tests/works/examples/test_dark_proof_style.py -q`。
- [ ] 3.2 更新 `tests/helpers/examples.py` 的 `STYLE_EXAMPLES`，加入 `dark-proof: sample`；验证依赖该名单的字体覆盖、示例卫生与六示例校验全部通过。
- [ ] 3.3 按参考风格契约产出 `styles/dark-proof/examples/sample/outputs/style-reference.md`：L1/L2/L3、不借清单、八项指标参考/目标/实际/差值、三张并排基准、2 秒动效样片；验证实际列回填且文件齐全。
- [ ] 3.4 由独立子代理冷审并排图与 2 秒样片，只投喂图像与中性问题；验证 `outputs/visual-notes.md` 含基准链接、显示尺寸、隔离条件、结论与差异项，降级时显著披露。
- [ ] 3.5 渲染代表帧与完整候选，检查手机横屏可读性、唯一硬切、字幕安全区与数学显示；验证 `uv run m2v qa --project ...` 通过，响度约 −14 LUFS / −1 dBTP，`outputs/` 不入库。

## 4. 文档与清单同步

- [ ] 4.1 更新 `styles/README.md`、`README.md`、`docs/PROJECT_PLAN.md`、[风格接入契约](../../../.agents/skills/material2video/references/style-pack.md) 与 `AGENTS.md`：五个风格/五个示例改为六个，登记 `dark-proof` 与 `sample`，并同步“不登记 assets”的包名单；验证所有相对链接与数字一致。
- [ ] 4.2 确认 `style-registry`、`article-explainer`、`vibe-fable-style` 的规格增量与主规格同步，归档时把“五个”更新为“六个”；验证 `openspec validate add-dark-proof-style-and-sample --strict`。
- [ ] 4.3 检查 Git 暂存范围：只含风格包源码、示例源码与文档，排除 `outputs/`、生成媒体、字体二进制与参考片；验证 `git status` 与 `git ls-files styles`。
- [ ] 4.4 运行 `uv run pytest`、`uv run pytest -m "not slow"` 与 `uv run pytest -m slow`（按改动影响选择层级），并检查 README、styles/README、skill 参考文档与 AGENTS 的相对链接和六示例数字一致；验证现有五套风格与他们的示例不回归。
- [ ] 4.5 独立子代理只读审查：核对包边界、无参考媒体、六示例名单、字幕安全区与数学口径；修复后复查。
- [ ] 4.6 提交实施并自动归档：同步 `openspec/specs/` 主规格、把变更移入 `openspec/changes/archive/` 后提交归档结果；交付报告 commit 标识与验证结果。
