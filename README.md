# article2video

将观点型文章转换成竖屏信息可视化短视频的个人内容生产项目。

**文章是内容层，画面工程是表现层，视频是最终发布格式。** 项目把抽象观点、因果关系和核心模型
转化为观众可以直观看到的思想结构。

## 这是什么

一个**项目级 Skill**：由 AI 编程工具（Codex、Claude Code、DSH 等）读懂文章，分阶段声明
内容分镜、视觉策略、逐幕意图与视觉论证、场景树与动效，写成 v2 分镜 JSON；画面由仓库
`web/` 里的共享 React composition（Remotion）按场景树逐帧渲染成 MP4。
AI 不直接生成视频，因此画面可控、可改、可重渲染。

```text
文章 → 内容分镜 → 视频级视觉策略 → 逐幕视觉意图与视觉论证 → 场景树与动效 → v2 分镜 JSON
     → 配音与字幕准备（可选）→ 共享 composition 逐帧渲染与音轨合成 → 竖屏 MP4
```

Skill 位于 [`.agents/skills/article2video/`](.agents/skills/article2video/SKILL.md)，
该目录被 Codex 与 DSH 直接识别；Claude Code 需要时可用软链接映射到 `.claude/skills/`。

## 当前状态

仓库已接入 [OpenSpec](openspec/config.yaml) 进行功能变更规划：`openspec/changes/` 存放进行中的提案、规格与任务，归档后的能力规格存放在 `openspec/specs/`，已完成的变更连同其提案、设计与逐轮实施记录留档在 `openspec/changes/archive/`。Codex 与 DSH 的工作流 Skill 位于 `.agents/skills/openspec-*/`。首次使用前需安装 OpenSpec CLI；在仓库根目录可用 `openspec list` 查看变更，以 `$openspec-propose` 发起新提案。

已完成**场景树架构切换**（v2）：画面不再由整页语义组件决定，而是由每幕声明的**场景树**
经共享递归解释器（`web/src/primitives/SceneTree.tsx`）逐节点渲染。旧整页组件、
`data.figure.kind`、场景类型默认映射与作品专属 `scenes.tsx` 画面模块已全部删除；
旧版分镜（version=1）进入任何新版入口都会被拒绝并给出迁移指引。

- **分镜 v2 结构**：根级声明 `schemaVersion: 2` 与视频级视觉策略 `visualDirection`
  （母题、构图偏置、密度、节奏、禁止复用项）；每幕声明 `visualIntent`（信息关系、视觉焦点、
  构图、密度、情绪，以及视觉论证字段 `mode` / `claim` / `showWithoutText` /
  `primaryObject` / `motionMeaning`）、`sceneTree`（受控原语树）与 `motions`
  （按节点 id 绑定的具名动效）。
  结构与约束见
  [分镜脚本结构](.agents/skills/article2video/references/storyboard-schema.md)；
- **导演层与审美闭环**：可选 `directingVersion: 1` / `directingBrief` 声明核心命题、情绪曲线、视觉母题与风格包；场景可声明 `camera`、`transition` 和 beat 状态字段。运行时已支持受控镜头运动、显式跨幕继承 / 有限变形 / 拆解 / 重组 / 断裂、注册表风格配方、联系表、审美预检与渲染前门禁；旧分镜未启用时保持原行为。
- **分段口播与语义节拍**：新作品用 `narrationSegments`（每段 `{id, text, beatId}`）
  取代字符串 `narration`（二者互斥），并用 `beats`（`{id, action, targets, meaning}`）
  声明这一步推理在画面上如何发生。动作取自 11 个受控动词（`establish` / `connect` /
  `transfer` / `accumulate` / `deplete` / `transform` / `compare` / `highlight` /
  `loop` / `break` / `restore`），其中 `establish` 与 `highlight` 是**中性**动作——
  只让对象出现或更醒目，不算一次状态或关系变化。有声路径由真实 WordBoundary 解析出
  逐幕 `resolvedBeats`（媒体清单 version 2），字幕、配音与画面因此共用同一批边界；
  无声预览按声明时长等比例解析，并固定留出 12 帧稳定阅读时间。旧字符串口播继续可预览
  可渲染，A 系列闸门对它们如实记为「跳过」；
