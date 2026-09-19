# article2video

将观点型文章转换成竖屏信息可视化短视频的个人内容生产项目。

**文章是内容层，网页是表现层，视频是最终发布格式。** 项目把抽象观点、因果关系和核心模型
转化为观众可以直观看到的思想结构。

## 这是什么

一个**项目级 Skill**：由 AI 编程工具（Codex、Claude Code、DSH 等）读懂文章并选择视觉组件；特殊构图可生成专属动画网页，
再由确定性脚本把网页逐帧渲染成 MP4。AI 不直接生成视频，因此画面可控、可改、可重渲染。

```text
文章 → 分镜 JSON → 配音与字幕准备（可选）→ 动画网页 → 逐帧渲染与音轨合成 → 竖屏 MP4
```

Skill 位于 [`.agents/skills/article2video/`](.agents/skills/article2video/SKILL.md)，
该目录被 Codex 与 DSH 直接识别；Claude Code 需要时可用软链接映射到 `.claude/skills/`。

## 当前状态

仓库已接入 [OpenSpec](openspec/config.yaml) 进行功能变更规划：`openspec/changes/` 存放进行中的提案、规格与任务，归档后的能力规格存放在 `openspec/specs/`（现有 `declarative-video-scenes` 与 `article-to-storyboard` 两项）。Codex 与 DSH 的工作流 Skill 位于 `.agents/skills/openspec-*/`。首次使用前需安装 OpenSpec CLI；在仓库根目录可用 `openspec list` 查看变更，以 `$openspec-propose` 发起新提案。

已完成**支持多篇文章目录规范的可选配音视频端到端链路**：

- 新视频可只写 `article.md` 与 `storyboard.json`：共享页面按分镜声明的组件、主题和布局生成画面；`--page` 仍支持原有专属网页。声明式示例见 [`examples/declarative-number/`](examples/declarative-number/storyboard.json)，其数字组件为第八个组件；

- 分镜 JSON 的结构校验（版本、帧率、尺寸、场景 ID、时长、组件字段、关系图节点引用、图形标注），
  并按视觉规范给出排版警告（单行字数、场景过短、强调短语不生效、标注过长）；
- 网页与渲染脚本之间的确定性渲染契约 `window.__A2V__`，并提供时间轴运行时
  （帧状态推导、入场与常驻微动原语、预览播放控制）；
- 共享设计令牌 `assets/theme.css`：颜色 / 表面 / 阴影 / 圆角 / 节奏令牌，
  以及光晕、网格、细点阵三种可复用背景层，供网页按需引用；
- **视觉组件库** `assets/figures.js` + `assets/figures.css`：八个由帧驱动的画面组件
  （天平 / 落差尺 / 双栏对照 / 冰山 / 飞轮 / 阶梯 / 双向选择 / 数字），专属网页只声明
  `<div data-a2v-figure></div>` 挂载点，分镜用 `data.figure.kind` 选组件、
  用 `labels` 给短标签、用 `motion` 指定节奏；组件自带 DOM 与样式，文案全部来自分镜。
  目录与新增组件的契约见
  [视觉组件目录](.agents/skills/article2video/references/figure-catalog.md)；
- **动效配方层** `A2V.motion`：入场、弹性、收敛、常驻微动与节奏换算都写在
  `timeline.js` 一处，组件用名字调用（`api.motion.spring(api.since(f, start), 'lively')`，
  弹簧收的是秒数而不是缓存动过的进度），手感参数不会随组件漂移；
  Spring 曲线是 vendored 的阻尼谐振子闭式解（`assets/vendor/spring.js`，wobble 1.5.1 · MIT），
  参数是物理量：`response`（自然周期，秒）与 `dampingFraction`（阻尼比 ζ）；
