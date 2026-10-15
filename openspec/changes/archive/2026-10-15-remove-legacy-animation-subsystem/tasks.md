## 1. 搬迁共享件

- [x] 1.1 新建 `src/m2v/core/report.py`，从 `types/article/storyboard.py` 原样搬入 `Issue` 与 `Report`
- [x] 1.2 改 `types/general/adapter.py` 与 `types/stock/brief.py` 的导入指向 `core/report.py`
- [x] 1.3 从 `engine/remotion.py` 删除 `PageContract` 导入与 `CompositionMetadata.contract` 属性，并把 `metadata` / `render_frames` / `render_session` 的 `composition_id` 改为必填
- [x] 1.4 新建 `src/m2v/core/workspace.py`，从 `types/article/paths.py` 搬入 `CONTENT_ROOT_ENV`、`PROJECT_MARKER`、`bundle_repo_root`、`content_root`
- [x] 1.5 改 `types/relocation.py` 的导入；让 `cli.py` 复用 `CONTENT_ROOT_ENV` 常量替换硬编码 `"M2V_CONTENT_ROOT"`
- [x] 1.6 改 `types/article/adapter.py::prepare_narration` 直接调用 `engine.tts.scene_audio(..., contract_version=3)`，去掉对 `article/prepare.py` 的依赖
- [x] 1.7 更新 `tests/test_render_session.py` 以显式传入 `composition_id`
- [x] 1.8 跑 `uv run pytest` 确认搬迁后全绿

## 2. 删除 Python 旧子系统

- [x] 2.1 删除 `types/article/` 下 18 个模块：`cli.py`、`inspect.py`、`keynote.py`、`production.py`、`render.py`、`animation_review.py`、`benchmark.py`、`storyboard_v4.py`、`visual_narrative.py`、`motion.py`、`media.py`、`workflow_cli.py`、`prepare.py`、`state_tracks_v4.py`、`timeline_v4.py`、`bespoke_review.py`、`rhythm_review.py`、`motion_plan.py`
- [x] 2.2 删除 `types/article/storyboard.py` 与 `types/article/paths.py`
- [x] 2.3 删除 `core/catalog.py`、`core/determinism.py`、`core/diversity.py`、`engine/beats.py`、`engine/browser.py`（保留 `types/financial/commands.py`：规格与 `test_financial_video.py` 覆盖的独立金融入口）
- [x] 2.4 删除 `engine/subtitles.py` 的 `segment_windows` 与 `srt`（保留 `cues_from_words`）
- [x] 2.5 删除 `engine/contract_page.py` 的 `CONTRACT_VERSION`
- [x] 2.6 删除 `engine/remotion.py` 的 `COMPOSITION_ID` 默认值，改为必填参数
- [x] 2.7 删除 `types/migration.py` 的 `article-v4` 分支，并同步 `cli.py` 的 `--from` choices
- [x] 2.8 删除 `.agents/skills/material2video/scripts/benchmark_render.py` 与 `sync_catalog.py`
- [x] 2.9 检查 `types/article/` 是否只剩 `adapter.py`、`explainer*.py`、`article_text.py` 等活跃模块，清理空目录
- [x] 2.10 跑 AST 可达性脚本，确认除设计 D8/D9 保留的独立金融入口 `m2v.types.financial.commands` 外，全部剩余 Python 模块均从 `m2v.cli` 可达（66 个模块中 65 个可达）
- [x] 2.11 连带删除随 `embeddedCodeModules` 消失的参数链：`remotion.bundle` / `prepare_composition_entry` / `scene_manifest.generate` 的 `additional_modules`、`remotion._with_additional_modules()`、清单里的 `additionalSourceDirs` 与 `gen-active-scenes.mjs` 的读取

## 3. 删除 Web 旧子系统