- **视觉论证与全片预算（严格校验）**：`a2v/visual_narrative.py` 把逐幕声明与场景树结构
  对照分类——只承认九类**结构证据**：图表、图片、连接关系、圆周布局（≥ 2 个内容子节点），
  以及五个中层原语 `flow` / `cycle` / `timeline` / `gauge` / `pictogram`；
  布局原语、表面、形状、图标与单个数值都算包装或文字；`validate.py --strict` 因此执行
  文字幕不超过 `ceil(场景数 × 30%)`、相邻两幕不得都是文字幕、八幕及以上至少 3 种
  （少于八幕至少 2 种）非文字模式、声明非 `typography` 模式必须拿得出证据，
  失败定位到 `scenes[N].visualIntent.mode`。阈值版本化（`RULE_VERSION`）并由测试钉住；
  缺少新字段的旧分镜在普通校验里只给兼容警告，预览与渲染照常；
- **视觉原语注册表是唯一真源**：`web/src/registry/registry.json` 登记 21 个原语——
  布局 7（`stack` / `row` / `column` / `split` / `grid` / `radial` / `overlay`）、
  内容 5（`text` / `number` / `image` / `icon` / `chart`）、
  图形 4（`shape` / `surface` / `connector` / `group`），
  外加五个**中层原语**（`flow` / `cycle` / `timeline` / `gauge` / `pictogram`，
  按绘制方式归入 layout 与 content 两类）——
  以及各原语允许的属性、子节点容量、动效配方与支持的语义动作。
  `scripts/sync_catalog.py` 由它生成
  Python 校验器镜像（`a2v/catalog.py`）、TypeScript 枚举与属性/动效映射
  （`web/src/schema/primitiveTypes.ts`）和
  [原语目录](.agents/skills/article2video/references/primitive-catalog.md)
  （`--check` 可机检漂移）；校验器按注册表拒绝未知原语、超容量子节点、
  未注册属性、不支持的动效与不支持该动作的 beat 目标；
- **确定性渲染**：布局由离散受控参数（对齐、间距档、分栏比例、列数）经 CSS 确定性求解，
  不允许任意坐标或 transform 逃生口；相同分镜、字体、画布与帧号重复求值，
  节点几何与可见画面一致（测试钉住）。设计语言预设启用时，对声明了字号档（`role`）的
  文字原语按**实测宽度**向下取档，档位与是否实测记录在节点的
  `data-a2v-fit-role` / `data-a2v-fit-measured` 上，未启用预设不取档；
- **动效**：配方只有五种（`reveal` / `fade` / `rise` / `count` / `draw`），逐帧纯函数；
  目标用幕内唯一的节点 id 定位，配方与目标原语的匹配、时间范围是否落在场景内
  都在校验阶段确认，开渲前失败；
- **场景级代码双轨（v2.1）**：默认每幕仍走场景树；受控原语表达不了的图表面板、
  图形叙事可以在幕上声明 `renderer: { kind: "code", module: "…" }`，把整幕画面交给
  `scenes/` 下工作级 TSX 模块——模块默认导出 `(props) => ReactNode`，逐帧接收
  `progress`，用 `@a2v/scene` 的探针与适配层（ECharts/Dagre/Lucide/SVG 工具）保持
  确定性。依赖白名单（`react` / `remotion` / `echarts` / `@dagrejs/dagre` /
  `lucide-react`）、静态清单（构建前生成 `.gen/active-scenes.ts`）、安全门
  （挂钟/随机/定时器/网络/动态 import 等静态禁令）与运行期离线隔离（非本地请求
  一律阻断并计为错误）共同兜底；构建输入指纹覆盖当前作品可达源码与本地资产；
  `review.py --check-determinism` 做同帧重复截图与随机寻帧验收（PSNR ≥ 60 dB）。
  详见 [代码场景](.agents/skills/article2video/references/code-scenes.md) 与
  [示例](examples/code-scenes/storyboard.json)；
- **确定性渲染契约 `window.__A2V__`（version 2）**：由契约页
  `web/dist/contract/contract.html`（`pnpm -C web build` 产出）提供——它把 composition
  挂进 `@remotion/player`，从查询参数 `a2v-storyboard` 读分镜，因此一个页面服务任意作品。
  体检（帧量测、场景树契约探针）用 Playwright 驱动它；渲染不走它，而是直接从 composition
  源码打包渲染（Remotion）；
