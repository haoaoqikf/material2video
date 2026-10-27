# web/ —— 画面实现与渲染契约页

这里是 Material2Video 的**表现层与渲染层**：React composition 画画面，Remotion 逐帧渲染成 MP4。
内容层（材料与分镜 JSON）与配音层（Python 的 `m2v prepare`）不在这里。

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

渲染入口是固定常量（`src/m2v/engine/remotion/process.py` 的 `ENTRY_POINT`），没有
`--engine` 之类的切换参数：当前只有 Remotion 一条实现，留一个只有单一取值的
参数只会让「能不能换引擎」这件事含糊。

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

## 通用讲解

通用类型使用 v8 全画布代码场景：每一幕是作品 `scenes/` 下的本地 TSX，由 `src/code-scene/` 的独立录制页逐帧录制并缓存，`ArticleExplainer` 只回放片段与共享字幕；作品 TSX 不进入 composition，也不支持旧 general-plan 编排或片段嵌入。

## 渲染契约（`window.__M2V__` version 6）

契约页把 composition 挂进一个可被浏览器自动化驱动的页面，并暴露：

| 字段 | 说明 |
| --- | --- |
| `version` | 固定为 `6`；量测脚本按版本号拒绝旧页面，而不是等超时后报一句看不懂的话 |
| `fps` / `width` / `height` / `durationInFrames` | 必须与材料一致，不一致时渲染入口报错终止 |
| `ready()` | 字体就绪、Player 已挂载、首帧已绘制后 resolve |
| `seekToFrame(frame)` | 把画面定位到第 `frame` 帧并暂停，画面更新完成后 resolve |
| `currentFrame()` | 返回 Player 当前实际帧号，仅供只读诊断 |

契约页只量测已准备的 v8 讲解材料，不需要作品自带 HTML；页面通过 `m2v-storyboard` 查询参数
读取这些材料。

契约类型与求帧逻辑在 `src/contract/bridge.ts`，页面实现在 `src/contract/explainer.tsx`，**作品不许自己实现**。

## 字体

随仓库分发的两套可变字体（Inter、Noto Sans SC，均为 SIL OFL 1.1）由
`src/fonts.ts` 在运行时用 CSS Font Loading API 注册，URL 用相对路径 `fonts/<文件>`——
这样契约页与 Remotion 的页面用同一个字符串都能解析到。

字体二进制**不入库**，由仓库根 `fonts/registry.json` 与 `fonts/fetch.py` 恢复；
`src/assets/fonts.json` 仍声明画面注册的字体系列与源目录（`../fonts/files`）。
构建前 `scripts/sync-fonts.mjs` 从字体仓同步到 `public/fonts/`（已 gitignore），并核对
登记摘要。**源文件缺失或摘要不符会让构建失败**并提示运行
`uv run python fonts/fetch.py`：静默回退到系统字体是本项目最怕的一类失败——
成片出来了、字全变了、没有任何报错。

字体栈由 `tokens.css` 的 `--m2v-font` 给出，声明在 `:root` 上，页面里的所有元素
都继承它——不存在按属性切换的作用域。

## 源码确定性

共享 composition 的可达源码必须由帧号驱动画面；挂钟时间、随机数、计时器与 CSS 动画由 `src/m2v/core/source_policy.py` 在打包前检查。

## 许可证

| 依赖 | 许可 | 越界条件 |
| --- | --- | --- |
| Remotion | 个人与 ≤3 人公司**免费，可商用** | 4 人以上组织协作，或对外提供渲染服务（属「Remotion for Automators」，$0.01/render、$100/月下限）时须升级 |
| React / Tailwind / Vite | MIT | 随附许可证与版权声明 |
| Inter、Noto Sans SC | SIL OFL 1.1 | 随附许可证、不得单独售卖字体、不得用保留字体名发布修改版；本项目不做修改 |

Remotion 的免费额度按**组织规模与用途**判定，不按渲染量。个人内容生产落在免费范围内；
一旦这个项目变成对外服务或多人协作，**升级许可是使用前提**，不是可选项。