- [x] 3.1 删除 `src/compositions/` 的 `M2VComposition.tsx`、`M2VCompositionV4.tsx`、`CodeSceneHost.tsx`、`LayoutGeometryPreflight.tsx`
- [x] 3.2 删除 `src/primitives/`（`SceneTree.tsx`、`iconSet.tsx`）
- [x] 3.3 删除 `src/runtime/` 的 11 个 v3/v4 模块，保留 `offline-guard.ts`
- [x] 3.4 删除 `src/schema/` 的 `storyboard.ts`、`storyboardV4.ts`、`primitiveTypes.ts`、`articleText.ts`（含其测试）
- [x] 3.5 删除 `src/registry/`
- [x] 3.6 重写 `src/Root.tsx`，只注册 5 个 composition
- [x] 3.7 重写 `src/contract/main.tsx`，只保留 explainer 契约页
- [x] 3.8 精简 `src/contract/bridge.ts`，只保留 `M2VContractV5` 与 `settleOnFrame`
- [x] 3.9 精简 `src/styles/index.css` 的 `@import`，删除 `theme.css`、`keynote.css`、`primitives.css`、`declarative.css`、`scene-tree.css`
- [x] 3.10 清理 `base.css` 中只服务场景树的 `[data-m2v-stage]` / `[data-m2v-scene]` / `[data-m2v-controls]` 规则（先 grep 确认无其他消费者）
- [x] 3.11 把 `tokens.css` 的三层令牌合并成单层 `@theme static`，删掉没有任何代码挂载的 `[data-m2v-preset]` / `[data-m2v-theme]` / `[data-m2v-style-pack]` 作用域层
- [x] 3.12 把 `ArticleExplainer` 场景容器的 `z-index: 1` 从已删的 `declarative.css` 移进组件自身的内联样式，字幕层的 `z-index: 2` 因此不再依赖样式表
- [x] 3.13 从 `web/package.json` 移除 `zod` 并重新生成 `pnpm-lock.yaml`
- [x] 3.14 跑 `pnpm -C web run typecheck` 与 `pnpm -C web build`

## 4. 改写测试与夹具

- [x] 4.1 删除只覆盖被删模块的用例文件（42 个，按设计 D8 复核后的实际集合执行）
- [x] 4.2 删除 `tests/fixtures/` 的 `beat-vectors.json`、`storyboard-v4-vectors.json`、`storyboard-v4-timeline-vectors.json`
- [x] 4.3 改写 `tests/conftest.py`，去掉 `production`、`paths` 夹具，改用 `core/workspace.py`
- [x] 4.4 把 `test_figure_contrast.py` 收敛为只读 `tokens.css`，并补一条「字号/描边/墨色阶仍在令牌块里」的完整性断言
- [x] 4.5 改写代码场景族用例（`test_code_scenes.py`、`test_code_gate.py`、`test_code_composition.py`、`test_scene_manifest.py`），夹具换成 `general-plan.json` 形态，移除 `open_animated_page`
- [x] 4.6 改写文章族用例（`test_project_cli.py`、`test_general_video.py`），只保留 v5 断言
- [x] 4.7 改写其余混合用例（`test_render_performance.py`、`test_render_session.py`），删除对已删模块的导入与断言
- [x] 4.8 跑 `uv run pytest`（含 slow）与 `pnpm -C web test` 全绿

## 5. 清理示例与忽略规则

- [x] 5.1 删除三个示例的 `legacy-test-storyboard.json`、`scenes/`、`motion-design.md`、`review.md`、`production.template.json`
- [x] 5.2 删除 `darts-trial-and-error/production-workflow.md`、`buffer-smoothing/script-design.md`、`keynote-baseline/financial-plan.example.json`
- [x] 5.3 删除 `buffer-smoothing/assets/drop.wav`，保留 `bed.wav`、`generate.py`、`LICENSE.md`
- [x] 5.4 同步 `.gitignore` 中 `drop.wav` 的白名单行，并改掉 `generate.py`、`LICENSE.md`、三份 `README.md` 里对它的引用
- [x] 5.5 确认三个示例的 `storyboard.json` 与 `assets/feedback.png` 仍可 `m2v validate`

## 6. 收敛文档

