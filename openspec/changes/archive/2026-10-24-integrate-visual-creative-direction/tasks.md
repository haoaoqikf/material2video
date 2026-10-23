## 1. 方法与文档

- [x] 1.1 新增 `visual-creative-direction.md`：适用范围与边界、流程衔接、七步设计、文字预算、反平庸清单、七段式模板、十项自检、例外留痕、判断演练与人生五选择示例。
- [x] 1.2 更新 `production-workflow.md` 的七段式章节、四阶段表与三类记录，保持不新增阶段名。
- [x] 1.3 更新 `creative-production.md` 的核心体验、画面文字预算、粗预演与反平庸核对。
- [x] 1.4 更新 `article-to-storyboard.md` 的制作顺序、视觉创意七段式、关键画面与固定示例说明。
- [x] 1.5 更新 `scene-design-and-acceptance.md` 的逐场表、可见变化/镜头行为/母题状态与文字预算。
- [x] 1.6 更新 `visual-review-rubric.md` 的核心母题区分、视觉创意方案复核、反目标、静音边界与判断演练。
- [x] 1.7 更新 `director-review-and-edit.md` 的设计兑现观察、模板与判断演练。

## 2. 导航与示例

- [x] 2.1 更新 `src/m2v/types/catalog.json` 的 `general.skillGuide`，运行 `sync_docs.py`。
- [x] 2.2 更新 README 能力说明与文档导航、`docs/PROJECT_PLAN.md` 的设计指导段落。
- [x] 2.3 三个固定示例 `DESIGN.md` 补写「视觉创意方案（2026-10-24，非重制记录）」与十项自检。
- [x] 2.4 确认未修改示例分镜、场景、音频、视频产物或媒体，未改写既有交付结论。

## 3. OpenSpec 与测试

- [x] 3.1 写入 proposal、design、tasks 与 `video-production-workflow` 增量规格。
- [x] 3.2 在 `tests/test_doc_examples.py` 增加新文档 token、链接与示例段落断言；扩展逐场与示例测试 token。
- [x] 3.3 运行相关测试、`sync_docs.py --check`、`openspec validate --strict`、链接/锚点检查与 `git diff --check`。
- [x] 3.4 记录验证结果、既有漂移与未验证范围到 `verification.md`。

## 4. 提交与归档

- [x] 4.1 检查暂存内容仅含本轮文档、OpenSpec、示例 DESIGN 与测试，排除媒体、缓存与凭据。
- [x] 4.2 提交实施结果，报告 commit 与验证结果。
- [x] 4.3 同步 `openspec/specs/video-production-workflow/spec.md` 主规格，按 `2026-10-24-integrate-visual-creative-direction` 归档并提交。
