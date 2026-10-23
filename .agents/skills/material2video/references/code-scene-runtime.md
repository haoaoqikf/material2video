# 代码场景运行契约

> **适用范围：** 本文描述画面实现与渲染/量测脚本之间唯一的接口：契约页（`version: 6`）、
> `window.__M2V__` 的必需接口与 `ready()` / `seekToFrame()` 语义、画面源码的确定性、
> 代码场景的顺序逐帧采集、电影级后期与镜头，以及 lookdev 原生关键帧。渲染引擎、打包、
> 字幕量测与成片编码见 [渲染引擎](render-engine.md)；分镜结构见 [通用分镜 v8](storyboard-schema.md)，
> 设计令牌见 [设计令牌](design-tokens.md)，制作顺序见 [制作流程](production-workflow.md)。
> v3/v4 的共享动画、场景树、节拍运行时与 `version: 3/4` 契约页已随旧子系统删除，本文不再描述。

画面实现与渲染/量测脚本之间只有这一个接口。只要画面实现满足本契约，渲染脚本就能把它
导出为 MP4；反过来，任何一项不满足都会在开渲前报错，而不是产出一段有问题的视频。

## 契约的唯一提供者

画面契约由**契约页**提供：`web/dist/contract/contract.html`，由 `pnpm -C web build`
从 `web/src/contract/` 构建。它把共享 React composition（`ArticleExplainer`）挂进
`@remotion/player`，暴露 `window.__M2V__`（**version 6**）。作品参数（准备产物）由查询参数
`m2v-storyboard` 给出（本地静态服务提供），因此这一个页面能服务任意作品——作品不需要自己的 HTML。
字幕量测（preview / render 内部）用 Playwright 驱动它；
渲染不走它，而是直接从 composition 源码打包渲染（见 [渲染引擎](render-engine.md) 的「渲染引擎与打包」）。

## 必需接口

### 评审输出的全局帧范围与缩放

片段检查与量测使用 `m2v preview --project <目录>`，默认前十秒，支持起止时间且拒绝全片。旧 `general samples` / `general rehearsal` 已移除。正式 render 不依赖预览，候选只生成一次，验收后交付同一文件。
帧范围、媒体时轴与缩放由类型内部渲染器统一处理，正式导出仍须经
`m2v render --project <目录>` 渲染完整时间轴并保持原分辨率。

画面实现必须在 `window` 上暴露 `__M2V__` 对象。契约页（version 6）的字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `version` | `number` | 契约版本，当前为 `6` |
| `fps` | `number` | 帧率，必须与准备记录一致 |
| `width` | `number` | 画面宽度，必须与准备记录一致 |
| `height` | `number` | 画面高度，必须与准备记录一致 |
| `durationInFrames` | `number` | 总帧数，必须等于准备产物派生的全片时长（通用 v8 由逐段实际配音编译，上限 36000 帧） |
| `ready()` | `() => Promise<void>` | 资源就绪后 resolve |
| `seekToFrame(frame)` | `(frame: number) => Promise<void>` | 把画面切换到第 frame 帧，绘制完成后 resolve |
| `currentFrame()` | `() => number` | 只读诊断：Player 当前实际帧号，不参与求帧判定 |

`frame` 从 `0` 开始，最大值是 `durationInFrames - 1`。

## ready() 的语义

渲染脚本在加载页面后调用一次 `ready()`，并等待它 resolve 才开始截图。
version 6 的 `ready()` 必须保证：

- 字体已加载完成（否则首帧会用回退字体排版，且首帧与后续帧字宽不一致）；
- **Player 已经挂载**（契约页要求挂载之后才能 seek，否则只会得到空画面）；
- 第 0 帧已经绘制过至少一次；
- 画面里出现的本地图片已经解码完成，否则后截的帧才会拿到图片。

契约页的实现（`web/src/contract/bridge.ts` 与 `explainer.tsx`）：等字体 Promise（与渲染入口
`web/src/index.ts` 里 `delayRender` 等的是同一个）、把 Player 定位到第 0 帧并等画面落定，
再等全部 `document.images` 解码完成。这样预览、量测与导出用的是同一份字体和同一批已就绪资源。

## seekToFrame() 的语义与确定性要求

`seekToFrame(frame)` 必须是**由帧号推导画面的纯函数**。这是逐帧渲染能够成立的
唯一前提。

必须做到：

