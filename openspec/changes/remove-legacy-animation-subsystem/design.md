## Context

仓库当前有 5 个活跃视频类型（`financial-timeseries`、`article-narrative`、`general`、`housing-timeseries`、`stock-montage`），共享底座是 `src/m2v/{core,engine,types}` 加统一入口 `src/m2v/cli.py`，画面侧是 React 19 + Remotion 的 5 个 composition。在这之上还叠着一层 v3/v4「旧共享动画」实现：文章 v4 制作/体检/评审链、场景树原语、语义节拍运行时、视觉导演管线与发布会级设计语言排版引擎。

从 `m2v.cli` 做 AST 可达性分析，Python 侧只有 70/89 个模块可达，不可达的 19 个全部属于这层旧实现。Web 侧 5 个在用 composition 都不引用 `SceneTree`、`runtime/`、`registry/` 与 `schema/storyboard*`；把它们拉进 bundle 的唯一锚点是契约页 `contract/main.tsx` 的 v3/v4 分支与 `Root.tsx` 里已无消费者的 `M2V` composition。

约束：作品材料契约（`project.json` + v5 `storyboard.json` / `general-plan.json`）不能变；`m2v` 现有命令与参数不能变（`migrate --from article-v4` 除外，它当前只抛错）；`examples/` 只能有那 3 个目录，只能改内容。

## Goals / Non-Goals

**Goals:**

- 让「从 `m2v.cli` 可达」成为 Python 侧模块存活与否的判定标准，删完后可达集合等于全部剩余模块。
- 让 Web 侧非测试模块全部从 5 个 composition 与 explainer 契约页可达，依赖表与真实使用一致。
- 保住三处仍被当前能力使用的共享件，删除不产生破链。
- 把重复的文档真源收敛成一处，并让 `openspec/specs/` 只描述已实现行为。

**Non-Goals:**

- 不改任何作品材料契约、CLI 命令形态、成片编码参数或验收门槛。
- 不重命名 `keynote-design-system` 能力（虽然它收窄成令牌体系），避免在删除型变更里混入能力改名。
- 不重构仍活跃的金融/房价/素材/通用链路的内部结构。
- 不清理 `openspec/changes/archive/` 里每项变更的 proposal / design / tasks / spec delta。

## Decisions

### D1：先搬迁共享件，再删宿主模块

`Report`/`Issue` 定义在被删的 v3 校验器 `types/article/storyboard.py` 里，却被 `types/general/adapter.py` 与 `types/stock/brief.py` 用来承载 `engine/sound.py` 的校验结论。

选择：先把它们原样搬到按职责命名的小模块 `core/report.py`，改完消费方导入并跑一次测试，再删宿主模块。

替代方案是把 `Report` 留在 `engine/sound.py` 里 —— 否决，因为它是通用报告结构，不属于声音引擎。

`engine/browser.py` 的 `PageContract` 最初也在搬迁清单里，但复核发现它只被两处引用：`browser.py` 自身的页面加载路径，以及 `remotion.py` 的 `CompositionMetadata.contract` 属性；而后者只被 `article/render.py` 消费。各类型的渲染入口都在自己的 `confirm` 回调里直接比对 `(fps, width, height, durationInFrames)` 元组，不经过 `PageContract`。因此结论改为：`browser.py` 与 `CompositionMetadata.contract` 一并删除，不新建 `engine/page_contract.py`。这条修正同时让 `remotion.metadata` / `render_frames` / `render_session` 的 `composition_id` 去掉 `"M2V"` 默认值、改为必填——那个默认值没有任何真实消费者，留着只会掩盖「这个 composition 是谁」的问题。

### D2：路径工具搬到 `core/workspace.py`，消除 core → article 的反向依赖

`types/relocation.py`（统一入口 `m2v relocate` 的实现）只用到 `types/article/paths.py` 的 4 个名字：`CONTENT_ROOT_ENV`、`PROJECT_MARKER`、`bundle_repo_root`、`content_root`。这是「共享命令依赖某个视频类型的私有路径模块」的反向依赖，`paths.py` 其余 358 行（`ArticlePaths`、`for_storyboard`、`locate_article` 等）只服务已删的 v4 链路。

