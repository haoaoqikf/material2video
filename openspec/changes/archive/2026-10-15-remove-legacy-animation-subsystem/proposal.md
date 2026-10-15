## Why

仓库里仍留着一整套 v3/v4「旧共享动画」实现：文章类型的 v4 制作、体检与评审链，以及为它服务的场景树原语、语义节拍运行时、视觉导演管线、审美评审量表与发布会级设计语言的排版引擎。这些能力已不在任何产品入口上——统一 CLI 从 `m2v/cli.py` 出发只有 70/89 个 Python 模块可达，web 侧只剩契约页的旧分支和已无消费者的 `M2V` composition 在引用它们。它们靠测试文件与个别顺带导入存活，却仍在 `openspec/specs/` 里占着 11 份主规格、在 Skill 里占着 4 份参考文档、在示例里占着 v4 分镜与代码模块。

结果是同一件事有两份真源：`Report` 定义在被删的 v3 校验器里，`articleText.ts` 与 `article_text.py` 各实现一遍正文字符计数，`visual-spec.md`、`design-constitution.md`、`keynote-design-system.md` 三处各写一遍动效与闸门判据。继续维护这套不可达实现，会让每次改动都要判断「这处是不是旧路径」，并让文档描述的能力与代码实际能力持续背离。

## What Changes

- **BREAKING** 删除文章类型的 v4 制作、体检与评审链：`article/cli.py`、`inspect.py`、`keynote.py`、`production.py`、`render.py`、`animation_review.py`、`benchmark.py`、`storyboard_v4.py`、`visual_narrative.py`、`motion.py`、`media.py`、`workflow_cli.py`、`prepare.py`、`state_tracks_v4.py`、`timeline_v4.py`、`bespoke_review.py`、`rhythm_review.py`、`motion_plan.py`，以及 v3 分镜校验器 `storyboard.py` 中除 `Issue`/`Report` 之外的全部内容。
- **BREAKING** 删除只为上述模块存在的支撑件：`core/catalog.py`（视觉原语注册表镜像）、`core/determinism.py`、`core/diversity.py`、`engine/beats.py`、`engine/browser.py` 的 `AnimatedPage`/`open_animated_page`、`engine/subtitles.py` 的 `segment_windows`/`srt`。
- **BREAKING** 删除 `m2v migrate --from article-v4`：该分支当前只抛「不支持自动迁移」，v5 已是唯一文章契约。
- **BREAKING** 删除 web 侧 v3/v4 画面运行时：`M2VComposition`、`M2VCompositionV4`、`CodeSceneHost`、`LayoutGeometryPreflight`、`SceneTree`、`iconSet`、`runtime/` 下 11 个模块、`schema/storyboard.ts`、`schema/storyboardV4.ts`、`schema/primitiveTypes.ts`、`schema/articleText.ts`、`registry/`，以及 `styles/` 的 theme / keynote / primitives / declarative / scene-tree 五个样式层。`M2V` composition 与契约页 v3/v4 分支一并移除，契约页收敛为 explainer 单入口。
- **BREAKING** 把 `styles/tokens.css` 从三层合并成单层：删掉 `:root[data-m2v-preset='keynote']`、四个 `:root[data-m2v-style-pack='...']` 与 `:root[data-m2v-preset='keynote'][data-m2v-theme='light']`。这三个作用域属性没有任何代码会给页面挂上，而整套 `--m2v-space-*`、`--m2v-radius-*`、`--m2v-size-*`、`--m2v-ink-*`、`--m2v-line` 恰好只写在里面，因此作品代码场景里的 `var(--m2v-space-3)` 一直是空值——画面静默落到初始值，没有任何报错。合并后保留原先 keynote 那一套取值，只有深色一套。
- 搬迁两处仍被当前能力使用的共享件，避免删除造成破链：`Issue`/`Report` → `core/report.py`；`CONTENT_ROOT_ENV`/`PROJECT_MARKER`/`bundle_repo_root`/`content_root` → `core/workspace.py`（同时消除 `core` 命令 `relocation.py` 反向依赖 article 类型私有路径模块的问题）。`engine/browser.py` 的 `PageContract` 经复核只被将删的 `article/render.py` 消费，各类型渲染入口都在自己的 `confirm` 回调里直接比对元数据，因此 `browser.py` 整体删除，不做搬迁。
- 文章适配器的 `prepare_narration` 改为直接调用 `engine.tts.scene_audio(..., contract_version=3)`，保持通用与素材类型的语音缓存契约不变，并据此删除 `article/prepare.py`。
- 连带删除随宿主消失的参数链：`embeddedCodeModules`（文章 v5 分镜没有代码幕）删掉后，`additional_modules` 在 `remotion.bundle` / `prepare_composition_entry` / `scene_manifest.generate` 之间只剩传递、没有来源，`_with_additional_modules()` 与清单里的 `additionalSourceDirs`、生成脚本里的读取一并移除。
- 删除三个固定示例中的 v4 内容：`legacy-test-storyboard.json`、`scenes/*.tsx`、`motion-design.md`、`review.md`、`production.template.json`，以及零引用的 `script-design.md`、`production-workflow.md`、`financial-plan.example.json`、`drop.wav`（连同 `generate.py`、`LICENSE.md` 与 `.gitignore` 中引用它的那几行一起改掉）。
- 参考文档 `references/` 16 → 13：删除 `design-constitution.md`、`keynote-design-system.md`、`visual-spec.md`、`primitive-catalog.md`，新建 123 行的 `design-tokens.md` 承载仍生效的令牌族、画布安全区常量与代码场景作者规则；精简 `render-contract.md`、`media-contract.md`；把 `code-scenes.md` 从 v4 全片 world 契约改写为 `general-plan.json` 的幕级声明方式，并标注 `world`/`stage`/`objectStates`/`beats`/`motion` 五个槽位当前无内容、`probe()` 当前没有消费者。
- 消除跨文档重复：定位句、排除项清单、路径说明、K 闸门与动效规范各自收敛到一处真源；修正 `docs/PROJECT_PLAN.md` 把已交付的 general 能力写成待办的事实错误；把 `paths-and-outputs.md` 里早已过期的溯源结构与性能报告结构改成当前实现。
- 删除 `openspec/changes/archive/` 中 22 份一次性中间产物（README、review、validation、verification、implementation-review、baseline、evaluation），保留每项变更的 proposal / design / tasks / spec delta 与 `.openspec.yaml`。
- 测试：删除 42 个只覆盖被删模块的用例与 3 个 v4 夹具，改写 8 个混合用例使其只保留当前能力断言。

