---
name: article2video
description: 把观点型文章制作成竖屏信息可视化短视频。AI 选择受控视觉组件并编写分镜，使用共享页面或专属动画网页，再用确定性脚本逐帧渲染为 MP4。用于拆分镜、预览、渲染、验收与排查不一致问题。
---

# article2video

**文章是内容层，网页是表现层，视频是最终发布格式。**

这个 skill 把「写文章 → 出视频」拆成一条可复现的流水线：AI 负责理解文章并选择组件，必要时编写专属动画网页，
脚本负责准备可选配音与字幕，并把网页确定性地渲染成 MP4。AI 不直接生成视频，因此画面可控、可改、可重渲染。

## 何时使用

- 要把一篇观点型文章做成竖屏短视频；
- 要修改已有视频的画面、节奏或文案；
- 要渲染、验收视频，或排查「预览正常但导出异常」的问题。

如果只是写文章或做图文，不需要这个 skill。

## 核心原则

1. **单一真源**：文案与时长只写在 `storyboard.json`，网页读它绘制，渲染脚本读它推导总帧数。
   不要在 HTML 里再写一遍文案。启用配音后，实际时长由独立媒体清单派生，网页和渲染脚本共用它，不覆盖原分镜。
2. **帧驱动**：画面只由帧号推导得出。禁止 CSS `animation`/`transition`、`Date.now()`、
   `Math.random()`，否则逐帧截图会闪烁、不可复现。详见
   [渲染契约](references/render-contract.md)。
3. **先校验再渲染**：分镜脚本先过 `validate.py`，网页契约先过渲染脚本的前置检查，
   错误在开渲前暴露，而不是产出一段坏视频。
4. **预览与导出同源**：预览和渲染使用同一份 storyboard、同一套坐标，只缩放不改布局。
5. **层级先于装饰**：先做出背景 / 表面 / 焦点三层与统一的动效曲线，再考虑细节；
   「高级感」来自克制的层级与一致的节奏，而不是更多的颜色和更大的动效。
6. **AI 做导演，不做设计师**：先看 [视觉组件目录](references/figure-catalog.md) 里有没有
   合适的组件，选一个、给几段短标注、指定节奏；只有目录里确实没有，才按组件契约新写一个
   并沉淀回目录。每次从零画一遍既慢又容易失控，也难以保持一支视频内部的观感一致。
7. **先机检再人评**：`review.py` 负责保证「不是废片」（结构、契约、安全区、墨迹），
   人（或视觉模型）按 [评审量表](references/visual-review-rubric.md) 负责「值得看完」。
   把审美也交给脚本，等于放弃质量；反过来只靠眼睛，又会漏掉标签全空这类静默缺陷。

## 目录职责

| 路径 | 职责 |
| --- | --- |
| `.agents/skills/article2video/assets/` | 基础样式 `base.css`、设计令牌 `theme.css`、时间轴运行时 `timeline.js`、视觉组件库 `figures.css` + `figures.js` |
| `.agents/skills/article2video/scripts/` | 校验、配音准备、预览、渲染、视觉评审五个命令行工具 |
| `.agents/skills/article2video/references/` | 渲染契约、分镜结构、视觉规范、组件目录、设计宪法、评审量表、目录与输出路径 |
| `examples/why-effort-fails/` | 可直接运行的端到端示例，作为新视频的起点 |
| `videos/<slug>/` | 每支实际视频一个目录：文章、分镜；专属网页按需添加 |
| `.agents/skills/article2video/assets/declarative.html` | 声明式路径的共享页面；新视频可只保留文章与分镜 |
| `outputs/<slug>/` | 该文章的渲染产物，已被 `.gitignore` 忽略 |
| `outputs/examples/<slug>/` | 示例产物，独立一层避免与同名实际文章冲突 |

每篇文章的目录名（slug）稳定且唯一，标题变化不改目录名；源文件纳入 Git，产物统一放
`outputs/`。完整结构与推导规则见 [目录约定与输出路径](references/paths-and-outputs.md)。

`.agents/skills/` 是 Codex 与 DSH 都能识别的项目级 skill 位置；
Claude Code 需要该目录时可用软链接映射到 `.claude/skills/`。

## 标准流程

所有命令都在**仓库根目录**执行。输出路径可以省略：脚本从输入文件位置向上找到项目根，
再按 `videos/<slug>/` 或 `examples/<slug>/` 推导出 `outputs/<slug>/`，
推导结果与执行命令时的工作目录无关。无法推导时脚本直接报错，不会猜测归属。