选择：把这 4 个名字搬到 `core/workspace.py`，并让 `cli.py` 复用 `CONTENT_ROOT_ENV` 常量而不是硬编码字符串 `"M2V_CONTENT_ROOT"`。这样 `core` 只依赖 `core`。

### D3：文章适配器的旁白准备改为直连 `engine.tts`

`types/article/adapter.py::prepare_narration` 现在 `from m2v.types.article.prepare import _scene_audio`，而 `_scene_audio` 只是 `engine.tts.scene_audio` 的一层包装，并带 `contract_version=3`。这是删除 `article/prepare.py` 的唯一阻碍。

选择：在适配器里直接调用 `tts.scene_audio(text, voice, rate, cache, force=False, contract_version=3, rhythm=rhythm)`，显式保留 `contract_version=3`。该版本号是通用与素材类型语音缓存的键，改动会让所有已缓存语音失效。

### D4：契约页收敛为 explainer 单入口，`M2V` composition 整体移除

`web/src/contract/main.tsx` 在缺少 explainer 参数时渲染 v3/v4 的 `ContractApp`，这条分支是整条旧 web 链的唯一锚点。`Root.tsx` 里的 `M2V` composition 则按 `props.version === 4` 分派 `M2VCompositionV4` / `M2VComposition`，而 5 个适配器全部显式传自己的 composition id，`engine/remotion.py` 的 `COMPOSITION_ID = "M2V"` 只是默认参数。

选择：契约页只保留 `ExplainerContractApp`（`window.__M2V__` 版本 5）；`Root.tsx` 只注册 5 个 composition；`remotion.py` 去掉 `COMPOSITION_ID` 默认值，改为必填。删除后 `zod` 只剩被删 schema 在用，一并从 `web/package.json` 移除。

替代方案是保留一个 `M2V` 兼容 composition —— 否决，没有任何适配器或文档引用它，保留只会让「哪些 composition 是当前能力」继续含糊。

### D5：样式层删掉四个类层，并把令牌合并成单层

`styles/index.css` 有 9 个 `@import`。其中 `tokens.css`、`base.css` 与 Tailwind 三层仍被代码场景使用；`keynote.css`、`primitives.css`、`declarative.css`、`scene-tree.css` 四个类层只服务 `SceneTree`，连同 `base.css` 中只服务场景树的 `[data-m2v-stage]` 规则一起删除（删除前 grep 全仓库 `data-m2v-stage` 确认无其他消费者）。

复核 `tokens.css` 时发现一个独立缺陷：它有**三层**——默认 `:root` 层 56 个令牌，加 `:root[data-m2v-preset='keynote']` 与 `:root[data-m2v-style-pack='...']` 两个作用域层共 103 个令牌，而**没有任何代码会给页面挂上这两个属性**（全仓库 grep：只有 `tokens.css` 的定义、`test_figure_contrast.py` 的断言与 `web/README.md` 的一句陈旧说明）。整套 `--m2v-space-*`、`--m2v-radius-*`、`--m2v-size-*`、`--m2v-ink-*`、`--m2v-line` 恰好只写在作用域层里，因此作品代码场景里的 `var(--m2v-space-3)` 在运行时一直是空值——画面安静地落到初始值，没有任何报错。

选择：把三层合并成**单层** `@theme static`，保留原先 keynote 那一套取值；删掉 `:root[data-m2v-preset='keynote']`、四个 `:root[data-m2v-style-pack='...']` 与 `:root[data-m2v-preset='keynote'][data-m2v-theme='light']`。同时把 `base.css` 里硬编码的 `#07090f` / `#f4f7fb` 改为引用 `--m2v-bg-0` / `--m2v-ink-1`。

替代方案是保留作用域层、只把它们改成 `:root`——否决，那只是把同一个缺陷换个写法；替代方案二是保留浅色层——同样否决，没有任何代码选择浅色，留着等于承诺一套取不到的能力。

### D6：文档收敛成单一真源，而不是逐份打补丁

`design-constitution.md`（C/K/V/A 闸门）、`keynote-design-system.md`（1541 行，排版引擎与 K1–K10）、`visual-spec.md`（v3/v4 场景树规范）、`primitive-catalog.md`（由已删 `registry.json` 生成）描述的能力全部随本次删除消失。四处文档又互相重复（K1–K10 在两份里各写一遍，动效规范在 `render-contract.md` 与 `visual-spec.md` 各写一遍）。

