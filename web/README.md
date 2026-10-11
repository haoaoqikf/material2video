# web/ —— 画面实现与渲染契约页

这里是 Material2Video 的**表现层与渲染层**：React composition 画画面，Remotion 逐帧渲染成 MP4。
内容层（`storyboard.json`）与配音层（Python 的 `prepare.py`）不在这里。

## 为什么是 React + Remotion

换成这套栈的理由只有一条：**组件供给**。原生 JS 时代每加一类画面（数据图表、关系图、
逐字动效）都要从零手写几何与排版，边际成本压不下来。换栈没有松动本项目的核心原则——
Remotion 的官方规则与 material2video 的渲染契约是同一句话：**所有动画由帧号驱动，
不许用 CSS 动画**。

## 环境要求

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| Node.js | ≥ 20（本机实测 22.23.2） | Remotion 与 Vite 都要求 |
| pnpm | ≥ 10 | 仓库用 pnpm；`node_modules/` 不入库，`pnpm-lock.yaml` 入库 |

首次执行：

```bash
cd web
pnpm install
```

`pnpm install` 之后**不需要**再手动批准构建脚本：`pnpm-workspace.yaml` 里已把 `esbuild`
列进 `onlyBuiltDependencies`（Vite 的构建依赖它的平台二进制）。若换到别的包管理器，
需要自行确保 esbuild 的 postinstall 跑过。

首次 `remotion render` 会下载 Remotion 自带的 Chrome Headless Shell（约 113MB）。
**这一步需要联网；装好之后渲染期完全离线。**

## 常用命令

命令都要在 `web/` 下执行（`remotion.config.ts` 里的 `@/` 别名按 `process.cwd()` 解析，
跑错目录会在配置加载阶段直接报错并说明原因）。

```bash
pnpm sync:fonts     # 把字体清单中的共享资产同步到 public/fonts（构建前自动跑）
pnpm dev            # 起契约页开发服务（http://localhost:5178/contract.html）
pnpm build          # 同步字体 + 类型检查 + 构建契约页到 dist/contract
pnpm studio         # 起 Remotion Studio，逐帧拖动查看画面
pnpm typecheck      # 只做类型检查
pnpm test           # 单元测试
```

真实渲染不走这里的手写命令——用仓库根的命令行入口：

```bash
uv run m2v render --project <作品目录>
```

它负责路径归属推导、契约校验、配音与字幕合成、成片验收与交付权限，再调用这里的
`scripts/remotion-render.mjs` 逐帧渲染。两边的分工是硬边界：**Python 判定，Node 只执行**。
中间靠 stdout 上带前缀的行通信（`__M2V_COMPOSITION__{…}` 报元数据、`__M2V_PROGRESS__<百分比>`
报进度），不解析 Remotion 的日志文本——日志措辞随版本变化，把判定挂在它上面升级一次就会静默失效。

`--engine` 当前只有一个取值 `remotion`（保留该参数用于显式声明契约）。

## 渲染脚本（`scripts/remotion-render.mjs`）

```bash
node scripts/remotion-render.mjs --bundle <打包目录> --props <分镜> [--out <mp4>]
  [--crf 18] [--preset medium] [--frames 0-29] [--metadata-only]
```

`--bundle` 由 `npx remotion bundle src/index.ts --out-dir <目录>` 产出。走 CLI 打包而不是
`@remotion/bundler` 的 `bundle()`，是因为只有 CLI 会读 `remotion.config.ts`，
`@/` 别名与 Tailwind 因此只在一处配置。每次渲染用一个**新的**打包目录：复用固定目录会在
源码改动后渲出旧画面，而这种错误没有任何症状——成片看起来完全正常，只是它是上一版。

`--metadata-only` 只报元数据不渲染，渲染入口用它把「画面声明的时长」与「分镜累计的时长」
在开渲之前对齐。

## 两条构建路径，一份源码

| 路径 | 入口 | 用途 |
| --- | --- | --- |
| Vite | `contract.html` → `src/contract/main.tsx` | 渲染契约页：被 Playwright 驱动，供体检与量测使用 |
| Remotion | `src/index.ts` → `src/Root.tsx` | 逐帧渲染成 MP4 |

两条路径编译**同一份** `src/` 与同一个样式入口 `src/styles/index.css`，
所以体检量到的画面与成片描述的是同一套代码。这是「预览与导出同源」在构建层的落实。

## 作品代码场景（`renderer.code`）

v4 在全片 `world.renderer` 声明 `kind: "code"` 与 `module`，把画面交给作品
`scenes/` 下的 TSX 模块；`stages[]` 只推进叙事，不单独声明 renderer。模块契约、
依赖白名单、探针协议与确定性纪律的**权威文档**在
[代码场景](../.agents/skills/material2video/references/code-scenes.md)，
这里只记 web 工程侧的接法：

- 静态清单 `.gen/active-scenes.ts`（由 `scripts/gen-active-scenes.mjs` 按当前作品
  整体重建）持有一个 `Record<string, M2VCodeScene<any>>` 映射；
  `src/compositions/CodeSceneHost.tsx` 按模块标识取组件渲染，缺失模块直接抛错；