- 画面只由传入的 `frame` 决定，与调用次数、调用顺序、真实时间无关；
- 对同一帧重复调用得到完全相同的画面；
- 返回的 Promise 在画面更新完成后才 resolve。

必须避免：

| 禁止项 | 原因 |
| --- | --- |
| CSS `animation` / `transition` | 由浏览器时钟驱动，与截图时刻无法对齐，会闪烁或丢帧 |
| `Date.now()` / `performance.now()` | 同一帧在不同时刻渲染出不同画面 |
| `Math.random()` | 每次渲染结果不同，重播不可复现 |
| 依赖 `requestAnimationFrame` 累积状态 | 截图期间帧数不确定 |
| `setTimeout` 驱动的动画 | 与帧号脱钩 |
| 未等待的网络请求 | 后截的帧可能才拿到数据 |

允许：CSS `transform` / `opacity` / 颜色等**静态样式**，只要它们的值由 JS 按帧计算后写入。

> 判断标准：把第 300 帧连续渲染两次，两次截图应该一致。

实测口径：Chromium 无头模式下对同一帧重复截图，**偶发**极少数像素相差 1 个色阶
（抽查 6 帧命中 0–2 帧，PSNR 79–111 dB）。这是光栅化噪声，不是画面逻辑问题——
未改动的画面同样复现，且与帧号无关。所以验收按「编码后不可见」判定，而不是逐字节相等；
需要拦下的是**整块元素的位置或透明度不同**，那类差异的 PSNR 会远低于 60 dB，
因此 `PSNR ≥ 60 dB` 是判定同帧一致性的阈值。当前没有自动抽帧比对同帧的命令，
确定性由下面的源码闸门与源码指纹保证。

### 画面源码的确定性

React 路径没有「渲染前扫描网页 HTML」这一步：画面由 composition 源码决定，
契约页的 HTML 里只有一个挂载点与一个入口脚本，照旧按 HTML 查会连「组件库」
都找不到，报出来的全是假问题。确定性的结论由两处承担：

- 组件源码里**不出现**时间源与随机源（`Date.now` / `performance.now` /
  `Math.random` / 计时器 / 未关闭的 CSS `animation`）：打包前由静态源码闸门
  （`src/m2v/core/source_policy.py`）扫描 composition 的全部可达源码，命中即失败
  并报出文件与行号；动效一律从 `useCurrentFrame()` 推导；
- 布局量测与成片验收照常运行（见 [渲染引擎](render-engine.md)），成片仍要过上面的确定性验收。

### 代码场景的顺序逐帧采集

作品 `scenes/` 下的 TSX 不进入 composition，其动画在检查或正式生成时由独立录制页
（`web/src/code-scene/`）采集。内部接口 `start()` 后只接受连续的
`advanceToFrame(n)`，从第 0 帧到 `durationInFrames - 1`；不支持倒序或跳帧。

录制页在作品加载前安装受控 Date/performance、定时器和 RAF 时钟。每帧上下文时间为
`n / fps`，React 提交、动画库回调、Three.js 绘制、CSS 动画定位及本地视频解码完成后
才截图。截图、PNG 落盘和机器负载不会推进作品时间。资源加载与宿主超时使用真实时间。
Motion、GSAP、ECharts、R3F 使用该时钟；作品仍使用 `useSceneContext()`，不新增录制配置。
视频按作品 play/pause、入点、播放速率和循环设置同步到受控时间，原声不进入片段。

作品可以在 `look.motion` 声明**运动模糊与 SSAA**：hero 镜头内的每一帧按
`(frame + k / subframes) / fps` 依次推进 `subframes`（1–4）个子帧，宿主把同一帧的 React 状态、
三维绘制、动画库、CSS 动画与本地视频都停在这些真实时刻上，Python 侧再把子帧等权平均成一张
输出帧（`mix`，等权归一化）。`supersample: 2` 时按 2 倍设备像素截图、编码时用 lanczos 降采样
回目标画幅。子帧时间仍然只前进不后退，因此同一帧在任意一次录制里都可复现；未声明 `motion`
时配置与缓存键与既有一致。

作品绘制实际横竖画幅的完整不透明画布，重要内容避让 `subtitleSafeArea`；共享层只叠加字幕。
系统只开放已登记媒体和仓库字体，阻断外网及 WebSocket，打包仍只批准文档列出的共享依赖
（含电影级后期所需的 `postprocessing` 与 `@react-three/postprocessing`；依赖缺失时在打包前
明确失败，不会静默渲染成没有后期的画面）。
字体、组件与显式资源未就绪、运行异常或逐帧绘制超时均使 prepare 失败，不发布有效缓存。

