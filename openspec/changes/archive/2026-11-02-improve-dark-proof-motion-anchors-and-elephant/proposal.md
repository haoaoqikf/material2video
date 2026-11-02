## Why

《样本》已经能讲清 3/1000、33 点摆动、唯一硬切、均值回归与标准误，但视觉执行仍落后于参考片：对象移动与爆散缺少光效，字幕只有整句淡入淡出，转场靠两层整屏 opacity 叠放、观感接近硬切或重影，大象轮廓不像象。用户要求修复这四点，并先把可复用的算法提取为通用能力，再按「通用原语 → 风格组件 → 视频专属」分层。

用户同时新增规则：新增动效或可视化组件前必须先检索外部成熟方案，能在逐帧确定性约束内引入的优先引入，禁止未检索直接手写。本变更已先完成检索并记录取舍。

## What Changes

- 通用代码场景新增 `random.ts`、`dynamics.ts`、`subtitles.ts`：固定种子、路径等距采样、光轨、爆散、扩散环、互补溶解、逐字错峰、字幕窗口与两行切分。全部是纯数值函数，只接收显式进度、种子与缓动。
- 引入 MIT 许可的 `svg-path-properties@2.2.0` 与 `perfect-freehand@1.2.3`，由 `m2v/code-scene` 显式导出，作品与风格组件不直接导入第三方包。`@remotion/motion-blur`、`tsparticles`、`reveal-text`、`roughjs`、`flubber` 等候选因运行环境、真实时间依赖、风格不合或停止维护而不引入。
- `dark-proof` 风格包新增 `light-trail`、`burst`、`shock-ring`，升级 `screen-subtitle`（逐字展开、英文延迟、关键词高亮、三种进出场）、`counter`（数字残影）与 `hand-drawn-line`（锥形笔触）；`tokens.json` 增加光效与字幕运动参数；版本升为 1.1.0。
- 《样本》改为持续锚点转场：1000 点阵与 3 个金点跨拍保留，金点在圆片顶、样本点、趋势点、取样窗与标准误标记之间交接；局部内容旧层快速退出、新层稍后进入，唯一硬切仍固定在 600 帧。
- 光效按事件加入：轨迹光轨、评价翻转小爆散、线溶解与全象揭示爆散、扩散环、n=1000 与结尾回扣；800 帧以内每拍至多一个光效焦点。
- 大象改用 Lucide Lab `elephant`（ISC，`@lucide/lab@0.7.0`）的路径作为几何基底，补象牙；三个取样窗改为同一轮廓的真实局部放大，不再画通用纹理。
- 同步 GUIDE、DESIGN、SOURCES、PROJECT_PLAN、skill 参考文档、测试与 OpenSpec 主规格。

不改变视频类型、CLI、v8 schema、共享旁白字幕层、composition 跨幕转场、制作门与导出条件；不改 1740 帧、八拍事件、13 条字幕窗口与 DESIGN 检查点窗口。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `scene-motion-primitives`: 新增轨迹、爆散、扩散环、互补溶解、逐字错峰与字幕窗口原语；明确外部纯库的引入与边界。
- `react-code-scenes`: 代码场景 SDK 导出新增的纯数值模块与外部纯函数，作品仍不直接依赖第三方包。
- `dark-proof-style`: 新增光轨/爆散/扩散环组件，升级字幕、计数器与手绘线；锚点转场、光效克制边界、真实局部取样与可辨识大象进入契约。

## Impact

- 新增 `web/src/code-scene/{random,dynamics,subtitles}.ts` 与对应 Vitest；`sdk.tsx` 导出扩展；`web/package.json` 与锁文件新增两个 MIT 依赖。
- 修改 `styles/dark-proof/` 的组件、tokens、manifest、GUIDE、《样本》场景与文档；示例 `outputs/` 全部重做，旧「平涂无光晕」证据失效。
- 修改 `tests/common/test_motion_primitives.py`、`tests/works/examples/test_dark_proof_style.py`；其余风格与示例不回归。
- 参考片仍只作并排基准；Lucide Lab 只取路径数据，不新增运行时依赖。生成媒体与 `outputs/` 不入库。
