## Why

内容侧已经收敛得很好：分镜 JSON 是单一真源，AI 只挑组件、给标注、指定节奏，渲染确定性可复现。
但**表现层的供给已经跟不上内容侧的需求**：组件目录只有八个由比喻驱动的图形，
而 [PROJECT_PLAN.md](../../../docs/PROJECT_PLAN.md) 自己登记着「复杂数值图表仍待扩展」，
关系图、流程图、逐字与镜头式动效则完全没有。继续在原生 JS 里手写几何，
每加一个组件都要重新发明排版、布局与动效，边际成本居高不下。

同时，[2026-09-17-introduce-declarative-visual-dsl](../archive/2026-09-17-introduce-declarative-visual-dsl/proposal.md)
当初记下的「不引入 React、Motion、GSAP、Three.js」是一条**在自建组件供给充足前提下的判断**。
今天这个前提不成立：缺口不是「少几个比喻」，而是整类画面（数据图表、关系结构、高级文字动效）
都需要从零手写。因此本次变更显式**取代**该结论，并把渲染层换成 React + Remotion。

换栈不会松动第一条原则：Remotion 官方规则与本项目渲染契约是同一句话——
「不要用 CSS 动画，所有动画由帧号驱动」。换的是执行者，不是判据。

## What Changes

- **BREAKING** 渲染层从「原生 HTML/CSS/JS + Playwright 逐帧截图 + imageio-ffmpeg」换成
  React + Tailwind + Remotion。旧共享资产（`base.css` / `theme.css` / `keynote.css` /
  `timeline.js` / `typography.js` / `figures.js` / `figures.css` / `declarative.*` /
  `vendor/spring.js`）在迁移完成后删除。
- **BREAKING** `window.__A2V__` 契约从 version 1 升到 version 2：字段与 `seekToFrame(frame)`
  语义不变，实现者改为 `@remotion/player`，`ready()` 额外保证 Player 已挂载且首批字体已加载。
- **BREAKING** 专属画面路径从 `videos/<slug>/index.html` 改为作品目录下的 `scenes.tsx`，
  由按 `A2V_CONTENT_ROOT` 生成的动态入口引入（生成目录不入库）。
- 新增 `web/` 前端工程（pnpm）：React 19 + TypeScript + Tailwind v4 + Remotion，
  含帧驱动运行时、组件注册表、第三方适配层与 `__A2V__` 契约页。
- **组件注册表成为唯一真源**：`kind` / 标注键 / 容量 / 适用场景 / 动效配方名由它定义，
  并据此**生成** `scripts/a2v/catalog.py`、组件目录文档的组件表与分镜 schema 的 kind 枚举，
  消除手抄镜像（`docs/PROJECT_PLAN.md` 记录过「基元清单是手抄的」这一类缺陷）。
- 新增组件类别与 kind：数据图表（柱 / 折线 / 饼 / 数值计数）与关系流程图
  （因果链、流程、系统结构），补上已登记的缺口。
- 新增第三方组件接入层，按**纯静态 / CSS keyframes / 自带时钟**三类分别处理：
  前两类可接入，第三类必须改写成帧驱动后接入；不允许未改造的第三方组件进入渲染路径。
- **保留并复用**：Python 侧的分镜校验、配音与字幕准备、K1–K10 观感闸门、M0–M4 动效闸门、
  组件契约探针、字体缺字机检、溯源、路径归属推导与交付文件权限修复全部继续生效，
  通过 `__A2V__` version 2 契约页对 Remotion composition 继续施加同一套判定。
- **BREAKING** 旧验收口径「同帧/跨会话逐字节一致」改为 **PSNR ≥ 60 dB**（`render-contract.md`
  既有阈值）；K 系列、M 系列与字体缺字机检的数值门槛不得放宽。

## Capabilities

### New Capabilities

- `remotion-renderer`：React + Remotion 渲染管线。定义 `__A2V__` version 2 契约页、
  逐帧确定性要求、成片编码与交付参数、以及 Python 入口与 Node 渲染器的分工。
- `react-component-registry`：组件注册表作为唯一真源，及其生成物
  （服务端目录镜像、组件目录文档、分镜 kind 枚举）的一致性与漂移检查。
- `deterministic-third-party-adapters`：第三方视觉组件的三类划分、CSS 动画的帧同步包装、
  自带时钟组件的改写要求，以及「未改造组件不得进入渲染路径」的机检。

### Modified Capabilities

- `declarative-video-scenes`：画面执行者从共享 HTML 页面改为共享 React composition；
  专属画面从 `index.html` 改为 `scenes.tsx`；受控组件集合扩大并改由注册表枚举。
- `frame-driven-motion`：动效原语从 `timeline.js` 迁到 TS 运行时，
  配方表数值与量测判据保持不变；外部依赖（闭式弹簧求解器）改为包依赖并要求随仓库锁定。
- `keynote-design-system`：设计令牌、四族基元与四个状态改为 TS/Tailwind 表达，
  对外契约（令牌名、基元类名、`data-a2v-*` 属性名）保持不变，使 K 系列与令牌闭包断言可原样复用。
- `font-coverage`：缺字机检的判据来源从「样式表里的 `@font-face`」改为
  「composition 实际注册的字体资产」，仍要求缺字按错误处理并定位到字段。
- `render-provenance`：指纹范围加入 TS 构建产物与依赖锁文件，
  使「改了组件源码但没重渲」能被判为落后。
- `article-workspace`：内容根下新增作品 composition 入口的解析规则，
  以及生成入口目录的归属与不入库约束。

## Impact

- **新增**：`web/` 整个前端工程（`package.json`、`pnpm-lock.yaml` 入库，`node_modules/` 与
  生成入口目录不入库）、`tests/` 中针对注册表生成物、适配层与 version 2 契约的新用例。
- **删除**：`.agents/skills/article2video/assets/` 下全部旧样式与脚本资产、
  `scripts/a2v/browser.py` 的截图路径、`scripts/a2v/encoder.py`、`scripts/a2v/static_server.py`；
  每个作品的 `index.html`。
- **保留并轻改**：`scripts/a2v/` 的 `storyboard.py`、`catalog.py`（改为生成物）、`prepare.py`、
  `media.py`、`paths.py`、`security.py`、`subtitles.py`、`fonts.py`、`assets.py`、
  `inspect.py`、`keynote.py`、`motion.py`、`constitution.py`、`cli.py` 与前五个命令行入口。
- **依赖**：Node / pnpm 成为渲染与预览的必需依赖；`imageio-ffmpeg` 与 `playwright` 的用途收窄
  （后者只服务体检探针）。Remotion 采用个人免费许可（个人与 ≤3 人公司可商用），
  升级触发条件写入 `web/README.md`。
- **文档**：README 的当前状态与关键约束、`docs/PROJECT_PLAN.md` 的链路图与技术栈、
  `openspec/config.yaml` 的技术栈一行、Skill 主文档与全部 `references/`。
- **兼容性**：`storyboard.json` 结构保持兼容，旧分镜无需改写；
  但**已实现专属网页的作品必须改写为 `scenes.tsx`**，这是本次唯一的源文件级破坏性变更。