- **文章生成分镜**：按「内容分镜 → 视频级视觉策略 → 逐幕视觉转译 → 推理拆分与节拍编排
  → 场景树 → 动效 → 验收」分阶段执行，每阶段以前一阶段和原文为输入，可局部返工；
  视觉转译要求先声明受控视觉模式与
  无正文视觉表达，原语不足以表达时**停在转译阶段**（重新构思、扩展通用原语或用代码场景），
  不得改写成文字卡片后继续宣称原模式。步骤、约束、判据与正反例统一写在
  [文章生成分镜](.agents/skills/article2video/references/article-to-storyboard.md)；
  由 AI 工具按规范执行，仓库不含生成器程序，也不调用任何模型服务；
- **多样性检查**：`a2v/diversity.py` 为每幕计算**不含正文**的归一化布局指纹
  （树形、原语类别、分区比例、焦点象限、密度、意图关系、视觉模式与动效序列），
  在严格校验命令里报告相邻完全同构与片内过度复用；显式传 `--reference`
  提供参考分镜集合时才做跨作品比较，否则如实标记「未运行」；
- **旧分镜迁移**：`scripts/migrate_storyboard.py` 接受一个旧分镜路径与显式输出路径，
  保留内容、场景 id、口播与时长，保守映射为基础原语树并写迁移报告
  （不可靠映射标记人工重编排）；默认拒绝覆盖，迁移成功不等于验收通过；
- 渲染输出 1080 × 1920 / 30fps / H.264 `yuv420p` MP4（`--crf` 默认 18），
  渲染后自动解码验收帧数与分辨率；
- 码流按「各播放器都能播」的参数固定：画面 `yuv420p(tv, bt709)`、配音 AAC-LC
  44.1kHz 立体声；验收阶段会读回码流，命中全范围像素格式（`yuvj420p`）直接报错
  ——这类流 ffmpeg 能解码，但 Windows 的 Media Foundation 会以 `0xc00d36c4` 拒绝打开；
- 交付文件落盘后自动交回目标目录的继承权限：经临时目录中转的文件会带上「关闭继承」
  的 ACL，导致打包应用（Windows 11 新版媒体播放器）报 `0x80070005` 打不开成片；
- 成片带溯源：渲染成功后在同目录写 `<名字>.provenance.json`（version 4：画面来源
  `renderer`、分镜、**构建输入指纹**——composition 可达的全部源码、`package.json`
  与锁文件、字体——帧数分辨率帧率与渲染时刻），体检命令据此回答
  「这个成片是不是旧画面渲的」——`report.json` 的 `provenance` 段与终端一栏给出
  `对得上` / `落后（并指名是哪几个文件变了）` / `无法判断`。
  它是提示不拦人：不参与错误数，也不改退出码。为什么需要它：成片不入库，
  以前改了动效源码而没重渲，旧成片看上去仍然是「上次验收通过」的样子。
  溯源一律用相对引用（`workspace` + 工作区相对键，`web/` 下的构建输入记
  `/__a2v_web__/` 别名键），因此文章与产物放在仓库之外也读得回来；
- 可直接运行的完整示例（全部为 v2 场景树）：
  [`examples/narration-beats/`](examples/narration-beats/storyboard.json)
  （分段口播 + 语义节拍：5 幕覆盖 `flow` / `cycle` / `timeline` / `gauge` / `pictogram`，
  严格校验与 A1–A5、A7、A8 全部通过）、
  [`examples/cause-chain/`](examples/cause-chain/storyboard.json)
  （横向因果链构图：row + connector + radial，4 幕）、
  [`examples/milestone-climb/`](examples/milestone-climb/storyboard.json)
  （台阶与数据构图：column + chart + number + grid，4 幕）、
  [`examples/why-effort-fails/`](examples/why-effort-fails/storyboard.json)
  （5 幕）、[`examples/keynote-baseline/`](examples/keynote-baseline/storyboard.json)
  （8 幕，设计语言基线）、[`examples/declarative-number/`](examples/declarative-number/storyboard.json)、
  [`examples/code-scenes/`](examples/code-scenes/storyboard.json)
  （混合双轨：1 幕场景树 + 4 幕代码场景，覆盖 Tailwind/Lucide/ECharts/Dagre/定制 SVG）；
