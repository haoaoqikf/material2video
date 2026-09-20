# article2video

将观点型文章转换成竖屏信息可视化短视频的个人内容生产项目。

**文章是内容层，画面工程是表现层，视频是最终发布格式。** 项目把抽象观点、因果关系和核心模型
转化为观众可以直观看到的思想结构。

## 这是什么

一个**项目级 Skill**：由 AI 编程工具（Codex、Claude Code、DSH 等）读懂文章并选择视觉组件，
写成分镜 JSON；画面由仓库 `web/` 里的共享 React composition（Remotion）按帧渲染成 MP4。
AI 不直接生成视频，因此画面可控、可改、可重渲染。

```text
文章 → 分镜 JSON → 配音与字幕准备（可选）→ React composition 逐帧渲染与音轨合成 → 竖屏 MP4
```

Skill 位于 [`.agents/skills/article2video/`](.agents/skills/article2video/SKILL.md)，
该目录被 Codex 与 DSH 直接识别；Claude Code 需要时可用软链接映射到 `.claude/skills/`。

## 当前状态

仓库已接入 [OpenSpec](openspec/config.yaml) 进行功能变更规划：`openspec/changes/` 存放进行中的提案、规格与任务，归档后的能力规格存放在 `openspec/specs/`，已完成的变更连同其提案、设计与逐轮实施记录留档在 `openspec/changes/archive/`。Codex 与 DSH 的工作流 Skill 位于 `.agents/skills/openspec-*/`。首次使用前需安装 OpenSpec CLI；在仓库根目录可用 `openspec list` 查看变更，以 `$openspec-propose` 发起新提案。

已完成**渲染器迁移**：画面从「作品自己的动画网页」整体迁到共享 React composition，
渲染默认走 Remotion（打包 → 元数据交叉校验 → 逐帧渲染 → 编码验收），旧页面、旧运行时
与逐帧截图路径已删除；`--page` / `--declarative` 等旧引擎参数已从命令行移除。

- 新视频只写 `article.md` 与 `storyboard.json`：composition 按分镜声明的组件、主题、布局与
  动效生成画面；示例见 [`examples/declarative-number/`](examples/declarative-number/storyboard.json)。
  需要共享组件表达不了的画面时，在作品目录写 `scenes.tsx` 专属画面模块，渲染脚本按工作区根
  自动发现并接进 composition；
- **组件注册表是唯一真源**：`web/src/registry/registry.json` 登记 10 个组件
  （天平 balance / 落差尺 gap / 冰山 iceberg / 飞轮 loop / 阶梯 stairs / 双向选择 exchange /
  双栏对照 versus / 数字 number / 图表 chart / 流程图 flow）的默认组件、场景类型、
  容量约束与标注键声明；`scripts/sync_catalog.py` 由它生成校验器目录、文档组件表与
  `web/src/schema/figureKinds.ts`（`--check` 可机检漂移）。分镜写 `data.figure.kind` 选组件、
  用 `labels` 给短标注、用 `figure.motion` 指定节奏；组件实现于 `web/src/components/`
  （图表在 `web/src/charts/`、流程图在 `web/src/flow/`），文案全部来自分镜。
  目录与新增组件的契约见
  [视觉组件目录](.agents/skills/article2video/references/figure-catalog.md)；
- **确定性渲染契约 `window.__A2V__`（version 2）**：由契约页
  `web/dist/contract/contract.html`（`pnpm -C web build` 产出）提供——它把 composition
  挂进 `@remotion/player`，从查询参数 `a2v-storyboard` 读分镜，因此一个页面服务任意作品。
  体检（帧量测、组件契约探针）用 Playwright 驱动它；渲染不走它，而是直接从 composition
  源码打包渲染（Remotion）；
