# 布局盘点与评估记录

## 状态

实施与验收完成。候选包未采用；保留现有 DOM 度量，增加 tree v4 字体后全片预检、四行上限、K7 诊断和镜头实测几何。以下盘点来自源码与列明的浏览器/渲染实测。

## 工具链与对象盘点

- Remotion 全部锁定 `4.0.526`；隔离候选版本 `@remotion/layout-utils@4.0.526` 可从配置的包源解析（`pnpm view` 返回 `4.0.526`）。官方 API 含 `measureText`、`fillTextBox`、`fitText`、`fitTextOnNLines`，且官方要求测量前等待字体就绪。候选包未安装到正式依赖。
- `web/src/primitives/SceneTree.tsx`：tree `text` 节点取 `data.*` 文案；`TextPrimitive` 只在预设开启且声明 `role` 时，挂载后用 span `scrollWidth` 对比父容器 `clientWidth`，按 `hero → headline → title → body → label → caption` 降档。没有记录最低档仍溢出的 `data-a2v-fit-fits=false`，且 `fitRoleDown` 仍把不适配报告为 `measured: true`。测量只查宽度，不负责行数/高度、内边距、强调片段或稳定容器尺寸。当前三个固定示例均使用 code renderer，故该路径不被它们覆盖。
- `web/src/fonts.ts`：`ensureFonts()` 注册字体并等待 `document.fonts.ready`；`web/src/index.ts` 通过 Remotion `delayRender` 等待它，契约页也在 `contract/bridge.ts` 等待。字体就绪链路已有保护；剩余问题是布局测量与镜头几何是否消费相同结果。
- `web/src/runtime/geometry.ts`：按 tree 结构平均分配归一化盒，radial/cycle 使用固定比例；不读内容、字体、实际尺寸或 DOM。`cameraV4.ts` 在 composition 首次渲染前调用 `compileCameraV4`，reframe 只消费上述估算盒。
- `web/src/code-scene/index.ts` 的 `probe({node, inside, geometry})` 提供 code 场景测量标记与作者声明几何。`web/src/code-scene/api.test.tsx` 覆盖其输出。`.agents/skills/article2video/scripts/a2v/inspect.py` 只量显式 `data-a2v-inside` 的文字/形状包含关系；`.agents/skills/article2video/scripts/a2v/keynote.py` 对无适配元素会跳过容器溢出门禁。
- 固定示例清单：`buffer-smoothing`（objects: inlet/tank/outlet/overflow，code module `water-tank`）、`darts-trial-and-error`（player/dart/target，`darts-trial-and-error`）、`keynote-baseline`（map/routes，`option-map`）。三者没有 tree sceneTree；代码场景文案及 probe/字号位于对应 `examples/*/scenes/*.tsx`。

## 历史四处缺口核对

规划文档中的“双向选择节点、冰山标注、天平载物、阶梯柱顶注”是旧作品/旧设计记录，不是固定三个示例的当前 v4 object ID。逐份解析现有三份 storyboard 的 `world.objects` 并检查代码模块后，这四种对象均没有对应对象或当前组件。因此本次不能据历史名目声称它们仍有缺陷；须以新发现的当前对象作适配目标。

## 已知架构差异

文字取档发生于浏览器挂载后的 `useLayoutEffect`；镜头几何与轨迹在 React render 前同步编译。候选测量也要求字体先就绪。用户已选择调整渲染时序：由 composition 在 Remotion 延迟句柄内等待字体并挂载布局预检树，测量各文案边界的节点画布盒，传给相机编译，再开始交付帧。实现与性能尚未验证。此方案不改变 code scene 公共 `probe` 几何路线。

## 同机环境

2026-10-10，Windows 11、Node `v22.23.2`、pnpm `10.15.0`、Remotion `4.0.526`、Playwright Chromium `153.0.8010.12`。字体为仓库 Noto Sans SC Variable。候选包安装在 `%TEMP%/a2v-layout-utils-4.0.526` 隔离目录，正式 `web/package.json` 与锁文件未变。

## 输入及候选包比较

在 520px 宽度、40px Noto Sans SC、三行上限下，对中文长句、标点/引号、中英混排、数字单位、强调片段文字及动态文案逐项比较 `@remotion/layout-utils` 与 Chromium DOM 行数/尺寸：