## Capabilities

### New Capabilities

无新增能力。本变更只做删除与收敛，不引入新行为。

### Modified Capabilities

- `article-to-storyboard`：整份移除（98 处 v4 表述、0 处 v5；v5 编排以 `article-explainer` 为准）。
- `bespoke-explanatory-animation`：整份移除。
- `cinematic-directing`：整份移除（导演简报与镜头语言随 v4 场景树消失）。
- `declarative-video-scenes`：整份移除（共享画面路径与预设必填不再存在）。
- `frame-driven-motion`：整份移除（动效计划与量测随 `motionPlan` 消失）。
- `react-component-registry`：整份移除（原语注册表镜像已删）。
- `scene-primitive-tree`：整份移除。
- `science-video-production`：整份移除（已在 `article-explainer` 与 `code-driven-scenes` 中替换，代码与文档零引用）。
- `semantic-motion-timeline`：整份移除（节拍运行时已删）。
- `storyboard-aesthetic-review`：整份移除。
- `visual-direction-pipeline`：整份移除。
- `code-driven-scenes`：改写——代码场景改由 `general-plan.json` 的幕级 `renderer` 声明，删除 v4 全片 world 声明、v4 体检与节点级连续性要求，保留能力白名单、执行边界与帧确定性。新增「作品可以在幕上声明代码场景」与「代码场景接收幕级上下文槽位」两条；原「代码场景继续接受统一体检」只移除不替代，因为现存唯一布局量测只覆盖 v5 讲解模板。
- `keynote-design-system`：改写——保留随仓库分发的字体资产与仍被代码场景消费的令牌（合并为单层），移除排版引擎、观感闸门 K1–K10、状态语汇、四族基元、动效与转场令牌、浅色主题及 `visual.preset` 相关要求；新增「亮度序与单一强调色」与「设计令牌是画面取值的唯一真源」。
- `remotion-renderer`：改写——渲染契约按 composition 收敛（不再有版本 3 的 v3/v4 运行时契约），保留打包、缓存、并发、元数据校验、编码与性能可观测要求。
- `video-production-workflow`：改写——移除关键幕样片要求，保留状态可查询、完整预演、返工闭环、输入版本绑定与配音节奏要求。

## Impact

- **Python**：`src/m2v/` 删除 27 个模块与 3 处函数级片段（净减约 10.6k 行），新增 2 个小模块（`core/report.py`、`core/workspace.py`，合计约 90 行）；`cli.py`、`types/migration.py`、`types/relocation.py`、`types/general/adapter.py`、`types/stock/brief.py`、`types/article/adapter.py`、`engine/remotion.py`、`engine/scene_manifest.py`、`engine/contract_page.py`、`engine/subtitles.py` 需同步修改。`types/financial/commands.py` 经复核属于**保留**范围：它是金融类型的独立材料初始化与离线渲染入口，`financial-timeseries-video` 规格的「新版初始化」与「旧参数拒绝」两个场景直接覆盖它，`tests/test_financial_video.py` 也以它为驱动。删完后从 `m2v.cli` 出发的 AST 可达性结果是 66 个模块中 65 个可达，唯一不可达的就是它。
- **Web**：删除 28 个非测试文件与 19 个测试文件（约 4.4k 行），重写 `Root.tsx`、`contract/main.tsx`、`contract/bridge.ts`、`styles/index.css`、`styles/tokens.css`、`styles/base.css`；`web/package.json` 移除 `zod` 并重新生成 `pnpm-lock.yaml`。
- **CLI 兼容性**：`m2v migrate --from article-v4` 移除，只保留 `--from financial`。其余命令、参数与行为不变。作品材料契约不变，已存在的 v5 文章作品无需迁移。
- **测试**：删除 42 个用例文件与 `tests/fixtures/` 中 3 个 v4 向量夹具，改写 8 个用例文件（`conftest.py`、`test_code_composition.py`、`test_code_gate.py`、`test_code_scenes.py`、`test_render_performance.py`、`test_figure_contrast.py`、`test_scene_manifest.py`、`test_project_cli.py`）。
- **示例**：三个固定示例目录保留，每个收敛到 `article.md`、`project.json`、`storyboard.json`、`README.md` 与按需的 `assets/`。
- **文档**：Skill 参考文档 `references/` 16 → 13；`openspec/specs/` 主规格 26 → 15；归档目录减少 22 个文件。
- **依赖**：`web/package.json` 去掉 `zod`；Python 依赖不变。
