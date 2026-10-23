## 1. 方法与模板

- [x] 1.1 在 `visual-creative-direction.md` 新增「载体来源决策：代码、外部素材与混合」：整体政策、候选层、逐场实例、判定顺序、硬边界与失败模式。
- [x] 1.2 更新 `production-workflow.md` 的「表达载体」与七段式，加入载体来源政策与逐场字段。
- [x] 1.3 更新 `creative-production.md` 的三案要求与核心体验设计，加入载体组合、证据体制与硬边界。
- [x] 1.4 更新 `article-media-and-sound.md` 的选择边界，保留导入、许可与溯源契约。
- [x] 1.5 更新 `scene-design-and-acceptance.md` 的逐场表与验收维度，加入「载体来源与理由」。
- [x] 1.6 更新 `SKILL.md`、README 与 `docs/PROJECT_PLAN.md` 的入口说明。

## 2. 示例与测试

- [x] 2.1 三个示例 `DESIGN.md` 的非重制方案记录加入「载体来源」小节与逐段来源表。
- [x] 2.2 扩展 `tests/test_doc_examples.py` 与 `tests/test_examples_strict.py` 的 token，覆盖两层字段与硬边界。
- [x] 2.3 确认未修改示例分镜、场景、音频、视频产物或媒体，未改写既有交付结论。

## 3. OpenSpec 与验证

- [x] 3.1 写入 proposal、design、tasks 与 `video-production-workflow` 增量规格。
- [x] 3.2 运行目标测试、`sync_docs.py --check`、`openspec validate --strict`、链接/锚点检查与 `git diff --check`。
- [x] 3.3 记录验证结果、既有问题与未验证范围到 `verification.md`。

## 4. 提交与归档

- [x] 4.1 检查暂存内容仅含本轮文档、OpenSpec、示例 DESIGN 与测试，排除媒体、缓存与凭据。
- [x] 4.2 提交实施结果，报告 commit 与验证结果。
- [x] 4.3 同步主规格，按 `2026-10-24-add-carrier-source-decision` 归档并提交。