- [x] 6.1 删除 `references/design-constitution.md`、`keynote-design-system.md`、`visual-spec.md`、`primitive-catalog.md`
- [x] 6.2 新建 `references/design-tokens.md`（123 行）
- [x] 6.3 精简 `references/render-contract.md` 到当前契约（431 → 367 行），删除动效运行时、场景树原语、语义节拍运行时与 Remotion 迁移回归基线四节，修掉两处死链
- [x] 6.4 精简 `references/media-contract.md`（280 → 263 行），删掉 130～170 字 / 35～45 秒残留与 v4 媒体清单整节，音床示例改用仍存在的 `bed.wav`
- [x] 6.5 改写 `references/code-scenes.md` 为 `general-plan.json` 的幕级声明方式，并标注 `world`/`stage`/`objectStates`/`beats`/`motion` 当前无内容、`probe()` 当前没有消费者
- [x] 6.6 更新 `references/paths-and-outputs.md`、`article-to-storyboard.md`、`visual-review-rubric.md` 中旧动画模块与过期输出/溯源结构的表述
- [x] 6.7 消除 README / SKILL / PROJECT_PLAN / web README 的定位句、排除项与路径说明重复
- [x] 6.8 修正 `docs/PROJECT_PLAN.md` 把已交付 general 能力写成待办的事实错误
- [x] 6.9 更新 README 与 SKILL 中 `migrate --from` 的取值说明
- [x] 6.10 修正复核中发现的其余文档事实错误：`voiced.mp4` / `silent.mp4` / `voiced.srt`、不存在的 `--engine`、代码模块标识字符集、`soundtrack.effects` 与无准备记录时的渲染行为
- [x] 6.11 跑 `python .agents/skills/material2video/scripts/sync_docs.py --check` 并检查相对链接（20 份文档全部可达）

## 7. 清理归档一次性产物

- [x] 7.1 删除 22 份归档中间产物（README / review / validation / verification / implementation-review / baseline / evaluation）
- [x] 7.2 确认每项归档变更仍保留 `proposal.md`、`tasks.md`、`specs/**` 与 `.openspec.yaml`（`2026-09-18-font-subsetting` 与 `2026-10-10` 之后几项本来就没有 `design.md` / `.openspec.yaml`，属既有状态，未新建）

## 8. 验收与归档

- [x] 8.1 跑完 11 项验收清单（可达性、typecheck、build、vitest、pytest 两轮、`m2v types`、三个示例 validate、article 与 general 各一次 preview+render、sync_docs --check、关键词零命中、相对链接）
- [x] 8.2 检查 `git status`，排除缓存、依赖与生成媒体（`web/dist`、`web/.gen`、`web/.cache`、`videos/**`、`outputs/`、`node_modules` 均被忽略）
- [x] 8.3 提交实现改动与配套文档，报告 commit 标识与验证结果（`9cd6bba`）
- [x] 8.4 同步 `openspec/specs/` 主规格并把变更移入 `openspec/changes/archive/`
- [x] 8.5 提交归档结果

## 最终复核记录（2026-10-15）

- 结论：旧共享动画链路及无消费者的参数链已移除，当前五类 composition 与文章 v5 契约保留；当前帧诊断接口已补齐，随机寻帧断言通过。未发现本变更范围内的交付阻塞项。
- 验证：本轮两次完整 pytest 均为 432 passed、5 skipped；Web typecheck、build、87 项 Vitest、三个固定示例 validate、类型清单、文档同步、20 份当前文档相对链接与 JSON 示例检查通过。15 份主规格通过严格校验。
- 端到端：general/code-smoke 与 article-narrative/v5-qa-keynote-baseline 均完成 prepare、完整 preview 和正式 render，并通过实际媒体验收；通用代码场景抽帧检查通过。作品与生成媒体未入库。
- 性能：通用正式导出 150 帧、总耗时 13.625 秒；文章正式导出 874 帧、总耗时 67.672 秒。删除降低维护面，未引入额外算法或逐帧工作；未据此声称对比旧版本的性能提升。
- 剩余限制：本机符号链接权限与未安装可选字体依赖导致 5 项跳过；Vite 有现存包体积提醒。一个旧 buffer-smoothing 作品准备时出现媒体覆盖权限错误，采用 keynote-baseline 完成文章端到端验证，未修改该作品权限。
- 质量评分：95/100；扣分来自上述环境覆盖限制与包体积提醒。逻辑、异常路径、兼容性、文档和性能影响已复核。
- 规格同步：更新 4 份能力，退役以下 11 份旧能力规格及其 Purpose，保留历史变更用于追溯。需要恢复退役规格时执行：

```powershell
git checkout 9cd6bba -- openspec/specs/article-to-storyboard/spec.md openspec/specs/bespoke-explanatory-animation/spec.md openspec/specs/cinematic-directing/spec.md openspec/specs/declarative-video-scenes/spec.md openspec/specs/frame-driven-motion/spec.md openspec/specs/react-component-registry/spec.md openspec/specs/scene-primitive-tree/spec.md openspec/specs/science-video-production/spec.md openspec/specs/semantic-motion-timeline/spec.md openspec/specs/storyboard-aesthetic-review/spec.md openspec/specs/visual-direction-pipeline/spec.md
```