- **动效配方层**（`web/src/runtime/motion.ts`、`spring.ts`）：入场、弹性、收敛、
  常驻微动与节奏换算都写在一处，组件用名字调用
  （`spring(seconds, SPRINGS['lively'])`，弹簧收的是秒数而不是缓存动过的进度），
  手感参数不会随组件漂移；Spring 曲线是阻尼谐振子闭式解，参数是物理量：
  `response`（自然周期，秒）与 `dampingFraction`（阻尼比 ζ）；
  动效原语全部是「按帧号求值的纯函数」，`web/src/runtime/motionDoc.test.ts` 把文档配方表
  逐值钉在 TS 常量上；量测实现只有一份（`scripts/a2v/motion.py`），验收命令 `review.py` 对
  **任意**作品给出同一套结论（`report.json` 的 `motion` 段，终端 M0–M4 一栏），
  动效结论与「不是废片」类错误分开计、不改退出码；
- **文章生成分镜**：从文章产出分镜的步骤、拆幕与时长规则、内容与排版约束、组件目录不足时
  的新增组件流程，以及生成后必须走完的校验闭环，统一写在
  [文章生成分镜](.agents/skills/article2video/references/article-to-storyboard.md)；
  由 AI 工具按规范执行，仓库不含生成器程序；
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
- 可直接运行的完整示例：[`examples/why-effort-fails/`](examples/why-effort-fails/storyboard.json)
  （5 幕，45 秒）、[`examples/keynote-baseline/`](examples/keynote-baseline/storyboard.json)
  （8 幕 / 68 秒，设计语言基线）、[`examples/declarative-number/`](examples/declarative-number/storyboard.json)；
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
- 一篇实际视频：`videos/never-fear-interviews/`（《永远不要害怕面试》，8 幕），
  八幕全部以帧驱动的比喻画面表达道理（天平 / 落差尺 / 冰山 / 飞轮 / 冰山 / 阶梯 /
  双栏对照 / 双向选择）。**这篇内容不入库**：
  它只存在于作者本机的内容目录里，克隆仓库看不到它，制作方法以 `examples/` 为准；
- **发布会级设计语言层**（可选）：分镜根级声明 `visual.preset: "keynote"` 时启用
  `web/src/styles/keynote.css`——模块化字号阶（10 档：28 / 34 / 40 / 60 / 76 / 96 / 120 / 140 /
  220 / 350px，每档配对行高与字距；排版引擎缩到 36px 正文下限即停）、
  8pt 间距阶（4–192px）、五个圆角档 + pill、三级阴影、12 列网格（内容宽 888px、
  槽宽 24px），以及 `keynote-dark`（bg `#08090c`、强调 `#32d6ff`）与
  `keynote-light`（bg `#eff1f4`、强调 `#0a6ad9`）两套主题，对比度预算正文 7:1、
  大字与图形 4.5:1；**图形颜色按五类分别守预算**（数据描边与图形内文本对画布 ≥ 4.5:1、
  边界描边对抬升面 ≥ 3:1、装饰描边 ≥ 1.5:1、面填充不设数值下限——形状由描边界定），
  `figures.css` 的 `fill`/`stroke`/`background` 里不许出现字面色值，均由
  `tests/test_figure_contrast.py` 按分类表断言，新增 `--fig-*` 必须先归类；
  纯分隔线刻意保持耳语并豁免于 WCAG 1.4.11；
  Inter Variable 与 Noto Sans SC Variable（SIL OFL 1.1）随仓库分发、不走 CDN，
  由 `web/src/assets/fonts.json` 声明并在 `web/src/fonts.ts` 里于首帧前注册；
  排版引擎 `web/src/runtime/typography.ts`（不属于渲染契约）：组件声明字号上限档位，
  composition 在预设生效时按**实测可用宽度**取档、按宽度均衡断行，到 36px 正文下限即停；
  行高、字距、字重仍归组件，字号归字阶。未声明的元素不会被改动；不声明 `preset` 时它不生效
  （样式受预设作用域约束、排版引擎不被调用）——预设作用域由
  `tests/test_react_design_tokens.py` 在浏览器里量计算值守住；
  字号阶的三方一致（文档表 / `SCALE` / `--a2v-size-*`）由
  `web/src/runtime/typographyDoc.test.ts` 守住；
  参考实现见 [`examples/keynote-baseline/`](examples/keynote-baseline/storyboard.json)；