- edge-tts 中文自动配音、逐句字幕烧录与 SRT 导出；配音超时自动延长场景；
- 配音按场景缓存，统一 WAV 音轨支持预览播放、拖动和最终 AAC 合成；
- 目录约定与输出路径推导：每篇文章一个 `videos/<slug>/`，产物落在 `outputs/<slug>/`，
  示例产物独立在 `outputs/examples/<slug>/`；`--out` 与 `--out-dir` 可省略，
  显式参数继续优先；
- **文章与仓库解耦**：`videos/` 是作品内容，已在 `.gitignore` 中忽略（文章内容不入库）；
  文章与产物还可以整体放在仓库之外的**内容根**里，用 `--content-root` 或
  `A2V_CONTENT_ROOT` 指定（命令行优先），命令与产物结构完全不变。契约页与 composition
  在仓库 `web/` 下，渲染与体检按仓库根自动定位并用 `/__a2v_web__/` 别名挂载，
  内容根里不需要 skill 副本。不设内容根时工作区根就是仓库根；
- **发布会级设计语言层**（可选）：分镜根级声明 `visual.preset: "keynote"` 时启用
  `web/src/styles/keynote.css`——模块化字号阶（每档配对行高与字距）、
  8pt 间距阶、五个圆角档 + pill、三级阴影、12 列网格，以及 `keynote-dark`
  与 `keynote-light` 两套主题，对比度预算正文 7:1、大字与图形 4.5:1；
  **图形颜色按类别守预算**，`fill`/`stroke`/`background` 里不许出现字面色值，
  由 `tests/test_figure_contrast.py` 按分类表断言，新增 `--fig-*` 必须先归类；
  纯分隔线刻意保持耳语并豁免于 WCAG 1.4.11；
  Inter Variable 与 Noto Sans SC Variable（SIL OFL 1.1）随仓库分发、不走 CDN，
  由 `web/src/assets/fonts.json` 声明并在 `web/src/fonts.ts` 里于首帧前注册；
  预设作用域（未启用预设时画面不受预设影响）由
  `tests/test_react_design_tokens.py` 在浏览器里量计算值守住；
  参考实现见 [`examples/keynote-baseline/`](examples/keynote-baseline/storyboard.json)；
- **观感闸门 K1–K10**：`scripts/a2v/keynote.py` 把留白预算、强调色占比、同帧字号种类、
  对齐基线、正文对比度、卡片纪律、图形描边一致性量成数值结论，与回答「是不是废片」的
  C 系列**分开计分**；`review.py` 随体检一起输出，取不到样本的条目
  跳过并写明原因。
  其中 **K7 文字溢出与 K8 容器内溢出是硬判定**：文本块越出安全区（容差 8px）、
  或图形内的文字穿出它所属的容器（容差 2px，容器由 `data-a2v-inside` 声明）时，
  会并入体检的错误数与退出码，并报出是哪个文本块、往哪个方向越了多少像素。
  v2 的图表原语是 DOM/SVG 实现，K7/K8 对整幕生效，不存在量不到的 canvas 内部。
  阈值与设计取舍见
  [发布会级设计语言](.agents/skills/article2video/references/keynote-design-system.md)；
- **契约锚点**：场景树每个可渲染节点输出稳定的 `data-a2v-node-id` 与
  `data-a2v-primitive` 类型标记，契约探针按节点 id 核对「声明的内容真的画了出来」，
  动效按节点 id 量测——原语内部 DOM 结构调整不影响验收目标；
- 自动化测试：Python 侧覆盖 v2 校验、分段口播与节拍时间轴、媒体清单 `resolvedBeats`、
  A 系列动画论证闸门、迁移、多样性指纹、视觉叙事预算与 V 系列闸门、
  缓存与失败恢复、字幕时间轴、
  路径推导、契约页、取档行为、动效量测、渲染溯源与 Remotion 打包；
  web 侧（`pnpm -C web test`）覆盖 schema 校验、注册表自洽、场景树运行时纯函数
  与五个中层原语的 beat 状态。

尚未实现、请勿当作已有能力使用：**分镜生成器程序**（生成由 AI 工具按
[规范](.agents/skills/article2video/references/article-to-storyboard.md) 执行，没有内置生成服务、
模型调用或批量生成）、**背景音乐**、**内容根的自动探测**（只能显式指定，脚本不去猜）、
**平台发布**、批量渲染与成片历史版本。