选择：删除这四份，新建一份 ≤150 行的 `references/design-tokens.md` 承载仍然生效的内容（令牌族、画布与安全区常量、代码场景作者规则）；`render-contract.md` 与 `media-contract.md` 各精简到只描述当前契约；`code-scenes.md` 改写为 `general-plan.json` 的声明方式。跨文档重复（定位句、排除项清单、路径说明）逐条收敛到一处并改为链接。

### D7：用 REMOVED + ADDED 而不是 MODIFIED 表达真正重写的需求

OpenSpec 的 MODIFIED 块会整体替换原需求，因此必须原样保留原有 scenario 名字。对于「制作阶段必须可查询」「模块化设计令牌与兜底取值」「版本 3 渲染契约」这类要求，其原有 scenario（连续性待定、四族基元状态矩阵、图形颜色分类等）描述的是已删除的实现，原样保留会让规格自相矛盾。

选择：把重写的需求放进 `## REMOVED Requirements`（附 Reason 与 Migration），再以新名字 ADDED 对应需求。复核后进入这一类的有四条：`制作阶段必须可查询`、`模块化设计令牌与兜底取值`、`版本 3 渲染契约`、`作品可以声明代码场景`、`代码场景继续接受统一体检`、`代码场景接收统一导演运行时上下文`、`主题预设与亮度序`——它们的原有 scenario 分别描述已删除的阶段运行时、四族基元状态矩阵、图形颜色分类、全片 world renderer、C/K/M 闸门量测、全局 beats/镜头上下文与浅深双主题，原样保留会让规格自相矛盾。

其中 `代码场景继续接受统一体检` 只 REMOVED 不 ADDED：现存唯一布局量测 `explainer_render.py::MEASURE` 只覆盖 `article-narrative` 的 v5 讲解模板，不覆盖 `general` 的代码场景，`probe()` 目前没有消费者——保留该需求等于承诺一项无人执行的验收。`主题预设与亮度序` 也只 REMOVED，改由新的 `亮度序与单一强调色` 承载仍然成立的约束。

### D8：测试按「是否只覆盖被删模块」二分

31 个用例文件的全部断言都落在被删模块或被删 web 资产上（含 `test_web_registry.py` 依赖已删的 `sync_catalog`、`test_icon_bundle.py` 读 `iconSet.tsx`、`test_scene_tree_text_breaks.py` 读 `scene-tree.css`、`test_text_fit.py`/`test_react_design_tokens.py`/`test_midlevel_probe.py`/`test_web_charts.py` 驱动旧契约页与场景树），整体删除；`tests/fixtures/` 的 3 个 v4 向量夹具一并删除。其余混合用例逐条删掉对已删模块的导入与断言，保留当前能力验收面；`test_figure_contrast.py` 从「四份 CSS 抽取图形令牌」收敛为「只读 `tokens.css`」。

复核时把「只覆盖被删模块」的判断从 `src/` 扩到 `tests/`，因此实际删除数从计划的 31 升到 42：`test_asset_fingerprint.py`、`test_beat_media.py`、`test_media.py`、`test_paths.py`、`test_content_root.py`、`test_production_workflow.py`、`test_render_provenance.py`、`test_remotion_render.py`、`test_react_contract.py` 等文件的被测函数（`asset_fingerprint`、`provenance_status`、`render_with_remotion`、`for_storyboard`、`resolve_from_windows`）全部只定义在被删模块里，没有任何存活实现可供改写，因此改为删除而不是改写。

同一轮复核也推翻了 `types/financial/commands.py` 的删除判断：`src/` 内确实零引用，但它是金融类型的独立材料初始化与离线渲染入口，被 `financial-timeseries-video` 规格的两个场景和 `tests/test_financial_video.py` 直接覆盖，删掉会丢能力。因此保留它，并把验收口径写成「从 `m2v.cli` 可达」而非「等于全部模块」——`commands.py` 是有意的第二入口。

### D9：验收口径

「可达集合等于全部模块」这条判据在遇到有意保留的第二入口时不成立。实际采用的判据是：**从 `m2v.cli` 出发不可达的模块，必须能说出它为什么仍然存在**。删完后只剩 `m2v.types.financial.commands` 一项，理由记录在 D8。

### D10：连带删掉随宿主消失的参数链