- 动效原语全部为纯函数：`progress` / `since` / `enter` / `spring`（物理弹簧）/
  `breath`（常驻微动）/ `drawPath`（SVG 描边）/ `revealChars`（逐字揭示）；
  曲线必须能按帧独立求值（渲染是随机访问帧，闭式解而非逐帧积分），
  `tests/test_motion_trajectory.py` 会逐帧量真实轨迹并覆盖参考实现的每一个入场元素
  （90 个：落地距幕尾 ≥ 12 帧、不透明度不回退；其中有位移的 9 个还要首帧 ≤ 25%、
  到 0.9 ≥ 6 帧），并带一个「把入场加速 8 倍就必须报错」的反例；
  量测实现只有一份（`scripts/a2v/motion.py`），验收命令 `review.py` 会对
  **任意**页面与分镜给出同一套结论（`report.json` 的 `motion` 段，终端 M0–M4 一栏），
  动效结论与「不是废片」类错误分开计、不改退出码；
  `tests/test_vendor_spring.py` 对 vendored 求解器核对解析解自身的性质；
- 开渲前静态扫描 `animation:` / `transition:` / `@keyframes` 与
  `Date.now(` / `performance.now(` / `Math.random(` 并给出警告，
  范围覆盖网页引用的本地样式表与脚本（含 skill 的共享资产与 `/__a2v__/` 别名），
  把「预览正常、导出闪烁」提前暴露；
- 本地 HTTP 预览（网页需 fetch 分镜 JSON，`file://` 下会被同源策略拒绝）；
- **文章生成分镜**：从文章产出分镜的步骤、拆幕与时长规则、内容与排版约束、组件目录不足时
  的新增组件流程，以及生成后必须走完的校验闭环，统一写在
  [文章生成分镜](.agents/skills/article2video/references/article-to-storyboard.md)；
  由 AI 工具按规范执行，仓库不含生成器程序。`review.py` 支持声明式入口
  （`--declarative --storyboard <分镜>`），共享页面也能跑组件契约探针；
- Playwright 逐帧截图 + ffmpeg 管道编码，输出 1080 × 1920 / 30fps / H.264 `yuv420p` MP4，
  渲染后自动解码验收帧数与分辨率；
- 码流按「各播放器都能播」的参数固定：画面 `yuv420p(tv, bt709)`、配音 AAC-LC
  44.1kHz 立体声；验收阶段会读回码流，命中全范围像素格式（`yuvj420p`）直接报错
  ——这类流 ffmpeg 能解码，但 Windows 的 Media Foundation 会以 `0xc00d36c4` 拒绝打开；
- 交付文件落盘后自动交回目标目录的继承权限：经临时目录中转的文件会带上「关闭继承」
  的 ACL，导致打包应用（Windows 11 新版媒体播放器）报 `0x80070005` 打不开成片；
- 成片带溯源：渲染成功后在同目录写 `<名字>.provenance.json`（页面、分镜、**网页真正
  引用的**资产指纹、帧数分辨率帧率、采集格式与渲染时刻），体检命令据此回答
  「这个成片是不是旧资产渲的」——`report.json` 的 `provenance` 段与终端一栏给出
  `对得上` / `落后（并指名是哪几个文件变了）` / `无法判断`。
  它是提示不拦人：不参与错误数，也不改退出码。为什么需要它：成片不入库，
  以前改了动效资产而没重渲，旧成片看上去仍然是「上次验收通过」的样子。
  溯源一律用相对引用（`workspace` + 工作区相对键，共享资产记 `/__a2v__/` 别名键），
  因此文章与产物放在仓库之外也读得回来；
- 一个可直接运行的完整示例：`examples/why-effort-fails/`（5 幕，1350 帧，45 秒），
  已按「排版层级 + 三层景深 + 统一动效曲线」重做，作为新视频的观感基线；
- edge-tts 中文自动配音、逐句字幕烧录与 SRT 导出；配音超时自动延长场景；
- 配音按场景缓存，统一 WAV 音轨支持预览播放、拖动和最终 AAC 合成；
- 目录约定与输出路径推导：每篇文章一个 `videos/<slug>/`，产物落在 `outputs/<slug>/`，
  示例产物独立在 `outputs/examples/<slug>/`；`--out` 与 `--out-dir` 可省略，
  显式参数继续优先；
