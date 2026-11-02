## Context

共享组件库上一轮只做到 L1/L2 动效与路径封装。真实作品仍在各自场景里手写 `clamp`/`ease`、标题字号、SVG 图表、圆环、时间轴与波形；`pure-time` 场景又禁用 ECharts，导致需要数据图时只能退回 `sequential`。本轮优先补"制作中反复出现、且有成熟纯函数实现"的能力，不追求组件数量。

## Decisions

### 1. 依赖选型与版本

- `@remotion/layout-utils@4.0.526`（MIT，无运行依赖）：`fitText` 做单行字号适配，`measureText` 做逐行断行测量。
- `@remotion/noise@4.0.526`（MIT，6 KB，依赖 `simplex-noise` 与 `remotion` 的确定性 `random(seed)`）：种子噪声。
- `d3-scale@4.0.2` + `d3-shape@3.2.0`（ISC，ESM 可摇树）：比例尺、刻度、折线/面积曲线。
- 全部精确锁定并与现有 Remotion 4.0.526 对齐；不加入 `build-code-scene.mjs` 的 approved 白名单。

### 2. 不引入的候选

- `@remotion/lottie`：许可为 `SEE LICENSE IN LICENSE.md`，且依赖 `useCurrentFrame`，code scene 无法直接驱动。
- `@remotion/transitions`、`@remotion/motion-blur`：只适用于 Remotion composition，code scene 已有子帧运动模糊。
- `@remotion/shapes`：标准形状用现有 SVG 手写成本更低，本轮不增加包体积。
- `flubber`、`polymorph-js`：停更，且 `@remotion/paths` 的 `interpolatePath` 已覆盖逐点插值。
- `lucide-react`：通用图标会削弱各风格的美术身份，需要时先沉淀少量项目图标。
- `@number-flow/react`、`react-countup`、`rough-notation`：时间驱动，违反 `progress` 单一输入契约。
- `recharts`/`visx`/`nivo`：与 ECharts 重复；纯时间图表用 d3 子模块更轻。

### 3. 文本测量与 CJK

`@remotion/layout-utils` 的 `fillTextBox`/`fitTextOnNLines` 按 `text.split(' ')` 切词，中文整句会被当成一个词，**不会换行**。因此：

- `AutoFitText` 只用 `fitText`（单行缩字号），中英文都可用。
- `TextBlock` 自己实现 CJK 断行：中文按字、西文按词、收尾标点吸附前一字、超长西文按字符硬断；测量函数由 `measureText` 注入，纯函数 `wrapText` 可单测。
- 组件首次渲染可能早于字体加载；用 `document.fonts.ready` 触发一次重测，字体未就绪时回退到调用方字号。Node/SSR 下不测量、不抛错。

### 4. 图表边界

`LinePlot`/`AreaPlot`/`Sparkline`/`Axis` 只做比例尺、曲线与静态 SVG，不内含坐标轴自动排版、图例或交互；坐标轴由调用方组合到同一个 SVG。折线按 `pathDrawProps` 生长，面积按 `clipPath` 从左向右揭示。这样 `pure-time` 的静态闸门（禁止 ECharts/Chart、`useFrame`、计时器）仍然成立。

### 5. 包体与导出

沿用单一 `m2v/code-scene` 入口，不引入按需子路径。新依赖均为 ESM 或可摇树的 CJS，esbuild 只保留实际用到的导出；等到真实作品迁移后若包体明显上升，再评估 `m2v/code-scene/text|charts` 子路径（那会改变构建白名单映射，另立变更）。

### 6. 不与本轮合并的事项

- 不迁移 `styles/*` 与 `videos/*` 到新组件：现有风格组件已有明确实现，迁移属于作品级改动，需要代表帧复核与重新准备。
- 不新增 gallery demo：Vitest 静态标记与 `pure-time` 慢测覆盖渲染契约。

## Risks

- `@remotion/noise` 通过 `remotion` 的 `random(seed)` 建表；`animation-utils` 已把 `remotion` 带进 code scene，因此不新增运行时依赖面，但仍需 slow 构建/PSNR 验证。
- 文本测量依赖字体与 DOM；本地缓存了测量结果，字体中途变化不会自动失效。录制页在 `ready()` 前等字体，组件再等一次 `document.fonts.ready`。
- 实现指纹变化会使所有引用代码场景的作品缓存失效，需要重新 prepare；本轮不重制既有成片。
