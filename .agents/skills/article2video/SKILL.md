---
name: article2video
description: 把观点型文章制作成竖屏信息可视化短视频。AI 选择受控视觉组件并编写分镜，画面由共享 React composition（Remotion）按帧渲染，用确定性脚本导出 MP4。用于拆分镜、预览、渲染、验收与排查不一致问题。
---

# article2video

**文章是内容层，composition 是表现层，视频是最终发布格式。**

这个 skill 把「写文章 → 出视频」拆成一条可复现的流水线：AI 负责理解文章并选择组件、
编写分镜（`storyboard.json`）；共享 React composition 读取分镜逐幕挂载视觉组件；
脚本负责准备可选配音与字幕，并把 composition 确定性地渲染成 MP4。
AI 不直接生成视频，因此画面可控、可改、可重渲染。

## 何时使用

- 要把一篇观点型文章做成竖屏短视频；
- 要修改已有视频的画面、节奏或文案；
- 要渲染、验收视频，或排查「预览正常但导出异常」的问题。

如果只是写文章或做图文，不需要这个 skill。

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
6. **AI 做导演，不做设计师**：先看 [视觉组件目录](references/figure-catalog.md) 里有没有
   合适的组件，选一个、给几段短标注、指定节奏；只有目录里确实没有，才按注册表流程
   新写一个并沉淀回目录。每次从零画一遍既慢又容易失控，也难以保持一支视频内部的观感一致。
7. **先机检再人评**：`review.py` 负责保证「不是废片」（结构、契约、安全区、墨迹），
   人（或视觉模型）按 [评审量表](references/visual-review-rubric.md) 负责「值得看完」。
   把审美也交给脚本，等于放弃质量；反过来只靠眼睛，又会漏掉标签全空这类静默缺陷。

## 目录职责

| 路径 | 职责 |
| --- | --- |
| `web/src/compositions/` | 共享 composition：读分镜、逐幕挂载组件 |
| `web/src/components/` + `web/src/flow/`、`web/src/charts/` | 视觉组件本体（比喻组件、数据图表、关系流程图） |
| `web/src/registry/registry.json` | 组件集合的唯一真源：kind、标注键、容量、场景类型、默认映射 |
| `web/src/runtime/` | 帧驱动原语：动效配方、弹簧、排版、共享图形几何 |
| `web/src/styles/` | 设计令牌与组件样式 |
| `web/dist/contract/contract.html` | 渲染契约页（`pnpm -C web build` 的产物），体检用它驱动画面 |
| `.agents/skills/article2video/scripts/` | 校验、配音准备、预览、渲染、视觉评审五个命令行工具 |
| `.agents/skills/article2video/references/` | 渲染契约、分镜结构、视觉规范、组件目录、设计宪法、评审量表、目录与输出路径 |
| `examples/<slug>/` | 可直接运行的端到端示例（文章 + 分镜），作为新视频的起点 |
| `videos/<slug>/` | 每支实际视频一个目录：文章、分镜。**内容不入库**，见 `.gitignore` |
| `outputs/<slug>/` | 该文章的渲染产物，已被 `.gitignore` 忽略 |
| `outputs/examples/<slug>/` | 示例产物，独立一层避免与同名实际文章冲突 |

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
再落到 `outputs/<slug>/`。推导结果与执行命令时的工作目录无关；无法推导时脚本直接报错，
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

**按规范生成**：读 [文章生成分镜](references/article-to-storyboard.md)，它规定这一步的输入输出、
拆幕与时长规则、内容与排版约束、组件不足时的处理，以及生成后必须走完的校验闭环。
产物是 `videos/<slug>/storyboard.json`，字段与校验规则见
[分镜脚本结构](references/storyboard-schema.md)。

这一步由 AI 工具按规范执行；项目不含生成器程序，也不调用模型服务。

要点（完整清单见规范）：