- **文章与仓库解耦**：`videos/` 是作品内容，已在 `.gitignore` 中忽略（文章内容不入库）；
  文章与产物还可以整体放在仓库之外的**内容根**里，用 `--content-root` 或
  `A2V_CONTENT_ROOT` 指定（命令行优先），命令与产物结构完全不变。内容根里的页面用
  `/__a2v__/<文件>` 引用仓库中那一份共享资产——静态服务器按这个别名把请求接到 skill 的
  `assets/`（只服务文件、不列目录，`..` 也穿不出去），所以内容根里不需要 skill 副本，
  也不会把仓库其他目录暴露给页面。不设内容根时工作区根就是仓库根，行为与之前一致；
- 一篇实际视频：`videos/never-fear-interviews/`（《永远不要害怕面试》，8 幕，
  2189 帧 / 73.0 秒有声），采用「编辑杂志」风格方向（浅底 + 墨黑文字 + 单一朱红强调），
  八幕全部以帧驱动的比喻画面表达道理（天平 / 落差尺 / 冰山 / 飞轮 / 冰山 / 阶梯 /
  双栏对照 / 双向选择），实现了 `list` 与 `timeline` 两个示例里没有的场景分支；
  页面另有常驻进度轨（幕号 / 章节 / 全片进度）为下半幅收口。**这篇内容不入库**：
  它只存在于作者本机的内容目录里，克隆仓库看不到它，制作方法以 `examples/` 为准；
- **发布会级设计语言层**（可选）：分镜根级声明 `visual.preset: "keynote"` 时启用
  `assets/keynote.css`——模块化字号阶（8 档，正文下限 36px，每档配对行高与字距）、
  8pt 间距阶（4–192px）、五个圆角档 + pill、三级阴影、12 列网格（内容宽 888px、
  槽宽 24px），以及 `keynote-dark`（bg `#08090c`、强调 `#32d6ff`）与
  `keynote-light`（bg `#eff1f4`、强调 `#0a6ad9`）两套主题，对比度预算正文 7:1、
  大字与图形 4.5:1；**图形颜色按五类分别守预算**（数据描边与图形内文本对画布 ≥ 4.5:1、
  边界描边对抬升面 ≥ 3:1、装饰描边 ≥ 1.5:1、面填充不设数值下限——形状由描边界定），
  `figures.css` 的 `fill`/`stroke`/`background` 里不许出现字面色值，均由
  `tests/test_figure_contrast.py` 按分类表断言，新增 `--fig-*` 必须先归类；
  纯分隔线刻意保持耳语并豁免于 WCAG 1.4.11；
  Inter Variable 与 Noto Sans SC Variable（SIL OFL 1.1）
  随仓库分发、不走 CDN；`assets/typography.js` 提供可选排版引擎 `A2V.type`
  （不属于渲染契约）：组件用 `data-a2v-fit="<档位>"` 声明字号上限档位，共享页面在预设
  生效时按**实测可用宽度**取档、按宽度均衡断行，到 36px 正文下限即停；行高、字距、
  字重仍归组件，字号归字阶。未声明的元素不会被改动；不声明 `preset` 时它不生效
  （样式受预设作用域约束、排版引擎不被调用）——新增预设层时用逐字节回归验证过
  「加预设不改非预设画面」，那份非预设成片的哈希后来在**动效升级**那一轮被刻意重新记录
  （改动在动效曲线，不在样式），所以样式隔离现在由
  `tests/test_typesetting_wiring.py` 的「非预设页面零取档」与
  `tests/test_keynote_assets.py` 的「视觉规则必须限定在预设作用域内、每个令牌都带原值兜底」守住；
  参考实现见
  [`examples/keynote-baseline/`](examples/keynote-baseline/storyboard.json)（8 幕 / 2040 帧 / 68 秒）；