### 0. 准备环境

```bash
uv sync                                              # 安装 Python 依赖
uv run playwright install chromium                   # 首次执行，安装浏览器
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
- 不虚构论据或数据；无来源的数值必须在画面中标明为示意；
- 生成后先过 `validate.py --declarative --strict --json`，按字段路径修正到通过再交付。

### 2. 分镜 → 动画网页

优先考虑声明式路径：若现有组件足以表达，分镜以 `data.figure.kind` 选择组件，
可选 `visual.theme`（`dark` / `light`）和场景 `visual.layout`（`center` / `lower`），
无需新建 `index.html`。运行：

```bash
uv run python .agents/skills/article2video/scripts/validate.py videos/<slug>/storyboard.json --declarative --strict
uv run python .agents/skills/article2video/scripts/preview.py --declarative --storyboard videos/<slug>/storyboard.json
uv run python .agents/skills/article2video/scripts/render.py --storyboard videos/<slug>/storyboard.json
```

当前有八个组件，包含基础 `number`。声明式模式拒绝未知组件与未支持的参数；
完整字段见 [分镜脚本结构](references/storyboard-schema.md)，仅含文章与分镜的示例在
`examples/declarative-number/`。需要目录外的特殊构图时，继续使用下述专属网页路径。

复制示例作为起点：

```bash
cp -r examples/why-effort-fails videos/<slug>
```

目录名保持稳定：文章标题后来变了也只改 `article.md` 与分镜里的 `title`，不改目录名，
否则产物会分裂到两个 `outputs/` 目录下。

然后改写 `videos/<slug>/index.html`：

- 保留 `<link>` 引入的 `base.css` 与 `<script>` 引入的 `timeline.js`
  （相对路径按所在层级调整），它们提供画布、安全区与 `__A2V__` 契约；
- 再引入 `theme.css`（设计令牌 + 光晕/网格/细点阵背景层）；顺序必须是
  `base.css` → `theme.css` → 页面自身样式，让页面拥有最终覆盖权；
- 每个场景一个 `<section data-a2v-scene data-scene-id="<场景 id>">`，
  `data-scene-id` 必须与 storyboard 中的 `id` 一致；
- 所有正文放进 `.a2v-safe` 安全区；背景层放在舞台内、场景容器之外并置 `z-index: 0`，
  场景容器置 `z-index: 1`；
- **不画图形**：每幕放一个 `<div class="a2v-safe" data-a2v-figure></div>` 挂载点，
  画面交给组件库；在 `renderFrame` 里只写一句
  `A2V.figures.renderScene(state, api, { defaults: DEFAULT_FIGURES })`，
  `DEFAULT_FIGURES` 把场景类型映射到组件（`comparison` → `versus` 等）；
- 要新画图形时先查 [视觉组件目录](references/figure-catalog.md)：有合适的就选它、
  给几段短标注；确实没有才按组件契约新写一个，并沉淀回目录；
- 页面自己只保留「舞台 + 常驻背景 + 每幕的挂载点 + 场景角标」这四件事；
- 播放控件放在 `[data-a2v-controls]` 或加 `a2v-preview-only` 类，导出时会被隐藏。

排版层级、动效配方与三套风格方向见 [竖屏视觉规范](references/visual-spec.md)；
`examples/why-effort-fails/index.html` 是**只声明挂载点**的完整范例（深色主题），
`videos/never-fear-interviews/index.html` 是同一套组件换成浅色主题的范例，
两者可以直接对照抄用。

引入 `figures.css` 时注意：组件库的墨色由 `--fig-line` / `--fig-ink` /
`--fig-surface` 等令牌决定（`theme.css` 已给深色默认值）。页面若换主题，
必须一并覆盖这几个令牌，否则图形不报错、只是安静地变成透明。

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
uv run python .agents/skills/article2video/scripts/preview.py videos/<slug>
```

有声预览追加 `--media outputs/<slug>/media/media.json`。网页须使用 `A2V.fetchStoryboard()`
加载分镜，并在 mount 后等待 `__A2V__.ready()`；它会加载统一媒体时间轴和字幕。

浏览器打开后检查：中文无裁切、正文在安全区内、场景切换自然、重播结果一致。
**不要双击 HTML 预览**——`file://` 下取不到 storyboard.json，页面会报错。

### 5. 渲染

```bash
uv run python .agents/skills/article2video/scripts/render.py \
  --page videos/<slug>/index.html \
  --storyboard videos/<slug>/storyboard.json
```