### 共享动效原语

`web/src/code-scene/primitives.ts` 提供五类只做数值映射的共享原语，作品从 `m2v/code-scene`
导入：

| 原语 | 输入 | 输出 |
| --- | --- | --- |
| `rollNumber` | 起止值、进度、小数位、调用方缓动、可选千位分隔 | 数值与可直接绘制的文本 |
| `growSeries` | 数据序列、进度、基础值、调用方缓动、可选 `stagger` | 生长后的数值与每点生长比例 |
| `scrollList` | 行数、行高、视口、进度、调用方缓动、可选 `overscan` | 偏移量与可视行索引、纵坐标 |
| `interpolateState` | 若干同字段数值状态、进度、调用方缓动 | 插值后的状态对象 |
| `particleField` | 数量、进度、显式种子、原点、扩散、寿命、尺寸 | 每个粒子的位置、尺寸与透明度 |

- `progress`（0–1）是唯一时间输入；原语不读挂钟、帧号、上一帧状态、视频或外部资源，
  相同进度与参数每次求值相同。跳帧采样与逐帧推进得到同一结果。
- 原语不内置视觉主题：不返回颜色、字体或线宽，这些由调用方在绘制时决定；缓动可传，
  缺省为恒等。粒子随机性只来自显式 `seed`，缺省使用固定种子。
- 原语不能用于关闭信息推进、母题可信度或版式重复问题，也不提供绕过复核的默认表现。
- 原语属于共享渲染资产：`implementation_inputs()` 递归收集 `web/src/code-scene/` 下的
  `.tsx`、`.ts` 与 `.js`，修改原语会使引用作品的片段缓存与准备指纹失效，必须重新准备并复查。
- 单元测试在 `web/src/code-scene/primitives.test.ts`，覆盖重复求值、跳帧一致性、种子、
  0 与 1 边界；`tests/test_motion_primitives.py` 另检查实现指纹与确定性源码闸门。

### 电影级后期与镜头

`PostFX` 只作用于 canvas，不影响共享字幕 DOM 层。全部后期参数由 `elapsedSeconds`/帧号驱动：
颗粒使用「镜头 id 哈希 + 帧号」的自带确定性效果，`EffectComposer` 关闭 MSAA
（`multisampling={0}`），不使用库里依赖 `Math.random` 生成噪点纹理的 `Noise`。
`CameraRig` 的位置、朝向、FOV、滚转与曝光同样只由帧号算出；`pathIntersectsSphere`、
`cameraPathRisk` 与 `backgroundRisk` 在作品侧提供穿球与背景裁切的纯函数检查。

作品不引用这些元件时画面与既有一致：真实浏览器验证「把套件从 SDK 导出里摘掉后，
标准画面逐像素相同」，且 look、shots 与 `claims` 只在非默认时进入片段缓存键。

连续编号 PNG 直接按 60 fps 编码为实际画幅的无声视频，输入与解码帧数必须精确一致；
不使用 fps 重采样或尾帧复制掩盖缺失状态。缓存绑定源码、参数、时间窗、画幅、字幕几何、
媒体摘要、依赖、浏览器和受控时钟实现；旧实时采集缓存失效。检查和正式生成按区间复用录制缓存。
顺序采集不等于任意作品可随机求帧或逐像素复现；浏览器量测仍只检查共享字幕，
不会自动识别作品正文和主体遮挡。

## lookdev 原生关键帧

`m2v lookdev` 重新构建当前代码场景，从第 0 帧连续推进到选定帧，仅保存关键帧，
不录制完整成片。逻辑画幅不变，采集配置的 `captureScale: 2` 使 SDK `Canvas`
及 `Chart` 原生绘制 2 倍像素；普通录制未声明时继续使用作品原有设置。
自定义 canvas 必须按该像素密度分配后备缓冲，像素不足会明确失败，不以放大代替。

关键帧以 PNG 进入共享 composition，按全片时间叠加字幕及转场，横屏输出
3840×2160（竖屏为 2160×3840）；有声作品的样片复用准备片段与母版音轨，无声作品输出无音轨样片。
`outputs/lookdev.json` 的 `stillCapture: native-code-png-v1` 表示原生采集路径，
记录准备指纹和实际输出尺寸。旧放大静帧不能作为原生 4K 细节的验收证据。