- **观感闸门 K1–K10**：`scripts/a2v/keynote.py` 把留白预算、强调色占比、同帧字号种类、
  对齐基线、正文对比度、卡片纪律、图形描边一致性量成数值结论，与回答「是不是废片」的
  C 系列**分开计分**；`review.py --declarative` 时随体检一起输出，取不到样本的条目
  跳过并写明原因。
  其中 **K7 文字溢出与 K8 容器内溢出是硬判定**：文本块越出安全区（容差 8px）、
  图形内的文字穿出它所属的容器（容差 2px，容器由组件用 `data-a2v-inside` 声明）、
  或排版引擎报「缩到正文下限仍放不下」时，会并入体检的错误数与退出码，
  并报出是哪个文本块/哪段文字、往哪个方向越了多少像素。
  K8 补的是 K7 量不到的那一格：K7 的参照只有安全区，而图形内按几何位置绘制的文字
  （飞轮节点、冰山标注、天平载物…）既不受安全区判定也不受容器判定。
  阈值与设计取舍见
  [发布会级设计语言](.agents/skills/article2video/references/keynote-design-system.md)；
- **组件级令牌与状态（进行中）**：`figures.css` 的描边宽度、字重、字距、圆角、
  1px 边框、间距、内边距与 `margin-top` 已经全部走令牌（86 处引用，字面值清零），
  不在 8pt 阶上的取值一并改到阶上。`keynote.css` 另外定义了四个图形基元
  （`a2v-surface` / `a2v-label` / `a2v-connector` / `a2v-frame`）与四个状态
  （`rest` / `focus` / `muted` / `done`）。
  这套约束由 `tests/test_figure_token_closure.py` 守住：以后往组件里写一个裸数值
  （`stroke-width: 3px`、`gap: 18px`）会直接测试失败。
  **基元与状态目前只落在飞轮一个组件上**——这是进行中的工作，不要当成已完成的能力；
- **容器内文字由内容测量决定几何**：装文字的容器（节点圆等）按实测文字宽度定形，
  而不是先写死尺寸再把字塞进去。参考示例的飞轮节点原先半径 76px 配 44px 的四字标签
  （约 183px，比直径还宽 31px），文字穿出圆而所有机检全绿，现在由 K8 守住；
- 自动化测试覆盖校验、缓存与失败恢复、字幕时间轴、预览同步、动效原语、
  渲染前置扫描、有声/无声渲染与路径推导。

尚未实现、请勿当作已有能力使用：**分镜生成器程序**（生成由 AI 工具按
[规范](.agents/skills/article2video/references/article-to-storyboard.md) 执行，没有内置生成服务、
模型调用或批量生成）、**背景音乐**、**内容根的自动探测**（只能显式指定，脚本不去猜）、
**平台发布**、批量渲染与成片历史版本。

设计语言层相关的未实现项同样不要当作已有能力：**视觉模型自动评审**（K 系列只给数值，
最终判断仍要人按
[评审量表](.agents/skills/article2video/references/visual-review-rubric.md) 完成）、
**webfont 子集化**（Noto Sans SC Variable 约 17MB）、**按内容自动选预设**
（必须由分镜显式声明），以及 K6 对「整幕没有卡片」只报跳过、不判断「这一幕本该有卡片」。

## 快速开始

```bash
# 1. 安装依赖（首次）
uv sync
uv run playwright install chromium

# 2. 校验分镜
uv run python .agents/skills/article2video/scripts/validate.py examples/why-effort-fails/storyboard.json

# 3. 本地预览（浏览器中确认节奏与排版）
uv run python .agents/skills/article2video/scripts/preview.py examples/why-effort-fails

# 4. 视觉评审（抽帧量测 + 组件契约探针 + 设计宪法，产出联系表与 report.json）
uv run python .agents/skills/article2video/scripts/review.py \
  --page examples/why-effort-fails/index.html \
  --storyboard examples/why-effort-fails/storyboard.json

# 5. 渲染（省略 --out 时输出到 outputs/examples/why-effort-fails/silent.mp4）
uv run python .agents/skills/article2video/scripts/render.py \
  --page examples/why-effort-fails/index.html \
  --storyboard examples/why-effort-fails/storyboard.json

# 6. 测试
uv run pytest
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

uv run python .agents/skills/article2video/scripts/preview.py examples/why-effort-fails \
  --media outputs/examples/why-effort-fails/media/media.json

uv run python .agents/skills/article2video/scripts/render.py \
  --page examples/why-effort-fails/index.html \
  --storyboard examples/why-effort-fails/storyboard.json \
  --media outputs/examples/why-effort-fails/media/media.json
```