省略 `--out` 时无声导出为 `outputs/<slug>/silent.mp4`；
有声导出追加 `--media outputs/<slug>/media/media.json`，输出 `outputs/<slug>/voiced.mp4`
和同名 SRT。加 `--limit-frames` 时写入 `outputs/<slug>/previews/`，使用相同的成片文件名，
不会覆盖正式成片。显式 `--out` 仍然优先。

输出包含 AAC 配音和烧录字幕，并生成同名 SRT；限帧会同步裁切音轨和字幕。
成片的画面固定为 `yuv420p(tv, bt709)`、配音固定为 AAC-LC 44.1kHz 立体声，
由编码器统一保证，网页不需要也不应该干预。

先用 `--limit-frames 30` 快速跑通链路再全量渲染。渲染脚本会：

1. 在 127.0.0.1 起临时静态服务（网页需要 fetch 分镜 JSON）；
2. 校验网页契约与分镜的 fps、总帧数是否一致，不一致直接报错；
3. 加 `a2v-rendering` 类隐藏预览控件、取消预览缩放；
4. 逐帧 `seekToFrame(frame)` → 截图 → 送入 ffmpeg 管道；
5. 完整解码一遍成片，核对帧数与分辨率，并检查码流是否为播放器友好的格式。

耗时参考：1080 × 1920、30fps 下实测约 11–16 帧/秒，45 秒视频（1350 帧）约 1.5–2 分钟；
成片验收会额外完整解码一遍，约增加 2 秒。

### 6. 视觉评审（渲染前后都该做）

```bash
uv run python .agents/skills/article2video/scripts/review.py \
  --page videos/<slug>/index.html \
  --storyboard videos/<slug>/storyboard.json \
  --media outputs/<slug>/media/media.json
```

声明式视频（没有专属网页）省掉 `--page`，改用 `--declarative`：

```bash
uv run python .agents/skills/article2video/scripts/review.py \
  --declarative --storyboard videos/<slug>/storyboard.json
```

此时场景由共享页面在运行时生成，依赖源码的三项静态检查（场景层、挂载点、文案单一真源）
会被跳过，改由运行时探针给出结论；产物仍写入 `outputs/<slug>/inspect/`。

它一次跑完三件事，产物在 `outputs/<slug>/inspect/`：

1. **组件契约探针**（最有力）：逐幕在三处采样，读出当前挂载点里每个元素的实际文本，
   再比对分镜声明的标注有没有真的画出来。**「组件挂上了、画面也出来了，只是图上没有一个字」
   这类缺陷不会报错**，只有真的去读 DOM 才会发现，因此这一步不能省；
2. **帧量测**：墨迹覆盖率（防空幕、黑屏）与上下安全区的墨迹；
3. **设计宪法静态检查**：结构、曲线纪律、模糊、挂载点、文案单一真源、安全区。

终端会打印错误与提醒，以及**需要人工判断的清单**。
机检只保证「这不是废片」；「值不值得看完」按
[视觉评审量表](references/visual-review-rubric.md) 打分，六项 60 分制、≥ 40 才发布。
评分标准见[设计宪法](references/design-constitution.md)（哪条能机检、哪条只能人看）。

### 7. 渲染验收

- 渲染脚本最后一行输出帧数、时长、分辨率、实测帧率与文件大小；
- 抽看首帧、每幕切换点、末帧，确认无空白帧、无文字裁切；
- 用系统默认播放器打开一次成片：全范围像素格式（`yuvj420p`）ffmpeg 能解码，
  但 Windows 播放器会报 `0xc00d36c4`；验收已会自动拦下，人工再确认一次最稳妥；
- 需要逐像素比对时用 `--capture-format png` 重渲一次。

## 命令速查

```bash
# 校验分镜（有 --strict 把警告也视为失败）
uv run python .agents/skills/article2video/scripts/validate.py <storyboard.json> [--strict] [--json] [--media <media.json>]

# 本地预览
uv run python .agents/skills/article2video/scripts/preview.py <目录> [--page index.html] [--port 8000] [--media <media.json>] [--storyboard <json>]

# 配音准备（省略 --out-dir 时写入 outputs/<slug>/media）
uv run python .agents/skills/article2video/scripts/prepare.py \
  --storyboard <json> [--out-dir <目录>] [--voice <音色>] [--rate=±N%] [--force] [-v]

# 视觉评审（省略 --out-dir 时写入 outputs/<slug>/inspect）
uv run python .agents/skills/article2video/scripts/review.py \
  --page <网页> --storyboard <json> [--media <media.json>] [--out-dir <目录>] [-v]

# 渲染（省略 --out 时按文章归属推导，限帧时写入 previews/）
uv run python .agents/skills/article2video/scripts/render.py \
  --page <网页> [--storyboard <json>] [--out <输出.mp4>] [--limit-frames N] \
  [--media <media.json>] [--capture-format jpeg|png] [--crf 18] [--preset medium] [--no-probe] [-v]
```