设计语言层相关的未实现项同样不要当作已有能力：**视觉模型自动评审**（K 系列只给数值，
V5 只列候选与结构证据，V6 与 A6 的结论也由人填写，最终判断仍要人按
[评审量表](.agents/skills/article2video/references/visual-review-rubric.md) 完成）、
**按内容自动选预设**（必须由分镜显式声明），以及 K6 对「整幕没有卡片」只报跳过、
不判断「这一幕本该有卡片」。

## 快速开始

```bash
# 1. 安装依赖（首次）
uv sync
uv run playwright install chromium
pnpm -C web install
pnpm -C web build

# 2. 校验分镜（v2 场景树；--strict 把警告提升为失败）
uv run python .agents/skills/article2video/scripts/validate.py \
  examples/cause-chain/storyboard.json --strict --json

# 3. 本地预览（浏览器中确认节奏与排版；首次会自动构建契约页）
uv run python .agents/skills/article2video/scripts/preview.py \
  --storyboard examples/cause-chain/storyboard.json

# 4. 视觉评审（抽帧量测 + 场景树契约探针 + 观感闸门，产出联系表与 report.json）
uv run python .agents/skills/article2video/scripts/review.py \
  --storyboard examples/cause-chain/storyboard.json

# 5. 渲染（省略 --out 时输出到 outputs/examples/cause-chain/silent.mp4）
uv run python .agents/skills/article2video/scripts/render.py \
  --storyboard examples/cause-chain/storyboard.json

# 6. 测试
uv run pytest
pnpm -C web test
```

国内网络下安装较慢时可指定镜像：

```bash
UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple uv sync
PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright uv run playwright install chromium
```

## 自动配音与字幕

无声命令保持兼容。要输出有声视频，先按每幕口播（`narrationSegments` 分段口播，
或旧版的字符串 `narration`）准备媒体：

```bash
uv run python .agents/skills/article2video/scripts/prepare.py \
  --storyboard examples/cause-chain/storyboard.json

uv run python .agents/skills/article2video/scripts/preview.py \
  --storyboard examples/cause-chain/storyboard.json \
  --media outputs/examples/cause-chain/media/media.json

uv run python .agents/skills/article2video/scripts/render.py \
  --storyboard examples/cause-chain/storyboard.json \
  --media outputs/examples/cause-chain/media/media.json
```

省略 `--out-dir` 时媒体写入 `outputs/examples/cause-chain/media/`；省略 `--out` 时
无声导出为 `silent.mp4`，带 `--media` 则导出 `voiced.mp4` 和同名 `voiced.srt`。
加 `--limit-frames` 默认写入 `previews/`，不会覆盖正式成片。显式 `--out`、`--out-dir`
始终优先。

默认音色 `zh-CN-XiaoxiaoNeural`、语速 `+0%`；可用 `--voice`、`--rate=-10%` 调整，
`--force` 强制重新合成。首次合成需要联网，无需 API key；已有缓存可离线重新准备与导出。
输出 MP4 内含字幕和 AAC 配音，同时生成同名 SRT。背景音乐尚未实现。

原分镜不被覆盖；原场景时长作为最短时长，配音较长时自动延长并留 300ms 收尾。
声明了分段口播的幕还会在媒体清单里得到逐幕 `resolvedBeats`——画面、字幕与配音共用
这批边界，因此改过分段或时长后必须重新 prepare（旧清单里没有它时会被明确拒绝，
而不是拿旧缓存凑一个时间轴）。修改分镜后重新执行 prepare（未改变的口播命中缓存）。
详细接口和错误处理见
[配音与字幕](.agents/skills/article2video/references/media-contract.md)。

## 制作一支新视频

1. 新建文章目录 `videos/<slug>/`（slug 稳定、唯一，标题变化不改名），写入 `article.md`。
   目录留在仓库里即可——内容不入库，不会被提交；想放仓库外时把它放进
   内容根（`--content-root <目录>` 或环境变量 `A2V_CONTENT_ROOT`），内容根下同样放
   `videos/<slug>/`；
2. 按 [文章生成分镜](.agents/skills/article2video/references/article-to-storyboard.md)
   分阶段生成分镜：先内容分镜，再视觉策略与逐幕意图，然后把口播切成语义段并绑定 beat，
   最后按
   [原语目录](.agents/skills/article2video/references/primitive-catalog.md)
   组合场景树并绑定动效。默认**不写画面代码**——场景树够用时不需要它；
   受控原语确实表达不了时，按
   [代码场景](.agents/skills/article2video/references/code-scenes.md)
   为个别幕声明 `renderer.code` 并把模块放进作品的 `scenes/`；