- 作品模块通过别名 `@m2v/scene` 导入 `src/code-scene/index.ts`——这是作品可导入的
  **唯一**项目内部 API；tsconfig paths、Vite 与 Remotion webpack 三处都对白名单
  裸包与该别名配置了解析（仓库外的作品模块因此可以编译）；
- 本地资产（图片/SVG）用打包器导入（`import markUrl from '../assets/mark.png'`），
  不要写相对 URL 字符串——那会按页面地址解析成 404；
- 依赖白名单（`react` / `remotion` / `echarts` / `@dagrejs/dagre` / `lucide-react`）
  的版本锁定在本工程 `package.json`；作品不得自行安装或导入其他 npm 包。

## Tailwind 与作品代码场景

样式入口通过生成的 source 索引（`.gen/active-tailwind.css`，由
`scripts/gen-active-scenes.mjs` 按当前作品整体覆盖）把**当前作品**的
`scenes/` 与 `assets/` 交给 Tailwind 类名扫描；其他作品的文件不会被扫进来。

作品代码场景里写 Tailwind 类名必须用**完整字符串**：

- 直接写在 `className` 里的类名会进构建 CSS：`<div className="rounded-xl p-4">`；
- 完整字符串映射也会进构建 CSS：`const cls = { box: 'gap-6 border-2' }`；
- **运行时拼接的类名不保证生成**：`className={`rounded-${size}`}` 这种写法
  扫描器看不到完整类名，构建后可能没有对应规则，画面会静默缺样式。
  需要按状态切换时，把完整类名写进映射对象再取用。

## 渲染契约（`window.__M2V__` version 4）

契约页把 composition 挂进一个可被浏览器自动化驱动的页面，并暴露：

| 字段 | 说明 |
| --- | --- |
| `version` | v4 分镜为 `4`；内部旧版页面实现仍为 `3`，当前制作入口拒绝 v1～v3 分镜 |
| `fps` / `width` / `height` / `durationInFrames` | 必须与分镜一致，不一致时渲染入口报错终止 |
| `ready()` | 字体就绪、Player 已挂载、首帧已绘制后 resolve |
| `seekToFrame(frame)` | 把画面定位到第 `frame` 帧并暂停，画面更新完成后 resolve |
| `currentFrame()` | 只读诊断读数：画面当前停在第几帧，供量测失败时定位，不参与 `seekToFrame` 语义 |
| `world()` / `stage()` / `objectStates()` / `camera()` / `beats()` | v4 全片世界、当前阶段、对象状态、镜头与节拍探针 |

分镜地址由查询参数给出：`contract.html?m2v-storyboard=<分镜的 URL>`，
因此这一个页面服务任意作品，作品不需要自己的 HTML。

契约实现只有一处（`src/contract/bridge.ts`），**作品不许自己实现**。

## 字体

随仓库分发的两套可变字体（Inter、Noto Sans SC，均为 SIL OFL 1.1）由
`src/fonts.ts` 在运行时用 CSS Font Loading API 注册，URL 用相对路径 `fonts/<文件>`——
这样契约页与 Remotion 的页面用同一个字符串都能解析到。

字体的唯一真源是 `src/assets/fonts.json`（清单），文件本身在构建前由
`scripts/sync-fonts.mjs` 从 `src/assets/fonts/` 同步到 `public/fonts/`（已 gitignore）。
**源文件缺失会让构建失败**：静默回退到系统字体是本项目最怕的一类失败——
成片出来了、字全变了、没有任何报错。

字体栈只在 `[data-m2v-preset="keynote"]` 作用域内切换（见 `src/styles/tokens.css`），
作用域之外的元素不继承这套字体栈。

## 第三方依赖：只经代码场景白名单

画面**不再**支持接入第三方视觉组件：整页组件接入路径（分类表、帧同步包装层
`FrameSyncedCssAnimation`）已随场景树架构一并移除，`web/src/third-party/` 不再存在。
需要第三方库能力时，只能按
[代码场景](../.agents/skills/material2video/references/code-scenes.md)
在作品的代码场景里声明，并使用共享白名单：React、React DOM、Remotion、ECharts、
Dagre、Lucide 与 `@m2v/scene`。

白名单外的裸模块引用会被源码闸门拒绝（`m2v/code_gate.py`）；可渲染源码里的挂钟时间、
随机数、计时器与 CSS 动画/过渡同样会被拒绝（`m2v/source_policy.py`）。
各白名单视觉库的确定性适配规则见
[渲染契约](../.agents/skills/material2video/references/render-contract.md)。

## 许可证

| 依赖 | 许可 | 越界条件 |
| --- | --- | --- |
| Remotion | 个人与 ≤3 人公司**免费，可商用** | 4 人以上组织协作，或对外提供渲染服务（属「Remotion for Automators」，$0.01/render、$100/月下限）时须升级 |
| React / Tailwind / Vite / ECharts / Lucide | MIT / ISC | ECharts 为 Apache-2.0，Lucide 为 ISC：均可商用，随附许可证与版权声明即可 |
| Inter、Noto Sans SC | SIL OFL 1.1 | 随附许可证、不得单独售卖字体、不得用保留字体名发布修改版；本项目不做修改 |

Remotion 的免费额度按**组织规模与用途**判定，不按渲染量。个人内容生产落在免费范围内；
一旦这个项目变成对外服务或多人协作，**升级许可是使用前提**，不是可选项。
