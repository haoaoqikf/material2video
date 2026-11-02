## Context

《样本》的四处差距来自同一层缺口：画面变化都靠整段透明度叠放，没有可复用的运动原语，也没有“同一对象跨拍延续”的机制。本变更先把可复用的数学与运动抽到 `web/src/code-scene/`，再在 `dark-proof` 包内组装风格组件，最后才改示例的锚点、光效、字幕与大象。

## Goals / Non-Goals

**Goals:** 让运动与字幕效果可在任意代码场景复用；让《样本》的转场由对象延续而非整屏叠化；让光效有可见来源且克制；让大象可辨识、三个取样窗是同一几何的真实局部；保持逐帧确定性与原有时间结构。

**Non-Goals:** 不改变共享旁白字幕层、composition 跨幕转场、v8 字段、制作门或导出条件；不重做参考片；不把示例数字说成真实统计结论；不为 Canvas 绘制层新增 API。

## 外部方案检索

| 候选 | 版本/许可 | 结论 |
|---|---|---|
| `svg-path-properties` | 2.2.0 / MIT | 引入。纯 JS、无 DOM/计时器，按弧长采样任意 SVG path |
| `perfect-freehand` | 1.2.3 / MIT | 引入。纯几何，按压力生成锥形手绘描边 |
| Lucide Lab `elephant` | `@lucide/lab` 0.7.0 / ISC | 引入路径数据作几何基底；补象牙；不新增运行时依赖 |
| `@remotion/motion-blur` | MIT | 不引入。依赖 Remotion `<Freeze>`/`useCurrentFrame`，代码场景是普通 React 页 |
| `tsparticles`、`burst-particles`、`@usefy/confetti` | MIT | 不引入。依赖 rAF/真实时间，不能按帧确定性求值 |
| `reveal-text`、`sight-anim-text` | MIT/ISC | 不引入。依赖 IntersectionObserver、GSAP/Motion 或 CSS 动画 |
| `roughjs` | MIT | 不引入。偏 sketchy，与干净手绘线不一致 |
| `flubber`、`d3-interpolate-path` | MIT | 不引入。本片用锚点交接，不做拓扑形变；flubber 已长期未维护 |
| `d3-shape` | ISC | 暂不引入。现有 `proof-chart.smoothPath` 已覆盖需求 |

结论：路径采样与手绘笔触用外部纯库，大象用外部图标路径；光轨、爆散、扩散环与字幕错峰没有满足逐帧确定性的外部组件，在通用层实现纯数值原语，并在本文件与 `SOURCES.md` 记录检索结论。

## 分层

### 通用（`web/src/code-scene`）

- `random.ts`：`hashSeed`、`seededRandom`、`random01`，FNV-1a + mulberry32。
- `dynamics.ts`：`samplePath`、`sampleTrail`、`burstField`、`expandingRings`、`dissolvePair`、`staggerReveal`，以及点列长度、沿折线取点与多边形路径工具。
- `subtitles.ts`：`activeScreenSubtitle`、`splitScreenSubtitle`、`screenSubtitleEnvelope`、`splitEmphasis`。
- 全部只接受 `progress`/帧推导出的 0–1、显式种子与缓动；端点透明；不读挂钟、`Math.random`、上一帧或外部资源。

### 风格（`styles/dark-proof`）

- `light-trail`：`sampleTrail` + `perfect-freehand` 的锥形尾迹、头部径向光晕与尾尘。
- `burst`：`burstField` + `expandingRings`，共享径向渐变，加法混合；粒子与环数受 tokens 限制。
- `shock-ring`：只画扩散环，支持虚线与旋转 dash。
- `screen-subtitle`：逐字展开（未轮到的字全透明）、英文延迟、关键词高亮、`rise/settle/wipe` 进场与 `drift/dissolve/mask` 出场。
- `counter`：2–3 层延迟残影；`hand-drawn-line`：锥形笔触。

### 视频（`styles/dark-proof/examples/sample`）

- `FieldAnchor`、`GoldAnchor`、`LightEvents` 三个持续层；局部幕只负责自己的内容。
- 转场：旧层 14 帧 `easeOutCubic` 退出，新层晚 2 帧、14 帧进入；旧层 8 帧内降到 0.15 以下；600 帧保持硬切，只加单环与局部光。
- 大象：Lucide Lab 路径 + 象牙 + 眼；耳、身体、腿、卷鼻分批生长；三个取样窗用同一 `<g>` 的 `<use>` + `clipPath` + 局部缩放，窗心由引线指向真实部位。

## 决策

- **锚点而非整屏溶解**：对象延续让观众跟住 3 个金点，避免两张全亮画面叠放。
- **光效克制**：光只服务状态变化；硬切处不放粒子；每拍至多一个焦点。
- **外部库只进 SDK**：第三方 import 只出现在 `web/src/code-scene`，风格组件的导入闸门仍只允许 react/m2v/./。
- **大象用成熟图标而不是继续手搓**：Lucide Lab 的侧视轮廓已经包含耳、眼、卷鼻与四腿；象牙与取样窗是视频专属补充。

## Risks / Trade-offs

- 外部库打包兼容：已由 `tsc`、Vitest 与 `build_scene` 验证；若后续打包器变化，SDK 的显式导出是唯一适配点。
- 逐帧确定性：新增原语不使用时间源；`burstField`/`expandingRings` 端点透明；测试覆盖重复求值、跳帧与种子。
- 性能：点阵仍单 path；爆散 ≤22 粒子；环 ≤3；光轨 ≤14 采样；字幕逐字 span 数量受 30 字上限约束。
- 字幕量测：逐字 span 不改变 `textContent`、换行、字号与安全区；外层保留 `data-m2v-role`。
- 旧证据失效：旧「平涂无光晕」指标、并排图、冷审结论必须重测重审。