3. 依次执行上面的校验、预览、渲染命令；`outputs/<slug>/` 由脚本自动推导
   （内容根在仓库外时即 `<内容根>/outputs/<slug>/`），无需手动创建。

手上只有旧版（`data.figure.kind`）分镜时，先显式迁移：

```bash
uv run python .agents/skills/article2video/scripts/migrate_storyboard.py \
  videos/<slug>/storyboard.json videos/<slug>/storyboard.v2.json
```

迁移结果必须通过严格校验、契约探针与视觉评审后才可替换旧分镜；
不可靠映射会在迁移报告里标记人工重编排。

已完成的文章：

| 目录 | 内容 | 分镜 | 成片（产物路径，不入库） |
| --- | --- | --- | --- |
| `videos/never-fear-interviews/`（不入库，作者本机） | 《永远不要害怕面试》 | 8 幕 / 2189 帧（73.0 秒） | `outputs/never-fear-interviews/voiced.mp4` + `.srt` |
| `videos/compound-interest-leverage/`（不入库，作者本机） | 《复利，才是普通人最强的杠杆》 | 10 幕 / 3572 帧（119.1 秒） | `outputs/compound-interest-leverage/voiced.mp4` + `.srt` |
| `examples/why-effort-fails/` | 《为什么努力没结果》（观感基线） | 5 幕 / 1350 帧（45 秒） | `outputs/examples/why-effort-fails/` |

上表里的成片路径是**推导出来的产物位置**，`outputs/` 不入库、也不随仓库分发。
三支文章均已随场景树架构更新为 v2 分镜；`examples/` 另有五支不同构图策略的
v2 示例可作为起点，其中
[`examples/narration-beats/`](examples/narration-beats/storyboard.json)
是分段口播与语义节拍的端到端参照。
《复利，才是普通人最强的杠杆》另附一份作品网页
（`videos/compound-interest-leverage/index.html`，不入库），把正文、成片、章节跳转与
口播全文放在同一页里互相对应。

目录结构与归属推导规则见
[目录约定与输出路径](.agents/skills/article2video/references/paths-and-outputs.md)；
分镜字段、渲染契约与排版规范见
[渲染契约](.agents/skills/article2video/references/render-contract.md)、
[分镜脚本结构](.agents/skills/article2video/references/storyboard-schema.md)、
[竖屏视觉规范](.agents/skills/article2video/references/visual-spec.md)。

## 视觉评审

`review.py` 一次跑完三层检查，产物落在 `outputs/<slug>/inspect/`：

- **场景树契约探针**：逐幕多处采样，按 `data-a2v-node-id` 读出画面里每个节点的实际文本，
  比对分镜声明的内容引用是否真的画了出来。「节点挂上了、画面也出来了，只是没有一个字」
  这类缺陷不会报错，只能靠读 DOM 发现——这正是它存在的理由；代码场景走**最小 DOM
  探针协议**（`data-a2v-node` / `-role` / `-inside` / `schematic`），协议缺失在严格评审里
  计为错误；加 `--check-determinism` 还会对每幕收尾帧做同帧重复截图与随机寻帧验收
  （PSNR ≥ 60 dB），失败计为错误；
- **帧量测**：墨迹覆盖率（防空幕、黑屏）与上下安全区的墨迹；动效量测（M0–M4）；
- **观感闸门 K1–K10**（声明 `visual.preset` 时）与**设计宪法静态检查**的适用部分：
  React 路径上静态结构检查明说跳过（画面由 composition 源码决定），由 web 侧
  源码扫描与运行时量测承担；
- **视觉叙事 V 系列**（`report.json` 的 `visualNarrative`）：V1 文字幕预算、V2 连续文字幕、
  V3 非文字模式覆盖、V4 声明与结构一致性——这四条与 `validate.py --strict` 同口径，
  失败并入错误数与退出码；V5 列出文字主导候选幕及判定证据（只呈现，由人逐条裁决）；
  V6 读 `review.md` 里人工填写的「图形承担论证」结论，**没填写就是「待评审」**，
  发布要求 V6 ≥ 4/5 且没有未裁决候选。语义结论不并入自动退出码；