`embeddedCodeModules`（文章 v5 讲解分镜里嵌入代码模块）只被 v4 全片 world 契约使用，v5 讲解模板的模板集是 `point|compare|steps|cause|image`，没有代码幕。删掉 `types/general/adapter.py` 的 `_embedded_modules()` 与 `_validate_embedded_checks` 里的指纹循环之后，`additional_modules` 这条参数链就只剩「传递」而没有「来源」：

`remotion.bundle(additional_modules=…)` → `prepare_composition_entry` → `scene_manifest.generate` → 清单里的 `additionalSourceDirs` → `gen-active-scenes.mjs` 的 Tailwind `@source` 行，另有 `remotion._with_additional_modules()` 把它并进缓存键与溯源指纹。

选择：整条删掉，而不是留着「以后可能有用」。一条没有任何调用方传值的参数会在下一次读代码时被当成活能力，而它唯一的行为是给指纹加几个永远不会出现的键。`scene_manifest` 的 `additionalSourceDirs` 键与生成脚本里的读取一并移除（生成脚本原本就按 `?? []` 容忍缺失）。

### D11：把「不可达但仍在」的判断写成文档事实

删除过程中出现三次「看起来是死的、实际有消费者」与一次反向误判，因此文档里凡是描述能力的段落都按当前代码核实过：

- `web/README.md` 的作品代码场景一节原本写 `CodeSceneHost.tsx` 与全片 `world.renderer`——当前入口是 `GeneralVideo.tsx` 的幕级 `renderer`；
- `web/README.md` 的渲染契约一节原本写 `window.__M2V__` version 4 并列出 `currentFrame()`、`world()`、`stage()`、`objectStates()`、`camera()`、`beats()` 探针——当前契约只有 `version`、尺寸/帧数、`ready()`、`seekToFrame()`；
- `paths-and-outputs.md` 的溯源与性能报告两节原本描述一套 `version: 4` 的 `workspace` / `page` / `assets` 结构——当前是 `schemaVersion: 1` 加 `type` / `projectId` / `preparedFingerprint` / `compositionId` / `inputs`；
- `code-scenes.md` 整篇是 v4 全片 world 契约，改写为 `general-plan.json` 的幕级声明，并明确标注 `world` / `stage` / `objectStates` / `beats` / `motion` 五个槽位**当前无内容**、`probe()` **当前没有消费者**。

`@m2v/scene` 的 `M2VCodeSceneProps` 里 `frame` 的注释原本写「全局帧号：整片时间轴上的绝对帧」，但 `GeneralVideo` 在幕的 `Sequence` 内取 `useCurrentFrame()`，实际是幕内帧——按代码改正注释（文档级改动，不改行为）。

## Risks / Trade-offs

- **误删仍被间接使用的模块**：以 AST 可达性为准，但可达性不等于被调用。缓解：删完后跑全量 `uv run pytest` 与 `pnpm -C web test`，并按验收清单做一次端到端 `preview` + `render`。
- **语音缓存失效**：`prepare_narration` 换实现时若漏掉 `contract_version=3`，通用与素材类型的已缓存语音会全部重算。缓解：在适配器里显式传参，并用 `test_tts_backend`、`test_voice_selection` 验证。
- **样式回归**：删除四个类层后，代码场景若隐式依赖某个类层规则会失去样式。已确认代码场景与示例场景只写 `var(--m2v-*)`；仍需在删除后跑 `pnpm -C web build` 并目视核对一个通用视频帧。
- **契约页量测能力下降**：旧契约页曾支撑 C/K/M 系列闸门。删除后只剩画布分区溢出、字幕遮挡与容器内溢出三项硬判定。这是有意的能力收缩，已在 `article-explainer` 与 `keynote-design-system` 的 delta 中写明。
- **规格删多了**：11 份主规格整份删除是不可逆的语义决定。缓解：`openspec/changes/archive/` 保留每项变更的完整 delta 与 proposal，历史可追溯；本次变更自身的 delta 也记录了 Reason 与 Migration。
- **`article-to-storyboard` 规格的取舍**：该规格 98 处 v4 表述、0 处 v5，判定为整份移除；v5 编排由 `article-explainer` 与 Skill 的 `article-to-storyboard.md` 承载。若复核发现其中有仍生效的通用编排要求，应改为 MODIFIED 而不是 REMOVED。