- **观感闸门 K1–K10**：`scripts/a2v/keynote.py` 把留白预算、强调色占比、同帧字号种类、
  对齐基线、正文对比度、卡片纪律、图形描边一致性量成数值结论，与回答「是不是废片」的
  C 系列**分开计分**；`review.py` 随体检一起输出，取不到样本的条目
  跳过并写明原因。
  其中 **K7 文字溢出与 K8 容器内溢出是硬判定**：文本块越出安全区（容差 8px）、
  图形内的文字穿出它所属的容器（容差 2px，容器由组件用 `data-a2v-inside` 声明）、
  或排版引擎报「缩到正文下限仍放不下」时，会并入体检的错误数与退出码，
  并报出是哪个文本块/哪段文字、往哪个方向越了多少像素。
  K8 补的是 K7 量不到的那一格：K7 的参照只有安全区，而图形内按几何位置绘制的文字
  （飞轮节点、冰山标注、天平载物…）既不受安全区判定也不受容器判定。
  阈值与设计取舍见
  [发布会级设计语言](.agents/skills/article2video/references/keynote-design-system.md)；
- **组件级令牌与状态**：`figures.css` 的描边宽度、字重、字距、圆角、
  1px 边框、间距、内边距与 `margin-top` 全部走令牌（86 处引用，字面值清零），
  不在 8pt 阶上的取值一并改到阶上。`keynote.css` 另外定义了四个图形基元
  （`a2v-surface` / `a2v-label` / `a2v-connector` / `a2v-frame`）与四个状态
  （`rest` / `focus` / `muted` / `done`）；承载焦点与状态的元素
  （表面族、标签族、连接件族、边界框族）**全部**走「基元 + `data-a2v-state`」。
  连续量（`--a2v-focus-mix`、`--vs-heat`）与结构性类名（`is-left` / `is-right`）
  按设计**不进**四态；
- **容器内文字由内容测量决定几何**：装文字的容器（节点圆等）按实测文字宽度定形，
  而不是先写死尺寸再把字塞进去。参考示例的飞轮节点原先半径 76px 配 44px 的四字标签
  （约 183px，比直径还宽 31px），文字穿出圆而所有机检全绿，现在由 K8 守住；
- 自动化测试：Python 侧覆盖校验、缓存与失败恢复、字幕时间轴、路径推导、契约页、
  动效量测、渲染溯源与 Remotion 打包；web 侧（`pnpm -C web test`）覆盖组件几何、
  图表、流程图布局、注册表自洽、动效配方与文档机检。

尚未实现、请勿当作已有能力使用：**分镜生成器程序**（生成由 AI 工具按
[规范](.agents/skills/article2video/references/article-to-storyboard.md) 执行，没有内置生成服务、
模型调用或批量生成）、**背景音乐**、**内容根的自动探测**（只能显式指定，脚本不去猜）、
**平台发布**、批量渲染与成片历史版本。

设计语言层相关的未实现项同样不要当作已有能力：**视觉模型自动评审**（K 系列只给数值，
最终判断仍要人按
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

# 2. 校验分镜
uv run python .agents/skills/article2video/scripts/validate.py \
  examples/why-effort-fails/storyboard.json --declarative --strict --json

# 3. 本地预览（浏览器中确认节奏与排版；首次会自动构建契约页）
uv run python .agents/skills/article2video/scripts/preview.py \
  --storyboard examples/why-effort-fails/storyboard.json

# 4. 视觉评审（抽帧量测 + 组件契约探针 + 观感闸门，产出联系表与 report.json）
uv run python .agents/skills/article2video/scripts/review.py \
  --storyboard examples/why-effort-fails/storyboard.json

# 5. 渲染（省略 --out 时输出到 outputs/examples/why-effort-fails/silent.mp4）
uv run python .agents/skills/article2video/scripts/render.py \
  --storyboard examples/why-effort-fails/storyboard.json

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

无声命令保持兼容。要输出有声视频，先按每幕 `narration` 准备媒体：

```bash
uv run python .agents/skills/article2video/scripts/prepare.py \
  --storyboard examples/why-effort-fails/storyboard.json

uv run python .agents/skills/article2video/scripts/preview.py \
  --storyboard examples/why-effort-fails/storyboard.json \
  --media outputs/examples/why-effort-fails/media/media.json

uv run python .agents/skills/article2video/scripts/render.py \
  --storyboard examples/why-effort-fails/storyboard.json \
  --media outputs/examples/why-effort-fails/media/media.json
```