省略 `--out-dir` 时媒体写入 `outputs/examples/why-effort-fails/media/`；省略 `--out` 时
无声导出为 `silent.mp4`，带 `--media` 则导出 `voiced.mp4` 和同名 `voiced.srt`。
加 `--limit-frames` 默认写入 `previews/`，不会覆盖正式成片。显式 `--out`、`--out-dir`
始终优先，原有调用方式继续可用。

默认音色 `zh-CN-XiaoxiaoNeural`、语速 `+0%`；可用 `--voice`、`--rate=-10%` 调整，
`--force` 强制重新合成。首次合成需要联网，无需 API key；已有缓存可离线重新准备与导出。
输出 MP4 内含字幕和 AAC 配音，同时生成同名 SRT。背景音乐尚未实现。

原分镜不被覆盖；原场景时长作为最短时长，配音较长时自动延长并留 300ms 收尾。
示例原长 45 秒，本机默认配音实测 46.27 秒；在线服务结果可能变化，以媒体清单为准。
修改分镜后重新执行 prepare（未改变的口播命中缓存）。详细接口和错误处理见
[配音与字幕](.agents/skills/article2video/references/media-contract.md)。

## 制作一支新视频

1. 新建文章目录 `videos/<slug>/`（slug 稳定、唯一，标题变化不改名），写入 `article.md` 与
   `storyboard.json`。目录留在仓库里即可——内容不入库，不会被提交；想放仓库外时把它放进
   内容根（`--content-root <目录>` 或环境变量 `A2V_CONTENT_ROOT`），内容根下同样放
   `videos/<slug>/`；
2. 声明式路径到第 2 步就够（共享页面按分镜画画面）；需要专属网页时复制
   `examples/why-effort-fails/index.html` 作为模板，按
   [竖屏视觉规范](.agents/skills/article2video/references/visual-spec.md) 的层级与动效配方改写场景。
   页面在仓库外时，把共享资产引用从 `../../.agents/skills/article2video/assets/…`
   改成 `/__a2v__/…`；
3. 依次执行上面的校验、预览、渲染命令；`outputs/<slug>/` 由脚本自动推导
   （内容根在仓库外时即 `<内容根>/outputs/<slug>/`），无需手动创建。

已完成的文章：

| 目录 | 内容 | 分镜 | 成片 |
| --- | --- | --- | --- |
| `videos/never-fear-interviews/`（不入库，作者本机） | 《永远不要害怕面试》 | 8 幕 / 2189 帧（73.0 秒） | `outputs/never-fear-interviews/voiced.mp4` + `.srt` |
| `examples/why-effort-fails/` | 《为什么努力没结果》（观感基线） | 5 幕 / 1350 帧（45 秒） | `outputs/examples/why-effort-fails/` |

`videos/never-fear-interviews/` 采用「编辑杂志」方向（浅底 + 墨黑衬线 + 单一朱红强调），
八幕全部改为**以形表意**：每一幕先用一个由帧驱动的比喻把道理画出来，文字只做注解，
而不是先排一段文字再配装饰。八幕依次是

| 幕 | 场景类型 | 比喻 |
| --- | --- | --- |
| 01 开场命题 | `title` | 天平：一侧是「命运的考试」，另一侧是「一次上场」，梁先倾后平 |
| 02 真正的损失 | `quote` | 落差尺：左栏从满到空量出「失去全部」，右栏贴着 0 线量出「无可失去」 |
| 03 恐惧的来源 | `list` | 冰山：水面之上是「不是失去」，水面之下是「是暴露」，光照过水后浮出「而变强」 |
| 04 反馈循环 | `diagram` | 飞轮：小球绕三节点一圈，底部的「准备度」同步填满 |
| 05 一份新信息 | `list` | 冰山：三个反馈渠道（简历 / 技术 / 表达）挂在水面之下，水面标为「现场反馈」 |
| 06 上场的复利 | `timeline` | 阶梯：四根逐级升高的柱子，标记随之跳动，末段翻转为「你在挑公司」 |
| 07 真正的危险 | `comparison` | 双栏对照：左栏「面试失败」→ 右栏「不敢进场」，箭头指出该防的是哪一边 |
| 08 收束 | `conclusion` | 双向选择：两条相反方向的箭头对流，「多上场」落在下方 |

