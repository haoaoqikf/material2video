# web/ —— 画面实现与渲染契约页

这里是 Material2Video 的**表现层与渲染层**：React composition 画画面，Remotion 逐帧渲染成 MP4。内容层（材料与分镜 JSON）与配音层（Python 的 `m2v prepare`）不在这里。代码分层、模块边界与依赖方向见 [ARCHITECTURE.md](../ARCHITECTURE.md)；渲染、量测与契约页细节见[渲染引擎](../.agents/skills/material2video/references/render-engine.md)与[代码场景运行契约](../.agents/skills/material2video/references/code-scene-runtime.md)。

## 目录分层

- **通用代码**：`src/code-scene/`、`src/runtime/`、`src/contract/`、`src/production/`、`src/styles/`、`src/assets/`，以及 `Root.tsx`、`frames.ts`、`fonts.ts`、`video-config.ts`。
- **类型专属代码**：`src/types/<type>/`，含该类型的 composition、纯函数、布局 JSON 与契约页入口。
- **具体作品代码**：作品内容目录下的 `scenes/` 与 `assets/`，不放进 `src/`。

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

`pnpm install` 之后不需要再手动批准构建脚本：`pnpm-workspace.yaml` 已把 `esbuild` 列进 `onlyBuiltDependencies`。首次 `remotion render` 会下载 Remotion 自带的 Chrome Headless Shell（约 113MB），这一步需要联网；装好之后渲染期完全离线。

## 常用命令

命令都要在 `web/` 下执行（`remotion.config.ts` 里的 `@/` 别名按 `process.cwd()` 解析）。

```bash
pnpm sync:fonts     # 把字体清单中的共享资产同步到 public/fonts（构建前自动跑）
pnpm dev            # 起契约页开发服务（http://localhost:5178/contract.html）
pnpm build          # 同步字体 + 类型检查 + 构建契约页到 dist/contract
pnpm studio         # 起 Remotion Studio，逐帧拖动查看画面
pnpm typecheck      # 只做类型检查
pnpm test           # 单元测试
```

真实渲染不走这里的手写命令，用仓库根入口：

```bash
uv run m2v render --project <作品目录>
```

它负责路径归属、契约校验、配音与字幕合成、成片验收与交付权限，再调用 `scripts/remotion-render.mjs` 逐帧渲染。两边分工是硬边界：**Python 判定，Node 只执行**；中间靠 `__M2V_COMPOSITION__` / `__M2V_PROGRESS__` 前缀行通信，不解析 Remotion 日志。

## 渲染脚本

```bash
node scripts/remotion-render.mjs --bundle <打包目录> --props <分镜> [--out <mp4>]
  [--crf 18] [--preset medium] [--frames 0-29] [--metadata-only]
```

`--bundle` 由 `npx remotion bundle src/index.ts --out-dir <目录>` 产出。走 CLI 打包而不是 `@remotion/bundler` 的 `bundle()`，是因为只有 CLI 会读 `remotion.config.ts`，`@/` 别名与 Tailwind 因此只在一处配置。每次渲染使用**新的**打包目录：复用固定目录会在源码改动后渲出旧画面，而这种错误没有症状。`--metadata-only` 只报元数据不渲染，用于开渲前对齐画面声明时长与分镜累计时长。

## 渲染契约

契约页把 composition 挂进可被浏览器自动化驱动的页面，暴露 `window.__M2V__` 的 `version`、`fps`、`width`、`height`、`durationInFrames`、`ready()`、`seekToFrame()` 与 `currentFrame()`。字段语义、版本拒绝规则与量测边界见[代码场景运行契约](../.agents/skills/material2video/references/code-scene-runtime.md)。两条构建路径（Vite 契约页与 Remotion 渲染）编译同一份 `src/` 与样式入口，因此量测画面与成片同源。

## 字体

随仓库分发的共享字体由 `src/fonts.ts` 在运行时通过 CSS Font Loading API 注册，URL 用相对路径 `fonts/<文件>`。字体二进制不入库，由仓库根 `fonts/registry.json` 与 `fonts/fetch.py` 恢复；构建前 `scripts/sync-fonts.mjs` 从字体仓同步到 `public/fonts/` 并核对摘要，缺失或摘要不符会让构建失败。恢复、缓存、许可与故障处理见[字体仓](../fonts/README.md)。

## 许可证

| 依赖 | 许可 | 越界条件 |
| --- | --- | --- |
| Remotion | 个人与 ≤3 人公司**免费，可商用** | 4 人以上组织协作，或对外提供渲染服务（属「Remotion for Automators」，$0.01/render、$100/月下限）时须升级 |
| `@remotion/paths` / `@remotion/animation-utils` | MIT | 随附许可证与版权声明 |
| `@remotion/layout-utils` / `@remotion/noise` | MIT | 随附许可证与版权声明 |
| `d3-scale` / `d3-shape` | ISC | 随附许可证与版权声明 |
| `roughjs` | MIT | 随附许可证与版权声明 |
| `perfect-freehand` | MIT | 随附许可证与版权声明 |
| `svg-path-properties` | ISC | 随附许可证与版权声明 |
| React / Tailwind / Vite | MIT | 随附许可证与版权声明 |
| Inter、Noto Sans SC | SIL OFL 1.1 | 随附许可证、不得单独售卖字体、不得用保留字体名发布修改版；本项目不做修改 |

Remotion 的免费额度按**组织规模与用途**判定，不按渲染量。个人内容生产落在免费范围内；一旦这个项目变成对外服务或多人协作，**升级许可是使用前提**。