省略 `--out-dir` 时媒体写入 `outputs/examples/why-effort-fails/media/`；省略 `--out` 时
无声导出为 `silent.mp4`，带 `--media` 则导出 `voiced.mp4` 和同名 `voiced.srt`。
加 `--limit-frames` 默认写入 `previews/`，不会覆盖正式成片。显式 `--out`、`--out-dir`
始终优先。

默认音色 `zh-CN-XiaoxiaoNeural`、语速 `+0%`；可用 `--voice`、`--rate=-10%` 调整，
`--force` 强制重新合成。首次合成需要联网，无需 API key；已有缓存可离线重新准备与导出。
输出 MP4 内含字幕和 AAC 配音，同时生成同名 SRT。背景音乐尚未实现。

原分镜不被覆盖；原场景时长作为最短时长，配音较长时自动延长并留 300ms 收尾。
修改分镜后重新执行 prepare（未改变的口播命中缓存）。详细接口和错误处理见
[配音与字幕](.agents/skills/article2video/references/media-contract.md)。

## 制作一支新视频

1. 新建文章目录 `videos/<slug>/`（slug 稳定、唯一，标题变化不改名），写入 `article.md` 与
   `storyboard.json`。目录留在仓库里即可——内容不入库，不会被提交；想放仓库外时把它放进
   内容根（`--content-root <目录>` 或环境变量 `A2V_CONTENT_ROOT`），内容根下同样放
   `videos/<slug>/`；
2. 声明式路径到第 2 步就够（composition 按分镜画画面）；需要共享组件表达不了的构图时，
   在作品目录写 `scenes.tsx` 专属画面模块，参照 `examples/` 下各示例的场景模块，
   按 [竖屏视觉规范](.agents/skills/article2video/references/visual-spec.md) 的层级与动效配方改写；
3. 依次执行上面的校验、预览、渲染命令；`outputs/<slug>/` 由脚本自动推导
   （内容根在仓库外时即 `<内容根>/outputs/<slug>/`），无需手动创建。

已完成的文章：

| 目录 | 内容 | 分镜 | 成片（产物路径，不入库） |
| --- | --- | --- | --- |
| `videos/never-fear-interviews/`（不入库，作者本机） | 《永远不要害怕面试》 | 8 幕 / 2189 帧（73.0 秒） | `outputs/never-fear-interviews/voiced.mp4` + `.srt` |
| `examples/why-effort-fails/` | 《为什么努力没结果》（观感基线） | 5 幕 / 1350 帧（45 秒） | `outputs/examples/why-effort-fails/` |

上表里的成片路径是**推导出来的产物位置**，`outputs/` 不入库、也不随仓库分发。

`videos/never-fear-interviews/` 采用「编辑杂志」方向（浅底 + 墨黑衬线 + 单一朱红强调），
八幕全部**以形表意**：每一幕先用一个由帧驱动的比喻把道理画出来，文字只做注解。
比喻里的短标签（托盘名、水面、纵轴名等）全部来自分镜的 `figure.labels`，
composition 不保存任何默认文案；比喻本身由视觉组件提供。

`examples/why-effort-fails`（《为什么努力没结果》）已经用同一套组件、换一套设计令牌
重做：深色底、青色强调，五幕分别是 `balance` / `versus` / `versus` / `loop` / `exchange`。
同一套组件在浅色与深色两套主题下都成立，
这正是「AI 做导演，不做设计师」想达到的效果：换内容只需要改分镜。

目录结构与归属推导规则见
[目录约定与输出路径](.agents/skills/article2video/references/paths-and-outputs.md)；
分镜字段、渲染契约与排版规范见
[渲染契约](.agents/skills/article2video/references/render-contract.md)、
[分镜脚本结构](.agents/skills/article2video/references/storyboard-schema.md)、
[竖屏视觉规范](.agents/skills/article2video/references/visual-spec.md)。

## 视觉评审

`review.py` 一次跑完三层检查，产物落在 `outputs/<slug>/inspect/`：