## 排查常见问题

| 现象 | 原因与处理 |
| --- | --- |
| `window.__A2V__ 未定义` | 网页没有引入 `timeline.js`，或 `A2V.mount()` 抛错（看控制台） |
| `分镜脚本加载失败: HTTP 404` | 网页里 `fetchStoryboard('storyboard.json')` 的相对路径不对，或预览时用了 `file://` |
| `总帧数不一致` | 改了 storyboard 的时长但没重新加载页面，或网页里硬编码了总帧数 |
| 成片有随机闪烁 | 画面里用了 CSS 动画或 `Date.now()`，改为由帧号推导；渲染前会静态提示 `animation:` / `transition:` / `@keyframes` |
| 预览正常但导出缺字 | 用了系统字体而渲染机器上没有该字体，改为随仓库分发 webfont |
| 动画后段像卡住 | 场景被配音拉长后画面完全静止，入场结束后叠 `api.breath()` 级别的常驻微动 |
| 画面扁平没有层次 | 缺少背景/表面/焦点三层：先加背景层与卡片内高光、双层投影（见视觉规范） |
| 强调色加在文案上却不生效 | `emphasis` 的短语没有原样出现在该场景文本里，`validate.py` 会给出警告 |
| 导出画面被裁切 | 文档尺寸超出 1080 × 1920，检查是否有元素溢出或页面出现滚动条 |
| 渲染中途 ffmpeg 退出 | 尺寸为奇数（yuv420p 要求宽高为偶数），或磁盘空间不足 |
| 成片能解码但播放器打不开 | 码流是全范围像素格式（`yuvj420p`/`pc`）或 24kHz 单声道 AAC；验收阶段现已报错拦下，参数见 [渲染契约](references/render-contract.md) 的「码流兼容性」 |
| 播放器报 `0x80070005 你没有访问该文件的权限` | 成片经临时目录中转时带走了「关闭继承」的 ACL，打包应用（Windows 11 新版媒体播放器）读不到；`render.py`/`prepare.py` 会自动 `icacls /reset` 修复，见 [渲染契约](references/render-contract.md) 的「交付文件的访问权限」 |
| 画面里出现播放控件 | 控件没放在 `[data-a2v-controls]` 内，也没加 `a2v-preview-only` 类 |
| `无法推导文章归属` | 网页或分镜不在 `videos/<slug>/`、`examples/<slug>/` 内，移入规范目录或显式指定输出路径 |
| `无法推导默认输出路径` | 省略 `--out` 但没有 `--storyboard`，补上分镜或显式指定 `--out` |
| 提示 narration 却按无声导出 | 没传 `--media`；先执行 `prepare.py`，再带 `--media` 渲染 |

## 当前边界

已实现：分镜校验、自动配音与逐句字幕、动画网页契约、有声/无声预览、逐帧渲染与成片验收、
按文章目录推导输出路径。

尚未实现，不要当作已有能力使用：

- **背景音乐**：尚未实现；目前仅支持配音音轨；
- **分镜生成器**：文章到分镜已可按 [文章生成分镜](references/article-to-storyboard.md) 的规范生成，
  但由 AI 工具执行，没有内置的生成器程序、模型调用或批量生成；
- **发布**：没有对接抖音或任何平台的上传接口；
- **批处理与历史版本**：没有多篇批量渲染，也不保留成片历史版本。

## 参考文档

- [文章生成分镜](references/article-to-storyboard.md)：从文章产出分镜的步骤、约束、校验闭环与组件缺口处理
- [目录约定与输出路径](references/paths-and-outputs.md)：文章目录、归属推导与默认产物位置
- [配音与字幕](references/media-contract.md)：媒体清单、TTS 缓存、字幕与音轨合成
- [渲染契约](references/render-contract.md)：网页必须实现的 `__A2V__` 接口与确定性要求
- [分镜脚本结构](references/storyboard-schema.md)：字段定义、已知场景类型与校验规则
- [竖屏视觉规范](references/visual-spec.md)：画布、安全区、排版层级、景深、动效配方与风格方向
