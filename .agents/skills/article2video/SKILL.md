---
name: article2video
description: 把观点型文章转化为竖屏单场景动态叙事短视频。AI 审查输入、选择受控视觉组件并编写 v4 分镜，画面由共享 React composition（Remotion）按帧渲染，用确定性脚本导出 MP4。用于拆分镜、预览、渲染、验收与排查不一致问题。
---

# article2video

产品方向是**单场景动态叙事**：一个观点，一个场景，一段动态叙事。
围绕一个核心观点构建持续存在的视觉世界，通过场景内动画、镜头运动、文字与状态变化完成表达。
完整定义见 [README](../../../README.md#当前能力)，后续路线见
[项目规划](../../../docs/PROJECT_PLAN.md)。
这里的产品场景与技术分镜阶段不同，多个 `stages[]` 元素可以表达同一个持续视觉世界。
单场景创作、输入审查、连续性评审与正式渲染门禁已进入当前制作规则；本 Skill 说明 v4 分镜契约和评审闭环。

**文章是内容层，composition 是表现层，视频是最终发布格式。**

这个 skill 把「文章 → 视频」拆成一条可复现的流水线：AI 负责审查文章、提炼观点并选择组件、
编写分镜（`storyboard.json`）；共享 React composition 读取一个持续的全片 world 并按阶段更新上下文；
脚本负责准备可选配音与字幕，并把 composition 确定性地渲染成 MP4。
AI 不直接生成视频，因此画面可控、可改、可重渲染。

## 何时使用

- 要把一篇观点型文章做成竖屏短视频；
- 要修改已有视频的画面、节奏或文案；
- 要渲染、验收视频，或排查「预览正常但导出异常」的问题。

如果只是写文章或做图文，不需要这个 skill。

如果请求以公司或指数、年份范围和投资收益演变为核心，转到[金融时间序列视频专题](references/financial-timeseries-video.md)。AI 助手自行搜索并核实公开免费行情来源，标的或价格口径有歧义时先澄清；随后在作品内容目录初始化并填写三类材料，运行专题校验、静音预演和渲染命令。金融专题采用 v7、1080×1920、30 fps 计划：横轴从起始年份按年度阶段平滑扩展、投资组合价值折线逐步揭示并保留历史、纵轴随已展示组合价值自适应；顶部为单行假设投资标题及靠右的小字日期/收益率/收益，收益与市值采用中文数量级并保留标的原币名称，端点金额随折线推进；底部显示来源、统计口径和一行风险提示。手机缩放检查和安全区检查通过后才可正式导出。旧计划须显式备份迁移。不展示股价，不收集事件资料，也不使用文章输入审查、字数或口播流程。

## 核心原则

1. **单一真源**：文案与时长只写在 `storyboard.json`，composition 读它绘制，
   渲染脚本读它推导总帧数。不要在任何画面代码里再写一遍文案。
   启用配音后，实际时长由独立媒体清单派生，composition 和渲染脚本共用它，不覆盖原分镜。
   组件集合同样只有一个真源：组件注册表 `web/src/registry/registry.json`。
2. **帧驱动**：画面只由帧号推导得出。禁止 CSS `animation`/`transition`、`Date.now()`、
   `Math.random()`，否则逐帧渲染会闪烁、不可复现。详见
   [渲染契约](references/render-contract.md)。
3. **先校验再渲染**：分镜脚本先过 `validate.py`，画面契约先过渲染脚本的元数据交叉校验，
   错误在开渲前暴露，而不是产出一段坏视频。
4. **预览与导出同源**：预览、体检与渲染使用同一份 storyboard、同一份 composition，
   只缩放不改布局。
5. **层级先于装饰**：先做出背景 / 表面 / 焦点三层与统一的动效曲线，再考虑细节；
   「高级感」来自克制的层级与一致的节奏，而不是更多的颜色和更大的动效。
6. **AI 做导演，不做设计师**：先声明逐幕视觉意图（信息关系、焦点、构图、密度、情绪），
   再声明**视觉论证**——受控视觉模式、核心论点、无正文视觉表达、主要视觉对象与动效语义，
   最后按 [视觉原语目录](references/primitive-catalog.md) 把意图组合成受控场景树。
   原语表达不了的基础视觉能力按注册表契约新增通用原语，不为某支视频写专属画面代码。
   **原语不足时停在视觉转译阶段**：重新构思隐喻、扩展通用原语，或确属作品特例时用代码场景；
   不得改写成「标题 + 文字卡片 + 图标」后继续宣称原来的视觉模式。
   每次从零画一遍既慢又容易失控，也难以保持一支视频内部的观感一致。
7. **先机检再人评**：`review.py` 负责保证「不是废片」（结构、契约、安全区、墨迹）、
   「画面有没有在论证」（视觉叙事 V1–V4 是硬判定）与「动画有没有解释论点」
   （动画论证 A1–A5、A7、A8 是硬判定），AI 助手按
   [评审量表](references/visual-review-rubric.md) 负责「值得看完」，并把
   「图形承担论证」的结论（V6）与「装饰动效是否恰当」的结论（A6）写进 `review.md`。
   把审美也交给脚本，等于放弃质量；反过来只靠眼睛，又会漏掉标签全空这类静默缺陷。
8. **画面变化跟着口播走**：新作品把口播切成语义段并绑定 beat，让字幕、配音和画面
   共用同一批边界；动作从受控词汇表里选，`meaning` 说明这一步解释了什么。
   入场配方只管「怎么出现」，说不清「正在解释哪一步推理」——两者都要，但不能互相替代。
   见[分镜脚本结构](references/storyboard-schema.md)的「语义节拍与字幕同步」。
9. **默认使用电影化动画计划**：全片 world 的对象状态、动作与镜头段绑定全局 beat 或阶段 phase；v1–v3 分镜在所有入口拒绝，必须按 v4 重新编排；没有迁移命令或兼容回退。
10. **作品定制动画**：默认场景树；静态原语能够绘制对象但不能表达必要的状态变化、对象编排或镜头揭示时，可以基于明确的叙事理由使用作品级代码场景。先按 [文章生成分镜](references/article-to-storyboard.md) 编写逐幕动作脚本；代码场景必须使用解析后的 `beats.plan`、提供探针并通过[定制动画动态评审](references/visual-review-rubric.md)。存在代码场景时，缺失或未达标的动态评审会阻断正式渲染。
11. **关键幕先行与 AI 制作记录**：按[文章生成分镜](references/article-to-storyboard.md)先验证开场、核心论证和高潮，再铺开全片；AI 助手自动读取文章、分镜和 `motion-design.md` 填写导演计划，生成联系表、关键幕样片与全片有声评审版后，必须查看实际画面，逐项填写静态/动态评审、可观察证据和返工项。完成结论写入 `production.json` 时绑定评审来源及材料 SHA-256；缺材料或不能查看画面就保持待评审。分镜、媒体、渲染资产或引用材料变化会使相关评审失效。正式成片需要关键幕和全片静态/有声 AI 评审通过，且没有未解决必改项。详见[视觉评审量表](references/visual-review-rubric.md)。完整命令流程见[制作流程](references/production-workflow.md)。

全片铺开前先静音播放开场、核心论证和高潮的关键幕样片；相同构图可以延续，但若只有字幕/标签变化、没有可见的论证性状态推进，必须返工。全片“节奏”单项至少 4/5，并需有声预演时间码或明确阶段证据；缺分、低分或缺证据均不得正式渲染。

## 目录职责

| 路径 | 职责 |
| --- | --- |
| `web/src/compositions/` | 共享 composition：读分镜、逐幕递归解释场景树 |
| `web/src/primitives/` | 场景树递归解释器：布局、内容与图形原语的统一渲染 |
| `web/src/registry/registry.json` | 视觉原语的唯一真源：类型、属性、子节点容量、动效配方 |
| `web/src/runtime/` | 帧驱动共享运行时：时间轴解析 |
| `web/src/styles/` | 设计令牌、预设与场景树原语样式 |
| `web/dist/contract/contract.html` | 渲染契约页（`pnpm -C web build` 的产物），体检用它驱动画面 |
| `.agents/skills/article2video/scripts/` | 校验、配音准备、预览、渲染、视觉评审等命令行工具 |
| `.agents/skills/article2video/scripts/production.py` | 制作记录模板、阶段状态、关键帧、关键幕有声样片与全片评审版 |
| `.agents/skills/article2video/references/` | 渲染契约、分镜结构、代码场景、视觉规范、原语目录、设计宪法、评审量表、目录与输出路径 |
| `examples/<slug>/` | 固定分发的三个端到端示例（文章 + 分镜），仅维护 `buffer-smoothing`、`darts-trial-and-error`、`keynote-baseline`；最多 3 个 |
| `videos/<slug>/` | 每支实际视频一个目录：文章、分镜。**内容不入库**，见 `.gitignore` |
| `videos/<slug>/outputs/` | 该文章的渲染产物，已被 `.gitignore` 忽略 |
| `videos/examples/<slug>/outputs/` | 示例产物，独立一层避免与同名实际文章冲突 |

每篇文章的目录名（slug）稳定且唯一，标题变化不改目录名。

仓库里有两层根：**仓库根**存放 skill 与 web 工程，**工作区根**存放文章与产物。不设内容根时
两者重合；设了 `A2V_CONTENT_ROOT`（或 `--content-root`）时工作区根是那个内容根，文章与产物
一起在仓库之外，命令不变。完整结构与推导规则见
[目录约定与输出路径](references/paths-and-outputs.md)。

`.agents/skills/` 是 Codex 与 DSH 都能识别的项目级 skill 位置；
Claude Code 需要该目录时可用软链接映射到 `.claude/skills/`。

## 标准流程

所有命令都可以在**任意工作目录**执行。输出路径可以省略：脚本按输入文件位置推导归属——
文件在仓库内时向上找到含 skill 标记的仓库根，文件在内容根内时用内容根作工作区根——
再落到 `videos/<slug>/outputs/`。推导结果与执行命令时的工作目录无关；无法推导时脚本直接报错，
不会猜测归属（文章在仓库之外又没设内容根时，报错会点名 `--content-root` 与
`A2V_CONTENT_ROOT`）。

### 0. 准备环境

```bash
uv sync                                # 安装 Python 依赖
pnpm -C web install                    # 安装 web 依赖
pnpm -C web build                      # 构建契约页（体检依赖 web/dist/contract/）
uv run playwright install chromium     # 首次执行，安装浏览器（体检用）
```

### 1. 文章 → 分镜 JSON

**先完成输入审查**：原文审查必须发生在口播重写和分镜之前。按[输入文章审查](references/input-review.md)核对130～170字、核心观点集中度和单场景表达能力；AI 写明观点、视觉隐喻和依据，依据不足时停止。失败时保留原文、提供具体修改意见和合规候选稿；只有用户明确采用后才能将其作为独立输入重新审查。`prepare.py` 也会在配音前阻断缺少有效审查或来源变化的输入。

**按规范生成**：读 [文章生成分镜](references/article-to-storyboard.md)，它规定这一步的输入输出、
持续场景与阶段规划、内容与排版约束、组件不足时的处理，以及生成后必须走完的校验闭环。
产物是 `videos/<slug>/storyboard.json`，字段与校验规则见
[分镜脚本结构](references/storyboard-schema.md)。

这一步由 AI 工具按规范执行；项目不含生成器程序，也不调用模型服务。

目标路径为**提炼核心观点 → 选择核心视觉隐喻 → 构建持续场景 → 编排场景内推理与变化**。标准正文及最终拼接口播分别为130～170字（目标约150字），声明与媒体实际时长分别为35～45秒。要点（完整清单见规范）：

- 先定位核心判断与必要推理，再围绕一个持续视觉世界组织叙事阶段；
- 阶段时长由口播所需时间规划，整片声明时长仍须35～45秒；
- 同一视觉世界内允许镜头和焦点变化；必须切换多个独立视觉世界才能讲清的文章不通过输入审查；
- 不虚构论据或数据；无来源的数值必须把对应节点声明为 `schematic: true`；
- 逐阶段先做视觉转译（受控视觉模式与论证字段），再选原语；文字卡片换布局包装不算图形论证；
- 新作品的口播切成**语义段**并绑定全局 beat（一段一个推理步骤），让字幕、配音和画面共用
  同一批边界；动作从受控词汇表里选真正改变状态或关系的那一个；
- 生成后先过 `validate.py --strict --json`，按字段路径修正到通过再交付。

### 2. 分镜即画面声明

画面默认由共享 composition 渲染：场景树使用全局 `world.sceneTree`，代码世界使用一个全片模块。
分镜根级强制声明 `version: 4`、`schemaVersion: 4`、`directingVersion: 2`、完整 `directingBrief`、
`visualDirection` 与 `visual.preset: "keynote"`；全片 `world` 声明唯一 renderer、对象、状态轨道与镜头，`stages[]` 只表示推理阶段，不切换画面根或 renderer。
每阶段声明 `visualIntent`（信息关系、焦点、构图、密度、情绪，以及视觉论证字段
`mode`/`claim`/`showWithoutText`/`primaryObject`/`motionMeaning`）、
全局 `sceneTree`（受控原语树，内容经 `contentRef` 引用 data）或作品级 code 模块。可选 `visual.theme`（`dark` / `light`）与根级
`visual.preset`（目前唯一取值 `"keynote"`）启用发布会级设计语言：
设计语言层、字号取档与观感闸门一起生效。说明见
[发布会级设计语言](references/keynote-design-system.md)。

新作品还要写**语义节拍**：阶段 `narrationSegments`（每段 `{id, text, beatId}`）
与 `beats`（`{id, action, targets, meaning}`）；v4 不接受字符串 `narration`。
完整口播就是所有阶段段落按顺序拼接，因此不存在第二份文本；动作取受控词汇表，
`targets` 的每个原语都要支持该动作。字段与三条硬规则（严格验收、结尾留白、
单一焦点）见[分镜脚本结构](references/storyboard-schema.md)。

当前有 21 个原语：布局 7（`stack`/`row`/`column`/`split`/`grid`/`radial`/`overlay`）、
内容 5（`text`/`number`/`image`/`icon`/`chart`）、图形 4（`shape`/`surface`/`connector`/`group`），
外加五个**中层原语**（`flow`/`cycle`/`timeline`/`gauge`/`pictogram`；注册表里按绘制方式
归入 layout 与 content 两类，目录表格的「类别」列是权威分类）。
每个原语允许的属性、子节点容量、动效配方与语义动作见
[视觉原语目录](references/primitive-catalog.md)。

原语组合表达不了的画面，按注册表契约登记并实现新原语
（`registry.json` + `SceneTree.tsx` 实现 + `sync_catalog.py` 重新生成 + 机检），
然后沉淀回目录——通用的视觉能力永远优先走这条路。**个别作品个别幕**确实需要
独特的图表面板、关系图或定制 SVG 时，可以为该幕声明
`renderer: { kind: "code", module: "…" }`，把画面交给作品 `scenes/` 下的 TSX 模块；
依赖白名单、静态安全门、离线隔离与确定性纪律见
[代码场景](references/code-scenes.md)——不要为能沉淀成原语的东西写代码场景。

### 3. 校验分镜

```bash
uv run python .agents/skills/article2video/scripts/validate.py videos/<slug>/storyboard.json
```

有错误时终止并列出 `stages[2].data.items` 或 `world.stateTracks[0].binding` 这类可定位的路径，修正后重跑。
加 `--json` 可得到机器可读输出，便于批量修正。
校验器还会按视觉规范给出**警告**（不阻止渲染）：单行字数超限、阶段短于 24 帧、
`emphasis` 短语没有出现在文本里。定稿前用 `--strict` 把它们也当作失败。

`--strict` 还执行全片视觉叙事预算：文字幕阶段占比及相邻限制仍会检查；视觉模式数量只作报告，单一隐喻可以贯穿全片；声明非 `typography`
模式的 tree 阶段必须拿得出结构证据，code world 不由脚本猜测其语义，逐阶段缺视觉论证字段也报错；
声明分段口播的非文字幕还要至少两条 beat 且包含真正改变状态或关系的动作。
失败会定位到 `stages[2].visualIntent.mode` 这类路径；阈值版本化在
`a2v/visual_narrative.py` 的 `RULE_VERSION`。判据与可粘贴的正反例见
[文章生成分镜](references/article-to-storyboard.md)。

### 3.1 配音与字幕准备（可选）

```bash
uv run python .agents/skills/article2video/scripts/prepare.py \
  --storyboard videos/<slug>/storyboard.json
```

省略 `--out-dir` 时媒体写入该文章的 `videos/<slug>/outputs/media/`。
默认 edge-tts 中文晓晓音色，支持 `--voice`、`--rate=-10%`、`--force`。
生成 `media.json`、统一 WAV 和 SRT；音频较长的场景自动延长。无口播场景静音。
声明了 `narrationSegments` 的幕还会在清单里得到逐幕 `resolvedBeats`
（场景内开始包含、结束不包含的帧区间）——画面、字幕与配音共用这批边界，
所以改过分段口播或时长后必须重新 prepare。
修改分镜后重新 prepare，缓存复用不变的配音。流程、缓存与失败处理见
[配音与字幕](references/media-contract.md)。无需将生成媒体加入 Git。

### 4. 预览（人工确认节奏与排版）

```bash
uv run python .agents/skills/article2video/scripts/preview.py \
  --storyboard videos/<slug>/storyboard.json
```

有声预览追加 `--media videos/<slug>/outputs/media/media.json`。
预览由契约页驱动同一份 composition，因此预览看到的就是渲染会画出的画面。

浏览器打开后检查：中文无裁切、正文在安全区内、场景切换自然、重播结果一致。
**不要双击 HTML 预览**——契约页需要本地静态服务提供分镜与资源。

### 5. 渲染

```bash
uv run python .agents/skills/article2video/scripts/render.py \
  --storyboard videos/<slug>/storyboard.json
```

- 想给一支作品配更小的字体：`prepare.py --subset-fonts <源字体>` 会切出只含
本作品用字的子集（落在 `videos/<slug>/outputs/`，源字体只读），**切完立刻用缺字机检判它**
  ——漏字的子集会静默回退到系统字体，那正是要防的。这一步需要可选依赖
  （`uv sync --extra fonts`）：不装、不开这个开关时，默认链路完全离线可跑。
省略 `--out` 时无声导出为 `videos/<slug>/outputs/silent.mp4`；
有声导出追加 `--media videos/<slug>/outputs/media/media.json`，输出 `videos/<slug>/outputs/voiced.mp4`
和同名 SRT。加 `--limit-frames` 时写入 `videos/<slug>/outputs/previews/`，使用相同的成片文件名，
不会覆盖正式成片。显式 `--out` 仍然优先。

渲染脚本会：

1. 校验分镜（无效分镜不开渲）；
2. 把 composition 打包成可渲染 bundle，并先向 composition 要一份真实元数据
   （fps / 尺寸 / 总帧数），与分镜逐项交叉校验，不一致直接报错；
3. 用 Remotion 按帧号确定性渲染，输出 H.264；
4. 合音轨（有声时）、完整解码一遍成片，核对帧数与分辨率，并检查码流是否为
   播放器友好的格式；
5. 写成片溯源（哪一版源码渲的，见下文「渲染验收」）。

先用 `--limit-frames 30` 快速跑通链路再全量渲染。首次渲染前会先打包 composition，
之后同一工程重复渲染无需重新安装依赖。

成片的画面固定为 `yuv420p(tv, bt709)`、配音固定为 AAC-LC 44.1kHz 立体声，
由编码器统一保证，画面代码不需要也不应该干预。

### 6. 视觉评审（渲染前后都该做）

```bash
uv run python .agents/skills/article2video/scripts/review.py \
  --storyboard videos/<slug>/storyboard.json \
  [--media videos/<slug>/outputs/media/media.json]
```

它一次跑完三件事，产物在 `videos/<slug>/outputs/inspect/`：

> 联系表按抽帧的时间轴命名：不带 `--media` 写 `contact-sheet.png`（分镜声明时间轴，
> 也是 `production.json` 登记的静态材料），带 `--media` 写 `contact-sheet-media.png`
> （配音派生时间轴）。两者是同一支片子在两条时间轴上的取帧，不要互相覆盖。

1. **组件契约探针**（最有力）：逐幕在三处采样，读出当前画面里每个元素的实际文本，
   再比对分镜声明的标注有没有真的画出来。**「组件挂上了、画面也出来了，只是图上没有一个字」
   这类缺陷不会报错**，只有真的去读 DOM 才会发现，因此这一步不能省。
   代码场景（`renderer.code`）走最小 DOM 探针协议，协议缺失在严格评审里计为错误；
   作品改过代码场景后，建议加 `--check-determinism` 对阶段边界及全片末帧做同帧重复截图
   与随机寻帧验收（PSNR ≥ 60 dB，失败计为错误），见 [代码场景](references/code-scenes.md)；
2. **帧量测**：墨迹覆盖率（防空幕、黑屏）与上下安全区的墨迹；
3. **观感与动效闸门**：声明了 `visual.preset` 时跑 K1–K10 观感闸门；
   M0–M4 动效闸门对任意作品都跑。

终端会打印错误与提醒，以及**需要人工判断的清单**。
机检只保证「这不是废片」；「值不值得看完」按
[视觉评审量表](references/visual-review-rubric.md) 打分，六项 60 分制、≥ 40 才发布。
评分标准见[设计宪法](references/design-constitution.md)（哪条能机检、哪条只能人看）。
全片节奏必须单项达到 4/5 并引用有声预演时间/阶段证据；缺分或低分会阻断正式渲染。
`report.json` 的 `visualNarrative` 给出 V 系列、`animationReview` 给出 A 系列；
评审结论写进同级的 `review.md`，其中「图形论证」评分与 `## 候选裁决` 小节会被下一次
`review.py` 读成 V6 结论，「动效服务」评分与 `## A6 候选裁决` 小节会被读成 A6 结论。

体检结论分五串，**分开计数、不要混成一个总分**：

- **C 系列**（废片类）：安全区与墨迹覆盖率等结构性结论，回答「这是不是废片」；
- **K 系列**（观感类 K1–K10）：留白预算、强调色占比、同帧字号种类、对齐基线、
  正文对比度、卡片纪律、文字溢出、容器内溢出、图形文字标记，回答「这像不像发布会级别的画面」。
  它只对声明了 `visual.preset` 的视频运行，跳过项都会写明原因——**跳过不等于通过**。
  其中 **K7 文字溢出与 K8 容器内溢出是硬判定**：文本块越出安全区（容差 8px）、
  或声明了 `data-a2v-inside` 的文字穿出它的容器（容差 2px），
  都会并入错误数与退出码，并写明是哪个文本块、往哪个方向越了多少像素——而不是只给一个数字。
  阈值与设计取舍见 [发布会级设计语言](references/keynote-design-system.md)。
- **M 系列**（动效类 M0–M4）：扫描覆盖、入场不弹跳、入场够慢、入场在幕内落地、
  入场不闪烁，回答「动作对不对」。它对任意作品都跑（不需要 `visual.preset`）：
  逐帧走完整个片子，量每一个入场元素。它**只提示、不拦人**，不改错误数与退出码——
  入场快一点是判断问题，不是「画面坏了」。判据与实测值见
  [视觉规范](references/visual-spec.md) 的动效章节。
- **V 系列**（视觉叙事 V1–V6）：V1 文字幕预算、V2 连续文字幕、V3 非文字模式覆盖、
  V4 声明与结构一致性——这四条与 `validate.py --strict` 同口径，失败**并入错误数与退出码**，
  报告列出场景 id、实际值与阈值；V5 列出文字主导候选幕与判定证据，**只呈现**，由人逐条裁决；
  V6 读 `review.md` 里 AI/人工填写的「图形承担论证」结论，**没填写就是「待评审」，不能显示通过**。
  发布清单要求 V6 ≥ 4/5 且没有未裁决候选（`publishable`）。语义结论不并入自动退出码——
  脚本只报告结构证据，语义判断归人。
- **A 系列**（动画论证 A1–A8）：A1 节拍覆盖、A2 含义声明、A3 状态或关系变化、
  A4 字幕同步、A5 结尾停留、A7 单一焦点、A8 稳定结束——这七条是机检，失败
  **并入错误数与退出码**，报告列出场景 id 与具体问题（哪条 beat 没被引用、
  哪一帧有几个焦点、最后一条 beat 距幕尾还剩几帧）；A6 读 `review.md` 里 AI/人工填写的
  装饰动画结论，**没填写就是「待评审」**，只拦「可发布」标记而不伪造脚本错误。
  A 系列的历史自动分析以 V3 局部时间轴为基础；V4 报告会明确标注尚未适配的部分。字符串口播由 v4 校验拒绝，无媒体下的音频同步评审
  如实记为「跳过」。判据见[设计宪法](references/design-constitution.md)的「动画论证闸门」。

### 7. 渲染验收

- **改过组件或运行时之后，已经渲过的成片会静默落后。** `outputs/` 不入库、
  也没有任何东西会提醒你，所以旧成片看上去仍然是「上次验收通过」的样子——
  实测踩到过：两支实际作品的成片比动效重写早了好几个小时，带着旧的 3 帧弹跳。
  现在这件事可机检：成片旁边有溯源（见 [渲染契约](references/render-contract.md)
  的「成片溯源」），体检命令会给出「对得上 / 落后（并指名文件）/ 无法判断」，
  所以改完资产先跑一次体检看结论，别靠人比对文件时间戳。
  分镜改过而媒体清单没跟上的（`分镜已修改，请重新 prepare`）先跑 `prepare.py`，
  配音文本没变时它会全部命中缓存，不需要联网。
- 渲染脚本最后一行输出帧数、时长、分辨率、实测帧率与文件大小；
- 抽看全片首帧、阶段边界、末帧，确认无空白帧、无文字裁切且对象状态连续；
- 用系统默认播放器打开一次成片：全范围像素格式（`yuvj420p`）ffmpeg 能解码，
  但 Windows 播放器会报 `0xc00d36c4`；验收已会自动拦下，人工再确认一次最稳妥；
- 需要逐像素比对时，用同一帧重复渲染两次比对。

## 命令速查

validate / prepare / preview / review / render 五个命令与 `production.py`（共六个入口）
都接受 `--content-root <目录>`（文章与产物放在仓库之外的内容根时使用；
也可以设环境变量 `A2V_CONTENT_ROOT`，命令行优先）。不设时工作区根就是仓库根。

```bash
# 校验分镜（有 --strict 把警告也视为失败）
uv run python .agents/skills/article2video/scripts/validate.py <storyboard.json> [--strict] [--json] [--media <media.json>]

# 本地预览（契约页驱动同一份 composition）
uv run python .agents/skills/article2video/scripts/preview.py --storyboard <json> [--port 8000] [--media <media.json>] [--content-root <目录>]

# 配音准备（省略 --out-dir 时写入 videos/<slug>/outputs/media）
uv run python .agents/skills/article2video/scripts/prepare.py \
  --storyboard <json> [--out-dir <目录>] [--voice <音色>] [--rate=±N%] [--force] [--content-root <目录>] [-v]

# 视觉评审（省略 --out-dir 时写入 videos/<slug>/outputs/inspect）
uv run python .agents/skills/article2video/scripts/review.py \
  --storyboard <json> [--media <media.json>] [--out-dir <目录>] [--content-root <目录>] [-v]

# 制作阶段查询、生成记录模板、关键幕样片与全片评审版
uv run python .agents/skills/article2video/scripts/production.py status --storyboard <json> [--media <media.json>]
uv run python .agents/skills/article2video/scripts/production.py template --storyboard <json> --out <作品目录>/production.json
uv run python .agents/skills/article2video/scripts/production.py keyframes --storyboard <json>
uv run python .agents/skills/article2video/scripts/production.py samples --storyboard <json> --media <media.json>
uv run python .agents/skills/article2video/scripts/production.py rehearsal --storyboard <json> --media <media.json>

# 正式渲染（必须已有当前分镜、媒体和资产版本的完整评审记录）
uv run python .agents/skills/article2video/scripts/render.py \
  --storyboard <json> [--out <输出.mp4>] [--limit-frames N] [--content-root <目录>] \
  [--media <media.json>] [--crf 18] [--preset medium] [--no-probe] [-v]
```

## 排查常见问题

| 现象 | 原因与处理 |
| --- | --- |
| `找不到可用的 web 工程` / 打包失败 | `web/` 依赖没装：`pnpm -C web install` 后重试 |
| 体检报「契约页不存在」 | 先 `pnpm -C web build` 构建 `web/dist/contract/contract.html` |
| `缺少查询参数 a2v-storyboard` | 契约页必须由脚本经本地静态服务打开，不要双击 HTML |
| `总帧数不一致` / `fps 不一致` | composition 元数据与分镜不一致：检查分镜是否保存、场景时长是否合法 |
| `不支持 v4 之前分镜` | v1–v3 分镜不能进入任何入口；依据[分镜脚本结构](references/storyboard-schema.md)重新编排，并按要求补齐导演字段 |
| `未知视觉原语` / `原语 X 不支持属性 Y` | 场景树用了注册表之外的原语或属性：查 [视觉原语目录](references/primitive-catalog.md) 的可选值与容量 |
| `动效目标 X 不存在` / `原语 X 不支持动效` | 动效绑定的节点 id 写错或配方超出该原语允许范围：按目录声明修正 |
| `内容引用 data.x 指向不存在的字段` | `contentRef` 指向的分镜 data 字段缺失或拼写不一致 |
| 成片有随机闪烁 | 画面里用了 CSS 动画或 `Date.now()`：组件必须由帧号推导（web 测试会拦） |
| 预览正常但导出缺字 | 用了系统字体而渲染机器上没有该字体，改为随仓库分发 webfont |
| 动画后段像卡住 | 场景被配音拉长后画面完全静止，入场结束后加常驻微动（`breath` 级别） |
| 画面扁平没有层次 | 缺少背景/表面/焦点三层：先加背景层与卡片内高光、双层投影（见视觉规范） |
| 强调色加在文案上却不生效 | `emphasis` 的短语没有原样出现在该场景文本里，`validate.py` 会给出警告 |
| `声明为 comparison，但场景树只有文字…` | 该幕声明了非 `typography` 模式却拿不出结构证据：改声明为 `typography`，或用 `chart`/`image`/`connector`/`radial` 真正承担论证，不要只加图标或换布局包装 |
| `文字幕 N/M 幕，超过允许上限` | 全片文字卡片过多：把其中几幕改成图形论证，或把相邻文字幕合并成一幕 |
| `相邻两幕均为文字幕` | 文字幕之间必须隔开论证型图形场景，调整幕序或改造其中一幕 |
| `模式多样性` | 模式数量只用于报告；持续单一视觉隐喻可贯穿全片，不要求模式最低数量 |
| 严格校验要求补齐视觉论证字段 | 旧分镜缺 `mode`/`claim`/`showWithoutText`/`primaryObject`/`motionMeaning`：逐幕补齐；脚本不会根据场景树自动推断语义 |
| `材料已缺失或摘要已变化`（keyframes） | 静态联系表被按另一条时间轴重画过：`production.py keyframes` 与不带 `--media` 的体检写 `contact-sheet.png`（分镜声明时间轴，登记的就是它），带 `--media` 的体检写 `contact-sheet-media.png`；重新执行 `production.py keyframes` 恢复登记材料 |
| V6 显示「待评审」或 `publishable=否` | `videos/<slug>/outputs/inspect/review.md` 还没有人工结论，或 V5 候选未裁决、评分低于 4/5：按[评审量表](references/visual-review-rubric.md)填写评分与 `## 候选裁决` |
| A6 显示「待评审」或 `publishable=否` | 同一份 `review.md` 缺「动效服务」评分，或 `## A6 候选裁决` 没逐条裁决 `animationReview.a6.candidates` 列出的装饰配方：按[评审量表](references/visual-review-rubric.md)填写 |
| 正式渲染提示「全片节奏评审待完成/未通过」 | `review.md` 的节奏评分缺失、低于 4/5，或没有有声预演时间码/明确阶段依据；返工后更新评审和材料再试 |
| A 系列报「没有任何 beat 改变对象状态或关系」 | 这一幕的 beat 全是 `establish`/`highlight`：换成 `connect`/`accumulate`/`transform` 这类真正改变状态或关系的动作，或承认它是文字幕并改 `visualIntent.mode` |
| A 系列报「字幕 cue 与口播段切法不一致」 | 某个口播段切在一句话中间，字幕 cue 跨过了段边界：把段边界挪到句子标点处 |
| A 系列报「最后一条 beat 距幕尾只有 N 帧」 | 幕尾稳定阅读时间不足 12 帧：加长 `durationInFrames`，或把最后一段口播缩短 |
| A 系列报「第 N 帧有 M 个焦点」 | 同帧点亮了多处（显式 `state: "focus"` 或两个关系容器的当前阶段）：只留一个，其余改成 `muted` 或让它不参与 beat 目标 |
| 导出画面被裁切 | 画面尺寸超出 1080 × 1920，检查是否有元素溢出 |
| 渲染中途 ffmpeg 退出 | 尺寸为奇数（yuv420p 要求宽高为偶数），或磁盘空间不足 |
| 成片能解码但播放器打不开 | 码流是全范围像素格式（`yuvj420p`/`pc`）或 24kHz 单声道 AAC；验收阶段现已报错拦下，参数见 [渲染契约](references/render-contract.md) 的「码流兼容性」 |
| 播放器报 `0x80070005 你没有访问该文件的权限` | 成片经临时目录中转时带走了「关闭继承」的 ACL，打包应用（Windows 11 新版媒体播放器）读不到；`render.py`/`prepare.py` 会自动 `icacls /reset` 修复，见 [渲染契约](references/render-contract.md) 的「交付文件的访问权限」 |
| `无法推导文章归属` | 分镜不在 `videos/<slug>/`、`examples/<slug>/` 内：移入规范目录，或用 `--content-root`/`A2V_CONTENT_ROOT` 指定内容根，或显式指定输出路径 |
| `无法推导默认输出路径` | 省略 `--out` 但没有 `--storyboard`，补上分镜或显式指定 `--out` |
| 提示 narration 却按无声导出 | 没传 `--media`；先执行 `prepare.py`，再带 `--media` 渲染 |
| 体检溯源结论是 `stale` | web 源码在成片渲染之后改过：重新渲染一次成片 |

## 当前边界

已实现：分镜校验（含严格模式下的视觉叙事预算与「声明与结构」反证）、
输入字数统计与输入审查门禁、130～170字正文/口播校验、35～45秒声明与实际时长门禁；
单场景 v4 分镜（全片 `world`、阶段 `stages`、全局对象状态与镜头时间轴）、分段口播与语义节拍
（媒体清单 version 4 携带全局 `resolvedBeats`，画面 / 字幕 / 配音共用同一批边界）、自动配音与逐句字幕、
React composition 画面（全片场景树解释器 + 注册表登记的 21 个受控原语，含五个中层原语
`flow`/`cycle`/`timeline`/`gauge`/`pictogram`，原语注册表单源；个别幕可用
`renderer.code` 的作品级代码场景）、
契约页体检（K/M 闸门、场景树契约探针、视觉叙事 V 系列与动画论证 A 系列）、
Remotion 确定性渲染与成片验收、按文章目录推导输出路径、内容根（文章与产物可放在
仓库之外、`videos/` 不入库）、按作品切 webfont 子集（`prepare.py --subset-fonts`，
需要可选依赖 `uv sync --extra fonts`），以及设计语言预设（分镜声明 `visual.preset: "keynote"`
后启用令牌层、排版引擎与观感闸门）。

尚未实现，不要当作已有能力使用：

- **视觉模型自动评审**：K 系列只给出数值，V5 只列出候选与结构证据，
  「图形有没有真的承担论证」（V6）与「装饰动效是否恰当」（A6）都由人填写，
  最终判断仍要按 [视觉评审量表](references/visual-review-rubric.md) 完成；
- **按内容自动选预设**：预设必须由分镜显式声明；
- **自动拆场景**：引擎能算出「缩到正文下限仍放不下」并由 K7 报出来，
  但把一幕拆成两幕仍由人（或上游 AI）决定，脚本不代劳；
- **自动选曲**：尚未实现；本地背景音乐、节拍音效及混音已支持，见媒体契约；
- **分镜生成器**：文章到分镜已可按 [文章生成分镜](references/article-to-storyboard.md) 的规范生成，
  但由 AI 工具执行，没有内置的生成器程序、模型调用或批量生成；
- **内容根的自动探测**：内容根只能由 `--content-root` 或 `A2V_CONTENT_ROOT` 指定，
  脚本不会去猜（猜错的后果是把成片写到你没在看的地方）；
- **发布**：没有对接抖音或任何平台的上传接口；
- **批处理与历史版本**：没有多篇批量渲染，也不保留成片历史版本。

## 参考文档

- [文章生成分镜](references/article-to-storyboard.md)：从文章产出分镜的步骤、约束、校验闭环与组件缺口处理
- [代码场景](references/code-scenes.md)：`renderer.code` 的模块契约、依赖白名单、探针协议、确定性适配与安全模型
- [制作流程](references/production-workflow.md)：阶段查询、关键幕样片、全片预演和版本化返工闭环
- [目录约定与输出路径](references/paths-and-outputs.md)：文章目录、归属推导与默认产物位置
- [配音与字幕](references/media-contract.md)：媒体清单、TTS 缓存、字幕与音轨合成
- [视觉评审量表](references/visual-review-rubric.md)：全片静态/动态维度、评审证据及返工要求
- [渲染契约](references/render-contract.md)：画面实现的 `__A2V__` 接口、渲染引擎与确定性要求
- [分镜脚本结构](references/storyboard-schema.md)：字段定义、分段口播与语义节拍、校验规则
- [竖屏视觉规范](references/visual-spec.md)：画布、安全区、排版层级、景深、动效配方与风格方向
- [发布会级设计语言](references/keynote-design-system.md)：`visual.preset` 的启用方式、字号阶与令牌、排版引擎、K1–K10 观感闸门与静默失效清单

## 精品科普 P0 制作

先按 [文章生成分镜](references/article-to-storyboard.md) 重写口播，再制作对象变化。`script-design.md` 只记录段落目的与场景引用，口播仅存分镜。全片 `production.json` 增加五项口播内容评审，各至少 4/5，必须引用实际有声预演材料。声音参数与混音见 [媒体契约](references/media-contract.md)，对象动画共享工具见 [代码场景](references/code-scenes.md)。使用 [缓冲区示例](../../../examples/buffer-smoothing/storyboard.json) 作为六幕机制解释参考，不机械复用它的幕序或构图。
