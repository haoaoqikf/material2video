## Context

vibe-knowledge-film 的 C 夜曲（夜曲）是已登记外部参考项目（固定提交 `62d51508aad00003dc6209afa80c4b5dc540de59`，2026-10-13）的两套外观之一。现有仓库已具备风格包机制：`styles/<id>/style.json` 是唯一注册来源，`core/styles.py` 负责清单校验、越界拒绝与内容指纹，general 场景可通过 `m2v/style` 读取 tokens 并显式导入登记组件和资产（[风格接入契约](../../.agents/skills/material2video/references/style-pack.md)）。但当前 `styles/` 为空，`style-registry` 规格明确"首期不包含正式风格"。

同时存在两个能力缺口：general 的字幕层只从 `narrationSegments` 经 TTS 派生，无旁白作品没有屏幕文字；现有视觉规范是镜头级，缺少 C 夜曲赖以成立的"逐句画法"。

本变更按已确认的三项决策执行：不动固定示例（C1）、屏幕字幕由作品自绘（B1）、先落地 C 夜曲。

## Goals / Non-Goals

**Goals:**

- `styles/vibe-night` 成为可查询、可选、可参与准备指纹与缓存失效的正式风格包。
- 用仓库自己的 TSX 组件还原 C 夜曲的可迁移部分：底色与光池、光点母题、章节标、点阵片名卡、数轴、闪与暗一下、辉光与颗粒。
- 补齐 C 夜曲依赖的宋体资产，并随包登记来源与 OFL 许可。
- 为无旁白知识片建立屏幕字幕约定，使"字幕即文案"在不改共享字幕层和分镜 schema 的前提下可用。
- 形成一份可执行的讲解设计文档，并接入 general 制作入口。
- 用一条不入库的原创试制片验证风格与约定，留下八项指标、并排基准与独立冷审证据。

**Non-Goals:**

- 不做 B 寓言；不替换三个固定示例；不新增视频类型或 CLI 命令。
- 不改 `web/src/frames.json` 共享字幕层，不改 v8 分镜 schema，不改制作门、审核轮次或导出门禁。
- 不移植外部 `engine/`、`film.js`、GIF/JPG、字幕系统或样片角色；不复制参考片的画面、文案与分镜。
- 不引入 Cormorant/Lora/JetBrains Mono 等西文展示字体；西文先用现有 Inter，观感差异写入 GUIDE。

## Decisions

### 1. 只做 C 夜曲，B 寓言另行评估

C 夜曲对"画"的要求最低、对"想"的要求最高，组件可复用性最好；B 寓言每场要画插画与角色，工作量约为 C 的两倍，且需要另建角色与视差组件。先验证风格包机制与屏幕字幕约定，再决定 B 是否值得做。边界不明确的部分按 OpenSpec 另行登记，不在本变更扩大范围。

### 2. 组件用 TSX 与 SVG 重写，不移植引擎

C 夜曲的核心不是 Canvas 引擎，而是数值规格与观看方式。组件基于 `m2v/code-scene` 的受控时钟与现有原语实现：

- `night-backdrop`：`#010104` 底、中央 `#0B1830` 光池、固定种子星点、暗角；星点数量与亮度可参数化。
- `spark` / `comet`：小白核 + 两层色晕的光点母题，彗尾用渐变描边。
- `glow-text`：字自身辉光；用 SVG `feGaussianBlur` 或文字阴影实现，不使用 WebGL 后期。
- `chapter-mark`：左上章节标（编号 + 单字 + 西文 + 细线）。
- `title-night`：点聚成字的片名卡，按本地时间推进。
- `flash` / `dip`：闪白与章间暗一下。
- `number-line`：带刻度的数轴，返回数值到坐标的映射。

辉光与暗角优先用 SVG filter 与径向渐变；粒子超过数百个时改用原生 canvas，避免逐帧滤镜开销。不使用 `Math.random`、挂钟或 CSS 动画，全部由帧号与固定种子驱动。`PostFX` 仍可供作品自行选择的 WebGL 场景使用，但不作为本风格包的唯一后期依赖。

### 3. 字体作为风格包资产，不改全局字体清单