- **动画论证 A 系列**（`report.json` 的 `animationReview`）：A1 节拍覆盖、A2 含义声明、
  A3 状态或关系变化、A4 字幕同步、A5 结尾停留、A7 单一焦点、A8 稳定结束——这七条
  只读分镜与媒体清单（不需要浏览器），失败并入错误数与退出码；A6 读 `review.md` 里
  人工填写的装饰动画裁决，**没填写就是「待评审」**，只拦 `publishable` 而不伪造脚本错误。
  只约束声明了 `narrationSegments` 的幕，旧字符串口播与无声预览下的 A4 如实记为「跳过」。

机检只保证「这不是废片」。**值不值得看完**按
[视觉评审量表](.agents/skills/article2video/references/visual-review-rubric.md)
六项 60 分制打分，≥ 40 才发布：[设计宪法](.agents/skills/article2video/references/design-constitution.md)
标明每条规则能不能机检——把审美也交给脚本，等于放弃质量。

Playwright 在本项目里的用途已收窄为**体检探针**：驱动契约页抽帧量测、读 DOM、
按帧验证画面。渲染不再经过浏览器截图。

## 关键约束

- **单一真源**：文案与原始时长写在 `storyboard.json`；分段口播的完整文本就是各段按顺序
  拼接，不另存一份；启用配音时，composition 和脚本
  共用媒体清单中的派生时长与逐幕 `resolvedBeats`；原语类型、属性、容量、动效与
  语义动作登记在 `registry.json`，
  生成物由 `sync_catalog.py` 同步（`--check` 机检漂移）；
- **帧驱动**：画面只由帧号推导（Remotion 的 `useCurrentFrame()`）。禁止 CSS
  `animation`/`transition`、`Date.now()`、`Math.random()`，否则逐帧渲染会闪烁且不可复现；
  web 侧测试与评审把守这条纪律；
- **受控表达**：分镜不携带 HTML、CSS、JavaScript、第三方包引用、任意表达式或
  任意坐标脚本；画面只能由原语注册表登记的节点类型与属性组合，校验器与
  契约探针双重把守；
- **产物归属**：一篇文章一个目录，产物只写进它自己的工作区根下 `outputs/<slug>/`；
  推导不出归属时脚本报错并要求显式指定路径或内容根，不猜测；
- **画质取舍**：渲染不产生中间帧文件，成片画质由 `--crf` 控制（默认 18）；
  画面避免大面积 `filter: blur()`，光晕用 `radial-gradient` 或 `box-shadow` 实现。

## 文档导航

- [项目规划](docs/PROJECT_PLAN.md)：处理链路、原语清单与阶段路线（未来方向的权威来源）
- [文章生成分镜](.agents/skills/article2video/references/article-to-storyboard.md)：分阶段生成流程、约束与校验闭环
- [协作约定](AGENTS.md)：中文协作、Git 与交付规则
- [Skill 主文档](.agents/skills/article2video/SKILL.md)：完整工作流与排查手册
- [分镜脚本结构](.agents/skills/article2video/references/storyboard-schema.md)：字段定义、分段口播与语义节拍、校验规则
- [配音与字幕](.agents/skills/article2video/references/media-contract.md)：媒体清单 version 2、逐幕 `resolvedBeats`、TTS 缓存与音轨合成
- [竖屏视觉规范](.agents/skills/article2video/references/visual-spec.md)：排版层级、景深、动效配方、语义动作与中层原语
- [视觉原语目录](.agents/skills/article2video/references/primitive-catalog.md)：有哪些原语、允许哪些属性、动效与语义动作、怎么组合
- [设计宪法](.agents/skills/article2video/references/design-constitution.md)：什么算做对了，以及哪条能机检
- [发布会级设计语言](.agents/skills/article2video/references/keynote-design-system.md)：`visual.preset` 的启用方式、字号阶与令牌、图形基元与状态、取档行为与 K1–K10 观感闸门
- [视觉评审量表](.agents/skills/article2video/references/visual-review-rubric.md)：六项评分、V6/A6 人工裁决写法与红线
- [目录约定与输出路径](.agents/skills/article2video/references/paths-and-outputs.md)：文章目录与产物位置规则

本仓库未配置远端，不含账号系统、云端任务队列或自动发布能力。