| 输入 | 候选字号 / 行数 | Chromium DOM 行数 | 结果 |
| --- | ---: | ---: | --- |
| 中文长句 | 14.05px / 1 | 3 | 失败；低于项目 28px 最小档 |
| 标点与引号 | 15.07px / 1 | 3 | 失败；低于项目最小档，断行不同 |
| 中英混排 | 40px / 3 | 3 | 行数相同 |
| 数字单位 | 40px / 3 | 3 | 行数相同；逐片段 `fillTextBox` 仍需由项目切分规则驱动 |
| 强调片段（纯文案基线） | 19.25px / 1 | 3 | 失败；API 单一字重测量不能直接表达 DOM 强调片段 |
| 动态长文案 | 20px / 1 | 2 | 失败；低于项目最小字号 |

候选包官方说明其 measure API 只在浏览器运行、需字体加载后调用；`fitText` 主接口按给定宽度计算单一字号，`fitTextOnNLines` 另有行切分。实际测试中连续中文行被作为单行，低于当前字号阶下限；需要另写项目级中文/强调分段算法才能修补。当前 DOM `scrollWidth` 加实测盒预检已能准确捕获浏览器实际换行，并消除单独重复测量的价值。故不采用候选依赖，正式依赖不变。参考 [官方 API](https://www.remotion.dev/docs/layout-utils)、[measureText](https://www.remotion.dev/docs/layout-utils/measure-text)、[fillTextBox](https://www.remotion.dev/docs/layout-utils/fill-text-box)、[fitText](https://www.remotion.dev/docs/layout-utils/fit-text)、[fitTextOnNLines](https://www.remotion.dev/docs/layout-utils/fit-text-on-n-lines) 与[字体加载建议](https://www.remotion.dev/docs/layout-utils/best-practices)。

## 运行时实现与基准

采用现有 DOM 方案：tree v4 composition 在字体等待句柄内按阶段、状态轨道边界挂载同尺寸预检树，求各对象在可达文案中的并集几何；相机先用该 map 编译再释放句柄。字号取档检查实际宽度及最多四行，最低档仍超宽/超行、或文字越过安全区或 surface 内边距时写入 `data-a2v-fit-fits=false`，由现有 K7 正式门禁阻断并报告对象 ID。树文字直接声明其最近 surface 的 `data-a2v-inside`，探针同时支持 HTML DOM 与 SVG geometry。code renderer 继续用公开作者几何。

三轮暖缓存的同一临时 V4 tree 分镜、1080×1920、单 Chromium 并发、仅输出 2 帧比较：

| 路线 | 三轮耗时（秒） | 中位数 | 峰值进程树 RSS（MB） | 中位数 |
| --- | --- | ---: | --- | ---: |
| 基线静态 tree geometry | 6.642 / 6.633 / 6.603 | 6.633 | 1282.5 / 1251.8 / 1270.0 | 1270.0 |
| 字体后布局预检与实测几何 | 6.546 / 6.516 / 6.492 | 6.516 | 1172.4 / 1170.8 / 1249.1 | 1172.4 |

此两帧样本的中位耗时改善 1.8%，峰值 RSS 中位数改善 7.7%；它只能表明预检没有在该样本引入 10% 退化，不能代表长片或高数量状态轨道。真实 Remotion Chromium 导出与契约预览的同一 tree 首帧比较通过 PSNR ≥35dB；测试还覆盖深浅主题下 360×640 安全区包含、阶段文案切换与后段到前段寻帧。三种 code renderer 仍由既有代码场景回归和公开 probe 几何覆盖，不改变其几何来源。

当前验证：`pnpm -C web test` 176 项通过，`pnpm -C web build` 通过；相关 Python 浏览器、字号/K7、探针、代码场景、三个固定示例、金融回归与 Remotion 导出测试共 148 项通过、1 项跳过、1 项按 `not slow` 排除；Remotion 首帧对比单测另行通过。`openspec validate ... --strict` 与注册表同步检查通过。Windows pytest 临时目录清理在进程退出时会报告既有 `pytest-current` ACL `PermissionError`，测试本身退出码为 0。

剩余边界：性能基准只有同机 2 帧窄样本，未代表长片的冷启动或大量状态轨道；预览/导出同帧图像验证覆盖首帧，非顺序求帧由契约测试验证字号/布局标记和镜头值，不宣称逐帧像素测试。三个固定示例全是 code renderer，因此 tree DOM 预检由临时 v4 tree 夹具验证。