C 夜曲的主体大字依赖宋体。新增 Noto Serif SC（OFL）woff2 作为包内资产，在 `style.json` 声明 `source` 与 `license`，组件通过 `m2v/style/assets/*` 取得 URL 后显式加载，场景在字体就绪后调用 `ready()`。全局 `web/src/assets/fonts.json` 与字幕层字体不因此改变。

体积控制：优先使用官方可变字体或按常用字表子集化的 woff2；包内保留 OFL 许可全文。试制片必须验证正文用字无回退字体（字体 cmap 检查 + 原尺寸帧复核），缺字视为未完成。

### 4. 屏幕字幕由作品自绘（B1）

无旁白作品在 `content.props` 声明屏幕文字（约定字段名 `screenSubtitles`，每项含 `startFrame`、`endFrame`、`text`），由作品场景在 `subtitleSafeArea` 内绘制。约定：

- 一行，不换行；C 夜曲中文不超过 28 字，超出拆句；
- 无底板、水平居中，字号与基线按 tokens，颜色语义与全片一致；
- 共享字幕层在无旁白时为空，不冲突；有旁白作品继续使用共享层，不读取 `screenSubtitles`；
- 这不是产品级字幕：不进入 `subtitleCues`、不参与字幕安全区量测与缺字扫描的自动报告。试制片用帧序列、原尺寸截图与独立评审补足，并在验证记录中披露该限制。

选择 B1 而非新增 schema，是为了先验证观感与制作流程；若试制片证明需要时间轴级校验，再另开变更升级为产品级字幕。

### 5. 讲解设计文档接在现有入口，不新增门禁

新增 `.agents/skills/material2video/references/explainer-design.md`，内容限定为：六种画法、找形象决策树、三问、五分之一不画、数量可数化、无旁白字幕稿的量与句式、看图改图的检查表。它被 `article-to-storyboard.md` 与 `visual-review-rubric.md` 引用，作为 general 讲解片的制作与自查依据，不改变检查点门、审核人数或完成条件。

### 6. 试制片是验收证据，不是固定示例

在 `videos/general/<slug>/` 制作一条 30–45 秒原创 C 夜曲短片，选题与事实表在作品内确定，不使用 `fold_C`、`pigeon_B` 的主题、形象与文案。作品内容按 `.gitignore` 不入库；仓库只提交风格包、文档、测试与验证记录。验收证据包括：八项指标表、并排基准、原尺寸与 393 宽截图、完整动态窗口、独立冷审结论。

### 7. 规格与登记同步

- `style-registry` 规格从"首期不包含正式风格"改为登记 `vibe-night`，保留"无风格作品仍可用"。
- 新增 `vibe-night-style` 规格描述该包的可验证行为。
- [外部参考项目登记](../../.agents/skills/material2video/references/external-projects.md) 中 `vibe-knowledge-film` 的状态从"临时登记"更新为"已作为风格包落地 C 夜曲"，B 寓言仍保持未并入。

## Risks / Trade-offs

- [宋体资产体积过大] → 使用子集化 woff2 并保留完整许可；以试制片实际用字验证覆盖，缺字即失败。
- [SVG 滤镜在 1080p 逐帧录制下变慢] → 限制每帧滤镜数量，大面积柔光改用径向渐变；粒子改 canvas；必要时降低星点密度。
- [屏幕字幕不受产品级校验，可能出错字或越界] → 在试制片用帧序列、原尺寸截图、安全区量测与独立评审逐项复核，并在验证记录中写明限制；若问题反复，升级为产品级字幕变更。
- [风格包与在制作品变更耦合] → 正在制作的 C 夜曲作品保持不写 `style.id`；本变更不要求迁移，风格包落地后由新作品使用。
- [外部许可边界被误用] → 只转译数值与方法，不复制 `engine/`、`film.js`、GIF/JPG、参考片画面与文案；样片仅作并排基准，不入库、不入片。
- [风格包被误当作自动换肤] → GUIDE 与规格明确：选择风格不自动改变画面，组件必须被作品显式导入。

## Migration Plan

无可迁移的旧风格。现有作品不自动获得 `style.id`；新作品按需声明。`create-night-embarrassment-film` 保持原状，不因本变更改写。完成实施与验证后按既有流程归档，同步 `openspec/specs/style-registry/spec.md` 与新增 `openspec/specs/vibe-night-style/spec.md`。