- 先定位文章的核心判断，再按「开场命题 → 核心判断 → 对照/过程 → 结构模型 → 收束」拆幕；
- 场景时长由**口播所需时间**反推（30fps 下 1 秒 = 30 帧，中文口播每秒约 4–5 字）；
- 长句拆成多个场景，而不是缩小字号；
- 不虚构论据或数据；无来源的数值必须声明 `figure.schematic: true`；
- 生成后先过 `validate.py --declarative --strict --json`，按字段路径修正到通过再交付。

### 2. 分镜即画面声明

画面全部由共享 composition 提供，**不需要写任何页面代码**。
分镜以 `data.figure.kind` 选择组件（不写则按场景类型取注册表默认），
可选 `visual.theme`（`dark` / `light`）和场景 `visual.layout`（`center` / `lower`），
根级 `visual.preset`（目前唯一取值 `"keynote"`）启用发布会级设计语言：
设计语言层、排版引擎与观感闸门一起生效。说明见
[发布会级设计语言](references/keynote-design-system.md)。

当前有十个组件：八个比喻组件、数据图表 `chart`（柱状/折线/饼图）与关系流程图
`flow`（dagre 分层布局）。组件的适用内容、标注键与容量见
[视觉组件目录](references/figure-catalog.md)。

目录里确实没有合适的组件时，按 [组件契约](references/figure-catalog.md#组件契约)
在注册表登记并实现新组件（`registry.json` + 组件本体 + 生成命令 + 机检），
然后沉淀回目录——不要为某一支视频写专属画面代码。

### 3. 校验分镜

```bash
uv run python .agents/skills/article2video/scripts/validate.py videos/<slug>/storyboard.json
```

有错误时终止并列出 `scenes[2].data.items` 这类可定位的路径，修正后重跑。
加 `--json` 可得到机器可读输出，便于批量修正。
校验器还会按视觉规范给出**警告**（不阻止渲染）：单行字数超限、场景短于 24 帧、
`emphasis` 短语没有出现在文本里。定稿前用 `--strict` 把它们也当作失败。

### 3.1 配音与字幕准备（可选）

```bash
uv run python .agents/skills/article2video/scripts/prepare.py \
  --storyboard videos/<slug>/storyboard.json
```

省略 `--out-dir` 时媒体写入该文章的 `outputs/<slug>/media/`。
默认 edge-tts 中文晓晓音色，支持 `--voice`、`--rate=-10%`、`--force`。
生成 `media.json`、统一 WAV 和 SRT；音频较长的场景自动延长。无口播场景静音。
修改分镜后重新 prepare，缓存复用不变的配音。流程、缓存与失败处理见
[配音与字幕](references/media-contract.md)。无需将生成媒体加入 Git。

### 4. 预览（人工确认节奏与排版）

```bash
uv run python .agents/skills/article2video/scripts/preview.py \
  --storyboard videos/<slug>/storyboard.json
```

有声预览追加 `--media outputs/<slug>/media/media.json`。
预览由契约页驱动同一份 composition，因此预览看到的就是渲染会画出的画面。

浏览器打开后检查：中文无裁切、正文在安全区内、场景切换自然、重播结果一致。
**不要双击 HTML 预览**——契约页需要本地静态服务提供分镜与资源。

### 5. 渲染

```bash
uv run python .agents/skills/article2video/scripts/render.py \
  --storyboard videos/<slug>/storyboard.json
```

- 想给一支作品配更小的字体：`prepare.py --subset-fonts <源字体>` 会切出只含
  本作品用字的子集（落在 `outputs/<slug>/`，源字体只读），**切完立刻用缺字机检判它**
  ——漏字的子集会静默回退到系统字体，那正是要防的。这一步需要可选依赖
  （`uv sync --extra fonts`）：不装、不开这个开关时，默认链路完全离线可跑。
省略 `--out` 时无声导出为 `outputs/<slug>/silent.mp4`；
有声导出追加 `--media outputs/<slug>/media/media.json`，输出 `outputs/<slug>/voiced.mp4`
和同名 SRT。加 `--limit-frames` 时写入 `outputs/<slug>/previews/`，使用相同的成片文件名，
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
  [--media outputs/<slug>/media/media.json]
```

它一次跑完三件事，产物在 `outputs/<slug>/inspect/`：

1. **组件契约探针**（最有力）：逐幕在三处采样，读出当前画面里每个元素的实际文本，
   再比对分镜声明的标注有没有真的画出来。**「组件挂上了、画面也出来了，只是图上没有一个字」
   这类缺陷不会报错**，只有真的去读 DOM 才会发现，因此这一步不能省；
2. **帧量测**：墨迹覆盖率（防空幕、黑屏）与上下安全区的墨迹；
3. **观感与动效闸门**：声明了 `visual.preset` 时跑 K1–K10 观感闸门；
   M0–M4 动效闸门对任意作品都跑。

终端会打印错误与提醒，以及**需要人工判断的清单**。
机检只保证「这不是废片」；「值不值得看完」按
[视觉评审量表](references/visual-review-rubric.md) 打分，六项 60 分制、≥ 40 才发布。
评分标准见[设计宪法](references/design-constitution.md)（哪条能机检、哪条只能人看）。

体检结论分三串，**分开计数、不要混成一个总分**：

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
- 抽看首帧、每幕切换点、末帧，确认无空白帧、无文字裁切；
- 用系统默认播放器打开一次成片：全范围像素格式（`yuvj420p`）ffmpeg 能解码，
  但 Windows 播放器会报 `0xc00d36c4`；验收已会自动拦下，人工再确认一次最稳妥；
- 需要逐像素比对时，用同一帧重复渲染两次比对。

## 命令速查

四个入口都接受 `--content-root <目录>`（文章与产物放在仓库之外的内容根时使用；
也可以设环境变量 `A2V_CONTENT_ROOT`，命令行优先）。不设时工作区根就是仓库根。

```bash
# 校验分镜（有 --strict 把警告也视为失败）
uv run python .agents/skills/article2video/scripts/validate.py <storyboard.json> [--strict] [--json] [--media <media.json>]

# 本地预览（契约页驱动同一份 composition）
uv run python .agents/skills/article2video/scripts/preview.py --storyboard <json> [--port 8000] [--media <media.json>] [--content-root <目录>]

# 配音准备（省略 --out-dir 时写入 outputs/<slug>/media）
uv run python .agents/skills/article2video/scripts/prepare.py \
  --storyboard <json> [--out-dir <目录>] [--voice <音色>] [--rate=±N%] [--force] [--content-root <目录>] [-v]

# 视觉评审（省略 --out-dir 时写入 outputs/<slug>/inspect）
uv run python .agents/skills/article2video/scripts/review.py \
  --storyboard <json> [--media <media.json>] [--out-dir <目录>] [--content-root <目录>] [-v]

# 渲染（省略 --out 时按文章归属推导，限帧时写入 previews/）
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
| `组件 <kind> 尚未实现` 或 kind 报错 | 注册表里没有这个组件：查 [视觉组件目录](references/figure-catalog.md) 的可选值，或按组件契约新增 |
| `figure.kind 必须是注册表里的组件` | 分镜写了未知 kind：改成目录里已有的，或新增组件 |
| 成片有随机闪烁 | 画面里用了 CSS 动画或 `Date.now()`：组件必须由帧号推导（web 测试会拦） |
| 预览正常但导出缺字 | 用了系统字体而渲染机器上没有该字体，改为随仓库分发 webfont |
| 动画后段像卡住 | 场景被配音拉长后画面完全静止，入场结束后加常驻微动（`breath` 级别） |
| 画面扁平没有层次 | 缺少背景/表面/焦点三层：先加背景层与卡片内高光、双层投影（见视觉规范） |
| 强调色加在文案上却不生效 | `emphasis` 的短语没有原样出现在该场景文本里，`validate.py` 会给出警告 |
| 导出画面被裁切 | 画面尺寸超出 1080 × 1920，检查是否有元素溢出 |
| 渲染中途 ffmpeg 退出 | 尺寸为奇数（yuv420p 要求宽高为偶数），或磁盘空间不足 |
| 成片能解码但播放器打不开 | 码流是全范围像素格式（`yuvj420p`/`pc`）或 24kHz 单声道 AAC；验收阶段现已报错拦下，参数见 [渲染契约](references/render-contract.md) 的「码流兼容性」 |
| 播放器报 `0x80070005 你没有访问该文件的权限` | 成片经临时目录中转时带走了「关闭继承」的 ACL，打包应用（Windows 11 新版媒体播放器）读不到；`render.py`/`prepare.py` 会自动 `icacls /reset` 修复，见 [渲染契约](references/render-contract.md) 的「交付文件的访问权限」 |
| `无法推导文章归属` | 分镜不在 `videos/<slug>/`、`examples/<slug>/` 内：移入规范目录，或用 `--content-root`/`A2V_CONTENT_ROOT` 指定内容根，或显式指定输出路径 |
| `无法推导默认输出路径` | 省略 `--out` 但没有 `--storyboard`，补上分镜或显式指定 `--out` |
| 提示 narration 却按无声导出 | 没传 `--media`；先执行 `prepare.py`，再带 `--media` 渲染 |
| 体检溯源结论是 `stale` | web 源码在成片渲染之后改过：重新渲染一次成片 |

## 当前边界

已实现：分镜校验、自动配音与逐句字幕、React composition 画面（比喻组件 + 数据图表 +
关系流程图，组件注册表单源）、契约页体检（K/M 闸门与组件契约探针）、
Remotion 确定性渲染与成片验收、按文章目录推导输出路径、内容根（文章与产物可放在
仓库之外、`videos/` 不入库），以及设计语言预设（分镜声明 `visual.preset: "keynote"`
后启用令牌层、排版引擎与观感闸门）。

尚未实现，不要当作已有能力使用：

- **视觉模型自动评审**：K 系列只给出数值，最终判断仍要人（或视觉模型）按
  [视觉评审量表](references/visual-review-rubric.md) 完成；
- **webfont 子集化**：随仓库分发的 Noto Sans SC Variable 约 17MB，尚未做子集化；
- **按内容自动选预设**：预设必须由分镜显式声明；
- **自动拆场景**：引擎能算出「缩到正文下限仍放不下」并由 K7 报出来，
  但把一幕拆成两幕仍由人（或上游 AI）决定，脚本不代劳；
- **背景音乐**：尚未实现；目前仅支持配音音轨；
- **分镜生成器**：文章到分镜已可按 [文章生成分镜](references/article-to-storyboard.md) 的规范生成，
  但由 AI 工具执行，没有内置的生成器程序、模型调用或批量生成；
- **内容根的自动探测**：内容根只能由 `--content-root` 或 `A2V_CONTENT_ROOT` 指定，
  脚本不会去猜（猜错的后果是把成片写到你没在看的地方）；
- **发布**：没有对接抖音或任何平台的上传接口；
- **批处理与历史版本**：没有多篇批量渲染，也不保留成片历史版本。

## 参考文档

- [文章生成分镜](references/article-to-storyboard.md)：从文章产出分镜的步骤、约束、校验闭环与组件缺口处理
- [目录约定与输出路径](references/paths-and-outputs.md)：文章目录、归属推导与默认产物位置
- [配音与字幕](references/media-contract.md)：媒体清单、TTS 缓存、字幕与音轨合成
- [渲染契约](references/render-contract.md)：画面实现的 `__A2V__` 接口、渲染引擎与确定性要求
- [分镜脚本结构](references/storyboard-schema.md)：字段定义、已知场景类型与校验规则
- [竖屏视觉规范](references/visual-spec.md)：画布、安全区、排版层级、景深、动效配方与风格方向
- [发布会级设计语言](references/keynote-design-system.md)：`visual.preset` 的启用方式、字号阶与令牌、排版引擎、K1–K10 观感闸门与静默失效清单