- **组件契约探针**：逐幕多处采样，读出画面里每个元素的实际文本，比对分镜声明的标注
  是否真的画了出来。「组件挂上了、画面也出来了，只是图上没有一个字」这类缺陷不会报错，
  只能靠读 DOM 发现——这正是它存在的理由；
- **帧量测**：墨迹覆盖率（防空幕、黑屏）与上下安全区的墨迹；动效量测（M0–M4）；
- **观感闸门 K1–K10**（声明 `visual.preset` 时）与**设计宪法静态检查**的适用部分：
  React 路径上静态结构检查明说跳过（画面由 composition 源码决定），由 web 侧
  源码扫描与运行时量测承担。

机检只保证「这不是废片」。**值不值得看完**按
[视觉评审量表](.agents/skills/article2video/references/visual-review-rubric.md)
六项 60 分制打分，≥ 40 才发布：[设计宪法](.agents/skills/article2video/references/design-constitution.md)
标明每条规则能不能机检——把审美也交给脚本，等于放弃质量。

Playwright 在本项目里的用途已收窄为**体检探针**：驱动契约页抽帧量测、读 DOM、
按帧验证画面。渲染不再经过浏览器截图。

## 关键约束

- **单一真源**：文案与原始时长写在 `storyboard.json`；启用配音时，composition 和脚本
  共用媒体清单中的派生时长；组件、默认映射与容量约束登记在 `registry.json`，
  生成物由脚本同步；
- **帧驱动**：画面只由帧号推导（Remotion 的 `useCurrentFrame()`）。禁止 CSS
  `animation`/`transition`、`Date.now()`、`Math.random()`，否则逐帧渲染会闪烁且不可复现；
  web 侧测试与评审把守这条纪律；
- **手感只有一处**：入场、弹性、收敛、常驻微动这些决定「整支片子什么手感」的数字
  只写在 `web/src/runtime/motion.ts` 的配方表里，组件用名字调用，不写裸数字；
  `web/src/runtime/motionDoc.test.ts` 把文档与常量逐值对齐，防止配方改着改着变成弹跳；
  验收命令 `review.py` 对任意作品都会跑同一套量测（终端 M0–M4 一栏），
  但它只提示、不拦人——「入场快了一点」不是「画面坏了」；
- **产物归属**：一篇文章一个目录，产物只写进它自己的工作区根下 `outputs/<slug>/`；
  推导不出归属时脚本报错并要求显式指定路径或内容根，不猜测；
- **画质取舍**：渲染不产生中间帧文件，成片画质由 `--crf` 控制（默认 18）；
  画面避免大面积 `filter: blur()`，光晕用 `radial-gradient` 或 `box-shadow` 实现。

## 文档导航

- [声明式示例](examples/declarative-number/storyboard.json)：无需专属画面模块的分镜
- [项目规划](docs/PROJECT_PLAN.md)：处理链路、组件清单与阶段路线（未来方向的权威来源）
- [文章生成分镜](.agents/skills/article2video/references/article-to-storyboard.md)：从文章产出分镜的步骤、约束与校验闭环
- [协作约定](AGENTS.md)：中文协作、Git 与交付规则
- [Skill 主文档](.agents/skills/article2video/SKILL.md)：完整工作流与排查手册
- [竖屏视觉规范](.agents/skills/article2video/references/visual-spec.md)：排版层级、景深、动效配方与风格方向
- [视觉组件目录](.agents/skills/article2video/references/figure-catalog.md)：有哪些现成组件、怎么选、怎么新增
- [设计宪法](.agents/skills/article2video/references/design-constitution.md)：什么算做对了，以及哪条能机检
- [发布会级设计语言](.agents/skills/article2video/references/keynote-design-system.md)：`visual.preset` 的启用方式、字号阶与令牌（含组件级的描边 / 字重 / 字距 / 几何四族）、图形基元与状态、排版引擎与 K1–K10 观感闸门
- [视觉评审量表](.agents/skills/article2video/references/visual-review-rubric.md)：六项评分与红线
- [目录约定与输出路径](.agents/skills/article2video/references/paths-and-outputs.md)：文章目录与产物位置规则

本仓库未配置远端，不含账号系统、云端任务队列或自动发布能力。
