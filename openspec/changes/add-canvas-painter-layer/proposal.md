## Why

通用代码场景目前有两条绘制路径：React + SVG/DOM（共享 composition 与风格包组件），以及 three/R3F（三维与 WebGL）。缺少中间一档——2D Canvas。辉光、粒子、线条生长与逐字显影这类质感镜头，用 DOM/SVG 做要么性能不够（数百粒子每帧重排），要么辉光要靠多层渐变硬叠；用 three 做则过重。外部参考项目用一张 1920×1080 的 2D canvas 加一次出帧（缩小两次、模糊、加法叠回）就解决了这类画面。

更实际的问题是量测。仓库里唯一用 Canvas 的真实作品（`videos/general/earth-night-lights/scenes/earth.tsx`）没有任何 `data-m2v-role` 标记，`__M2V_REVIEW_STATE__` 在全部作品与示例场景中零命中。这类画面在检查点量测里只能得到"观测范围：未验证"。绘制层若不同时解决量测通路，引入它就是拿技术换质量下降。

## What Changes

- 在 `web/src/code-scene/painter/` 新增可选 2D Canvas 绘制层：绘制原语（光、线、形、字、分组与合成）、出帧管线（底、内容层、辉光、颗粒）、React 绑定。
- 绘制层**必须**同时输出量测代理：从同一份绘制数据渲染透明的 `data-m2v-role`/`data-m2v-state` 元素并提供 `__M2V_REVIEW_STATE__` 状态，使检查点量测能读到与画面同源的几何与文字，而不是保持未验证。
- 绘制层按 `captureScale` 分配画布后备缓冲，使 lookdev 的 2 倍原生采集可用。
- 绘制层纳入确定性源码闸门的测试扫描，并计入实现指纹。
- 在运行时契约与分镜文档中说明使用方式、量测代理约定与边界。
- 不新增第三方依赖；不改动既有 SVG/DOM 与三维路径；不改动共享字幕层；不改变默认画面。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `react-code-scenes`: 代码场景新增可选的 2D Canvas 绘制层，并规定其必须提供同源的 DOM 量测代理与状态探针、按采集像素密度分配后备缓冲、受确定性源码闸门与实现指纹约束；既有逐帧录制、媒体解析与电影级接口条款不变。

## Impact

影响 `web/src/code-scene/painter/`（新增）、`web/src/code-scene/sdk.tsx`（导出）、`tests/test_motion_primitives.py` 或新增测试（源码闸门扫描范围）、`tests/` 下的量测代理有效性测试，以及 `references/code-scene-runtime.md` 与 `references/storyboard-schema.md`。

新增文件位于 `web/src/code-scene/` 会自动进入 `implementation_inputs()`，因此既有作品的准备指纹与录制缓存键会失效，需重新 prepare。这是预期行为。

`web/src/index.ts` 不引用 `web/src/code-scene/`，生产链路不会扫描该目录的确定性，因此闸门须由测试守住。产物目录与清理规则不变。不修改分镜 schema、审核轮次、导出门禁或既有作品。