比喻里的短标签（托盘名、水面、纵轴名等）全部来自分镜的 `figure.labels`，
网页不保存任何默认文案；八个比喻本身由视觉组件库提供，网页只声明挂载点与进度轨。

`examples/why-effort-fails`（《为什么努力没结果》）已经用同一套组件、换一套设计令牌
重做：深色底、青色强调，五幕分别是 `balance` / `versus` / `versus` / `loop` / `exchange`。
两份页面都不含任何图形代码——同一套组件在浅色与深色两套主题下都成立，
这正是「AI 做导演，不做设计师」想达到的效果：换内容只需要改分镜。

目录结构与归属推导规则见
[目录约定与输出路径](.agents/skills/article2video/references/paths-and-outputs.md)；
分镜字段、网页契约与排版规范见
[渲染契约](.agents/skills/article2video/references/render-contract.md)、
[分镜脚本结构](.agents/skills/article2video/references/storyboard-schema.md)、
[竖屏视觉规范](.agents/skills/article2video/references/visual-spec.md)。

## 视觉评审

`review.py` 一次跑完三层检查，产物落在 `outputs/<slug>/inspect/`：

- **组件契约探针**：逐幕多处采样，读出挂载点里每个元素的实际文本，比对分镜声明的标注
  是否真的画了出来。「组件挂上了、画面也出来了，只是图上没有一个字」这类缺陷不会报错，
  只能靠读 DOM 发现——这正是它存在的理由；
- **帧量测**：墨迹覆盖率（防空幕、黑屏）与上下安全区的墨迹；
- **设计宪法静态检查**：结构、曲线纪律、模糊、挂载点、文案单一真源、安全区。

机检只保证「这不是废片」。**值不值得看完**按
[视觉评审量表](.agents/skills/article2video/references/visual-review-rubric.md)
六项 60 分制打分，≥ 40 才发布：[设计宪法](.agents/skills/article2video/references/design-constitution.md)
标明每条规则能不能机检——把审美也交给脚本，等于放弃质量。

## 关键约束

- **单一真源**：文案与原始时长写在 `storyboard.json`；启用配音时，网页和脚本共用媒体清单中的派生时长；
- **帧驱动**：画面只由帧号推导。禁止 CSS `animation`/`transition`、`Date.now()`、
  `Math.random()`，否则逐帧截图会闪烁且不可复现；渲染前会静态提示这类写法；
- **手感只有一处**：入场、弹性、收敛、常驻微动这些决定「整支片子什么手感」的数字
  只写在 `timeline.js` 的 `A2V.motion` 配方表里，组件用 `api.motion.enter(...)`、
  `api.motion.spring(api.since(f, start), 'lively')` 这样的名字调用，不写裸数字；
  `tests/test_motion_trajectory.py` 会按帧量真实轨迹，防止配方改着改着变成弹跳；
  验收命令 `review.py` 对任意作品都会跑同一套量测（终端 M0–M4 一栏），
  但它只提示、不拦人——「入场快了一点」不是「画面坏了」；
- **产物归属**：一篇文章一个目录，产物只写进它自己的工作区根下 `outputs/<slug>/`；
  推导不出归属时脚本报错并要求显式指定路径或内容根，不猜测；
- **性能取舍**：中间帧默认用 JPEG q98 采集（1080 × 1920 实测约 66ms/帧，PNG 约 225ms），
  需要逐像素比对时用 `--capture-format png`；画面避免大面积 `filter: blur()`，
  光晕用 `radial-gradient` 或 `box-shadow` 实现。

## 文档导航

- [声明式示例](examples/declarative-number/storyboard.json)：无需专属网页的分镜与共享页面入口

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
