# 代码场景运行契约

> **独立工程 v3**：作品在自己的 `src/code-scene/` 使用逐帧接口，以本地源码、锁文件、字体和资源运行，不解析 `m2v/*`。本页列出的 `web/src/` 能力是可采用的参考源码；使用时递归携带依赖、样式和资源到作品，再按相对路径导入。恢复与构建见[独立工程说明](../../../../templates/standalone/README.md)。

完整分镜准备之前的代表性原生试制使用 `m2v sample capture/serve/deliver`，复用本页构建、受控采集与编码；依赖扩展、资源加载器、网页预览及完成条件见[网页原生样品](design-samples.md)。该入口不代替正式全片准备与验收。

> **适用范围：** 本文描述画面实现与渲染/量测脚本之间唯一的接口：契约页（`version: 6`）、
> `window.__M2V__` 的必需接口与 `ready()` / `seekToFrame()` 语义、画面源码的确定性、
> 代码场景的顺序逐帧采集、电影级后期与镜头，以及 lookdev 原生关键帧。渲染引擎、打包、
> 字幕量测与成片编码见 [渲染引擎](render-engine.md)；分镜结构见 [统一分镜 v9](storyboard-schema.md)，
> 字体和参考令牌边界见下方专节，创作顺序见[研究与试制](stage-research.md)。
> v3/v4 的共享动画、场景树、节拍运行时与 `version: 3/4` 契约页已随旧子系统删除，本文不再描述。

画面实现与渲染/量测脚本之间只有这一个接口。只要画面实现满足本契约，渲染脚本就能把它
导出为 MP4；反过来，任何一项不满足都会在开渲前报错，而不是产出一段有问题的视频。

## 契约的唯一提供者

画面契约由作品自己的 `contract.html` 与 `src/contract/` 提供，构建和准备由作品本地入口执行。它挂载本地 `SceneFilm`，暴露 `window.__M2V__`（**version 6**）；参数由本地服务提供。录制页面与合成实现、字体和媒体都属于作品，不借用主项目构建产物。正式渲染入口见[渲染引擎](render-engine.md)。

## 字体与缺字检查

作品的 `src/assets/fonts.json` 声明实际注册字体，来源、版本、摘要、许可及恢复目标在作品 `fonts/registry.json`；按作品 `fonts/fetch.py` 恢复。构建前由本地同步脚本校验源文件、摘要和路径，缺失或漂移明确失败，不静默回退系统字体。字体二进制不入库，许可文本保留。

准备/场景配置按实际登记字体检查会渲染的文本，并提取作品 `scenes/**/*.tsx` 的源码字面量作为静态覆盖补充，定位到字段或相对路径。口播文本本身不等于画面文本。静态提取不是对动态拼字、任意依赖或所有字体选用的完备证明；本片使用的具体字族、字重、字宽和排版仍须用实际画面复核。不能借另一支字体有字形就宣称所用字体正确。所有字体与异步排版在 `ready()` 前就绪。

字幕几何与默认样式以作品 `src/frames.json` 为准；主项目参考是 `web/src/frames.json`，不要抄进令牌和量测常量。字幕参数见[字幕契约](prepared-and-subtitles.md#作品级字幕字号)。

## 参考源码的设计令牌

`web/src/styles/tokens.css` 服务于主项目参考组件，值和用途在源码维护；不是所有独立作品的调色板、字号、画幅或单强调色规范。只有实际采用的组件才连同所需样式落入作品。作品自己的构图与美术由设计决定，字幕另遵守上一节契约。

参考令牌采用一个 `@theme static` 块，直接引用真实变量名，不增加同义别名或未被挂载的属性作用域。`static` 保证组件直接引用的变量也被输出；使用 Tailwind 任意值时保持完整类名。令牌层不保存运动时长，动画遵守[运动实现](#运动实现约定)。

已有数值、字阶关系和图形颜色分类分别由 `tests/common/test_design_tokens.py`、`tests/common/test_figure_contrast.py` 守护；分类和阈值以测试及 CSS 为准，不在指南复制数值表。参考图形颜色新增/调整须同步分类，半透明先合成再量对比度；实心、次级面与空壳保持区别。数据/必要边界与装饰的对比职责不同，面填充也不套用线条阈值。这些约束只适用于该参考实现，不强制其他风格照搬。

## 必需接口

### 评审输出的全局帧范围与缩放

片段检查与量测使用 `m2v preview --project <目录>`，默认前十秒，支持起止时间且拒绝全片。正式 render 不依赖预览，候选只生成一次，验收后交付同一文件。
帧范围、媒体时轴与缩放由类型内部渲染器统一处理，正式导出仍须经
`m2v render --project <目录>` 渲染完整时间轴并保持原分辨率。

画面实现必须在 `window` 上暴露 `__M2V__` 对象。契约页（version 6）的字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `version` | `number` | 契约版本，当前为 `6` |
| `fps` | `number` | 帧率，必须与准备记录一致 |
| `width` | `number` | 画面宽度，必须与准备记录一致 |
| `height` | `number` | 画面高度，必须与准备记录一致 |
| `durationInFrames` | `number` | 总帧数，必须等于准备产物派生的全片时长（统一 v9 由逐段实际配音编译，上限600秒，即30 fps为18000帧、60 fps为36000帧） |
| `ready()` | `() => Promise<void>` | 资源就绪后 resolve |
| `seekToFrame(frame)` | `(frame: number) => Promise<void>` | 把画面切换到第 frame 帧，绘制完成后 resolve |
| `currentFrame()` | `() => number` | 只读诊断：Player 当前实际帧号，不参与求帧判定 |

`frame` 从 `0` 开始，最大值是 `durationInFrames - 1`。

## DOM/SVG 观测标记

DOM/SVG 标记用于定位对象与排查几何，不能证明最终像素的可见性或代替独立评审。
数字残影等有意重叠仍须查看实际帧与完整事件窗口；当前不填写已移除的检查点断言或重叠豁免。

本地 Chromium 量测中，SVG 分组或嵌套 SVG 的包围盒可能包含透明粒子、完整字形度量或超出
画幅的子图形。标题宜分别标记文字，避免把周围粒子一并当成文字外框。雪球等主体在正常
展示时仍须保持完整；满幅前景擦屏则可用实际的 HTML 裁剪窗口作为观测对象，窗口内的超幅
图形不再同时标为需要完整呈现的主体。单纯给 SVG 设置宽高不等于得到裁剪后的 DOM 外框。
窗口标记只描述可见范围，不能证明转场内容、遮挡或表达正确，仍须看完整过程。

修复这类问题时，先检查原失败帧及相邻边界，再查看完整事件窗口；局部探针和静帧不替代
当前范围的独立评审。本节不增加制作门。

## 幕内事件查询

五类作品的场景从 `CodeSceneProps.eventFrames` 取得 prepare 解析的本幕事件帧表；无事件时省略。用本地 `createSceneEvents` 查询，不在动画和声音中重复写同一时刻：

```tsx
const events = useMemo(() => createSceneEvents(config.eventFrames), [config.eventFrames]);
const frame = clock.elapsedSeconds * config.fps;
const approach = events.progress('contact', frame, 18, -18); // 接触前18帧开始，接触时完成
const count = frame >= events.frame('contact') ? 1 : 0;
const emphasis = frame >= events.frame('contact') ? 1 - events.progress('contact', frame, 6) : 0;
```

从 `react` 导入 `useMemo`，从作品 `../src/code-scene/events` 导入 `createSceneEvents`。`frame(id)` 对未声明事件明确抛错；`progress(id,currentFrame,durationFrames,offsetFrames=0)` 将结果夹到0–1，当前帧、持续帧和偏移须有限，持续帧须大于0。允许分数帧，纯求值不依赖上次调用，适合子帧采集。零时长状态直接比较事件帧。

事件表是初始化快照，建议每份配置只创建一次。事件只规定时刻，不触发回调、不自动模拟碰撞、不重排字幕与旁白。录制页仍顺序逐帧推进；纯事件函数可乱序求值不表示录制页新增随机 seek 能力。声明与音效定位见[幕内事件](storyboard-schema.md#幕内事件)。

事件发生前后的画面取证用 `m2v lookdev --event <sceneId:eventId> --before <帧> --after <帧> [--hold <帧>]`：窗口由作者显式声明，工具从当前准备记录解析事件并取 before/at/after/hold 四类帧。它是看图预览，不生成评审通过记录，也不替代独立过程观察；事件越靠后，顺序采集仍从所属幕第 0 帧推进，pure 场景则直接 seek。

## 全局时间与连续行为

跨幕连续的动作不应在每一幕各写一份。作品在幕的 `content.props.capture` 声明：

```json
{"timebase": "global"}
```

`scene_config` 随后注入本幕在全片时间轴上的 `timeline`
（`sceneStartFrame`、`sceneEndFrame`、`durationInFrames`），`useSceneContext()` 提供：

| 字段 | 含义 |
| --- | --- |
| `elapsedSeconds` | 幕内时间，语义不变 |
| `globalSeconds` | `sceneStartFrame / fps + elapsedSeconds`；未声明 global 时等于 `elapsedSeconds` |
| `globalFrame` | `sceneStartFrame + elapsedSeconds * fps`；子帧保留小数 |
| `sceneStartFrame` | 本幕全片起点；未声明时为 0 |

推荐写法是**一条状态轨迹 + 多个取景**：

```tsx
// 不接收幕 ID；位置、朝向、啄食、轨迹全部由全片时间决定
function act(t: number) { /* ... */ }

export default function Scene(config: CodeSceneProps) {
  const {elapsedSeconds, globalSeconds} = useSceneContext();
  const state = act(globalSeconds);
  // 镜头只决定取景，不改变 state
  // 分镜 content.props.shot 显式传入作品自己的镜头键；CodeSceneProps 没有 chapter。
  const shot = config.props.shot as keyof typeof SHOT;
  return <Room state={state} shot={SHOT[shot]} />;
}
```

上例须在分镜的 `content.props.shot` 声明作品自己的镜头键，并在 `SHOT` 中提供对应取景。

同一时刻在全景、近景、特写里读到同一 `state`，换镜不会跳位置或动作。`capture.timebase`
是 opt-in：未声明时录制配置逐字节不变，既有片段缓存继续复用；声明后
`sceneStartFrame` 进入片段缓存键，前幕时长变化会让该幕重新录制。需要任意帧直接定位与
分块并行时，再声明[纯时间采集](#纯时间采集opt-in)；全局时间本身不强制使用它。

## ready() 的语义

渲染脚本在加载页面后调用一次 `ready()`，并等待它 resolve 才开始截图。
version 6 的 `ready()` 必须保证：

- 字体已加载完成（否则首帧会用回退字体排版，且首帧与后续帧字宽不一致）；
- **Player 已经挂载**（契约页要求挂载之后才能 seek，否则只会得到空画面）；
- 第 0 帧已经绘制过至少一次；
- 画面里出现的本地图片已经解码完成，否则后截的帧才会拿到图片。

契约页的本地实现（作品 `src/contract/bridge.ts` 与 `src/scene-film/`）：等字体 Promise（与渲染入口
`src/index.ts` 里 `delayRender` 等的是同一个）、把 Player 定位到第 0 帧并等画面落定，
再等全部 `document.images` 解码完成。这样预览、量测与导出用的是同一份字体和同一批已就绪资源。

本地媒体服务支持 Range 跳转。浏览器 seek 或退出页面取消旧请求时，服务结束该传输而不打印断连堆栈；一般读取、权限与资源错误仍然报出。取消传输不代表素材就绪，逐帧采集仍须等待目标时刻的视频解码完成。

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
因此 `PSNR ≥ 60 dB` 是判定同帧一致性的阈值。`m2v lookdev --det` 可用两次独立采集核对
同帧一致性；pure 场景还会在采集时自动做正序/倒序探针。确定性仍由源码闸门与源码指纹保证。

### 画面源码的确定性

作品 TypeScript 检查应核实实际覆盖范围，可用 `tsc --listFilesOnly` 查看入口和依赖。
专属配置宜用 `files` 显式列出分镜入口，缺失入口会明确报错；Windows 路径使用 `/`，
避免过度转义的反斜线通配符空匹配后仍退出成功。覆盖 `paths` 时核实本地模块所需的资源别名和
已登记图表类型声明映射，再记录真实类型检查结果。

React 路径没有「渲染前扫描网页 HTML」这一步：画面由 composition 源码决定，
契约页的 HTML 里只有一个挂载点与一个入口脚本，照旧按 HTML 查会连「组件库」
都找不到，报出来的全是假问题。确定性的结论由两处承担：

- 组件源码里**不出现**时间源与随机源（`Date.now` / `performance.now` /
  `Math.random` / 计时器 / 未关闭的 CSS `animation`）：打包前由静态源码闸门
  （作品 `runtime/python/film_runtime/core/source_policy.py`）扫描 composition 的全部可达源码，命中即失败
  并报出文件与行号；动效一律从 `useCurrentFrame()` 推导；
- 布局量测与成片验收照常运行（见 [渲染引擎](render-engine.md)），成片仍要过上面的确定性验收。

### 代码场景的顺序逐帧采集

作品 `scenes/` 下的 TSX 不进入 composition，其动画在检查或正式生成时由独立录制页
（作品 `src/code-scene/`）采集。**未声明 pure-time 时**，内部接口 `start()` 后只接受连续的
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

### 异步绘制完成边界

`useSceneContext().waitForFrame(task)` 登记 `PromiseLike` 绘制任务，适用于异步 Bitmap、
GPU 积分、去噪或显式异步组件更新。宿主等待登记工作及其链式新增工作，再等待浏览器合成后
完成本帧或子帧；等待不推进作品时间，也不另行触发用户 RAF。同步场景不额外增加绘制屏障。
初始 `ready()` 会等待已登记工作和字体，多次调用只共用一份就绪任务；`start()` 触发的工作由
首帧提交等待。资源恢复和模型初始化仍应在 `ready()` 前完成。

```tsx
const {elapsedSeconds, waitForFrame} = useSceneContext();
useLayoutEffect(() => {
  waitForFrame(renderAt(elapsedSeconds)); // renderAt返回真实绘制完成的Promise
}, [elapsedSeconds]);
```

完整可运行示例见 [async-bitmap.tsx](../../../../tests/fixtures/code-scenes/async-bitmap.tsx)，
它通过 `OffscreenCanvas.convertToBlob()` 与 `createImageBitmap()` 完成原生异步绘制，并由
真实浏览器及原生编码测试覆盖。示例不新增视频类型或第八部作品。

非法任务、任务拒绝、同一宿主重叠提交会明确失败，未完成工作仍由既有就绪及逐帧超时终止。
不得在绘制实际结束前提前 resolve；未登记工作不会自动等待。状态必须仍由受控时间推导，
异步接口不豁免计时器、随机、外网或 pure-time 正反序检查，也不自动证明动态品质。
队列、宿主及受控时钟进入实现摘要，改动后旧准备、缓存及原生样品需按既有规则重新采集。

OIDN 去噪、路径追踪等可选能力不由共享依赖登记；作品采用时自行安装固定版本，并把依赖、补丁、权重来源、许可与恢复摘要写进自己的工程和锁文件。构建器只核对作品内实际安装的依赖；固定模型、块大小、样本及逐帧确定性仍须实际验证。

### 纯时间采集（opt-in）

只有画面完全由 `elapsedSeconds`、`globalSeconds`、`props` 与 `eventFrames` 推导的场景，
才可以在 `content.props.capture` 声明：

```json
{"mode": "pure-time", "jobs": 2, "blockFrames": 30, "verifyFrames": 4}
```

- `mode` 默认 `sequential`；`pure-time` 隐含 `timebase: "global"`。
- `jobs` 为 1–4（默认 1）；`blockFrames` 默认等于 fps；`verifyFrames` 为 2–4（默认 4）。
- `jobs/blockFrames/verifyFrames` 是运行时参数，不进入片段缓存键；`mode` 与
  `sceneStartFrame` 进入。未声明 pure 的作品配置、缓存与采集路径不变。

pure 模式允许绝对定位：录制页从块首帧挂载，`seekToFrame` 可跳帧与倒序；采集只遍历目标帧，
不再从第 0 帧推进。请求窗口会向外扩到 `blockFrames` 边界，块可缓存复用，也可由
`jobs` 个独立子进程并行采集后无损拼接。预览与 `lookdev` 直接 seek 到目标帧，
`lookdev --det` 对 pure 场景按倒序做第二遍采集。

pure 场景必须通过两道闸门：

- **静态**：扫描作品根与场景依赖源码，拒绝计时器、随机源、CSS 动效、`useFrame`、
  ECharts 动画、`new Date`、`element.animate` 与自走媒体播放；
- **动态**：每段选 2–4 个探针帧，正序与倒序截图 PSNR ≥ 60 dB；相邻块边界见证帧跨进程比对。

任一失败会明确指出场景与帧号，不写缓存、不回退 sequential。`elapsedSeconds` 的既有语义
不变；全局时间写法见[全局时间与连续行为](#全局时间与连续行为)。

并行 worker 先把分块和收据写入本次临时目录，全部解码、自检与跨进程边界验证通过后才发布可复用缓存；缺少见证帧也明确失败。边界差异的两张实际帧保存在作品 `outputs/code-cache/diagnostics/` 供排查，不作为通过凭据。修复前的 pure-time 缓存收据会失效并重新采集，避免重试复用尚未完成整组验证的分块。

### 分进程最终渲染

`m2v render --jobs N` 在渲染层按帧区间启动 N 个独立进程，每段解码核对帧数、尺寸与帧率，
拼接后复核总帧数，最后统一混音。默认 2；内存紧张时显式改为 1，走原有单会话；五类均可使用大于 1。
`--jobs` 不进入候选绑定，改变 jobs 仍可复用同一内容候选。

作品绘制实际横竖画幅的完整不透明画布，重要内容避让 `subtitleSafeArea`；共享层只叠加字幕。
采集使用完整 Chromium 的无头模式（Playwright 的 `chromium` channel），以加载 Windows WebGPU 所需的 DXC；安装使用 `uv run playwright install chromium`，仅安装 headless shell 不足以运行 WebGPU 场景。系统只开放已登记媒体和仓库字体，阻断外网及 WebSocket，作品直接依赖在自身 `package.json` 与锁文件中固定精确版本，并在作品材料记录来源、许可和适配依据；构建器校验作品内实际安装版本
（采用电影级后期时，作品自行声明 `postprocessing` 与 `@react-three/postprocessing`；依赖缺失时在打包前明确失败，不会静默渲染成没有后期的画面）。
字体、组件与显式资源未就绪、运行异常或逐帧绘制超时均使 prepare 失败，不发布有效缓存。

作品采用 `three-gpu-pathtracer` 等路径追踪实现时，除固定样本、Sobol 与 megakernel 外，还要控制场景对象身份：该实现按 UUID 排序灯光、网格和纹理/Source，Three 的默认随机 UUID 会让同一随机数映射到不同灯光。可在作品内固定可写对象、几何和纹理身份，保留材质等只读接口，不覆盖全局随机数。既有确定性核验应观察独立加载及复位重建，而不能仅凭同页冻结 Canvas 的重复截图推断跨加载稳定。

WebGPU 使用 `RectAreaLight` 时，按 [Three 官方说明](https://threejs.org/docs/pages/RectAreaLight.html) 初始化 `RectAreaLightTexturesLib` 并调用 `RectAreaLightNode.setLTC()`；路径追踪仍可能经过栅格预览或辅助缓冲，不能忽略这些路径的控制台错误。变形几何在送入 BVH 前检查有限坐标，浮点挤出端点先夹紧再做分数次幂；GPU 积分与最终输出完成后再 `ready()`。以上为现有确定性与资源就绪语义的适配注意事项，具体美术和平台范围仍逐场验证。

### 结构化来源

分镜 `sources` 与幕内 `content.sourceIds` 在准备阶段校验。画面从 `../src/code-scene/sources` 引入 `FinancialSeriesScene`、`ConstructionScene`、`VehicleScene`，或用同一模块的 `useSceneSource(id)` 读取本幕已准备的数据。来源文件和计算实现进入准备指纹。未声明的 ID 与旧 `m2v/style` 导入明确拒绝。

## 运动实现约定

运动风格见创作前必读的[视觉与表达参考](visual-expression-inspiration.md#三动态风格12-种)，采用自选。技术实现与风格选择分开，不要求统一的运动人格、层次、时长或动作配方。

时间按作品实际帧率换算：`帧位置 = 秒数 × fps = 毫秒数 × fps / 1000`。非整数位置按调用字段、事件或采集接口的既有精度处理，不增加统一取整规则，不以 UI 毫秒表规定视频时长。

曲线从共享 `motion.ts` 复用；共享原语必须显式传入缓动并返回有限值，`linear`、加速、减速及回弹等均可按表达目标选择，不要求入场／离场方向或例外说明。相同进度与参数的输出保持一致；含随机性的原语使用显式种子或已有固定默认种子，不累积前帧状态。

当前采集模式继续决定可用实现：[顺序采集](#代码场景的顺序逐帧采集)使用受控时钟；[纯时间采集](#纯时间采集opt-in)要求可任意 seek 的纯函数；[并行渲染](#分进程最终渲染)沿用对应确定性与验证要求。动态风格名称不改变这些边界。

需要准确比较的数据动画在稳定窗口保持真实数值、比例和口径，数字与图形由同一数据或进度计算；过渡可弹性表现，不能用回弹改变稳定结果。声明接触关系的对象从实际绘制几何推导位置，分离时独立求轨迹，再次接触时恢复依赖。相关事件与声音可共用[幕内事件](storyboard-schema.md#幕内事件)，实际联动按完整窗口复核。不要求所有风格模拟真实物理，也不要求每场增加接触、配角或点缀。

### 共享动效原语

`web/src/code-scene/primitives.ts` 提供五类只做数值映射的共享原语，作品从采用后的本地 `../src/code-scene/primitives`
导入：

| 原语 | 输入 | 输出 |
| --- | --- | --- |
| `rollNumber` | 起止值、进度、小数位、调用方缓动、可选千位分隔 | 数值与可直接绘制的文本 |
| `growSeries` | 数据序列、进度、基础值、调用方缓动、可选 `stagger` | 生长后的数值与每点生长比例 |
| `scrollList` | 行数、行高、视口、进度、调用方缓动、可选 `overscan` | 偏移量与可视行索引、纵坐标 |
| `interpolateState` | 若干同字段数值状态、进度、调用方缓动 | 插值后的状态对象 |
| `particleField` | 数量、进度、显式种子、原点、扩散、寿命、尺寸、调用方缓动 | 每个粒子的位置、尺寸与透明度 |

- `progress`（0–1）是唯一时间输入；原语不读挂钟、帧号、上一帧状态、视频或外部资源，
  相同进度与参数每次求值相同。跳帧采样与逐帧推进得到同一结果。
- 原语不内置视觉主题：不返回颜色、字体或线宽，这些由调用方在绘制时决定。缓动
  **必须显式传入**，没有缺省恒等；曲线从 `motion.ts` 复用，按表达目标选择，不限制
  `linear` 或其他曲线的通用使用场景。粒子随机性只来自显式 `seed`，缺省使用固定种子。
- `web/src/code-scene/motion.ts` 提供相机与原语共用的命名曲线：线性、缓入、缓出、
  缓入缓出、指数、五阶和回弹落定。曲线只依赖输入 0–1，不读时间或随机源；不得在作品内
  复制近似曲线。时间换算、数据与联动边界见[运动实现约定](#运动实现约定)。
- 原语不能用于关闭信息推进、母题可信度或版式重复问题，也不提供绕过复核的默认表现。
- 采用后的本地原语进入作品来源绑定；修改作品内被引用的实现后重新准备并复查，主项目参考源码的后续变化不会自动改变独立作品。
- 单元测试在 `web/src/code-scene/primitives.test.ts`，覆盖重复求值、跳帧一致性、种子、
  0 与 1 边界；`tests/common/test_motion_primitives.py` 另检查实现指纹与确定性源码闸门。

`dynamics.ts` 与 `subtitles.ts` 提供同一约束下的动效与字幕原语：`samplePath`、`sampleTrail`、
`burstField`、`expandingRings`、`dissolvePair`、`staggerReveal`，以及字幕激活、两行切分、
窗口包络与关键词切分。`screenSubtitleCharacters` 按传入帧号、开始帧、逐字间隔与单字时长
返回独立字符进度，标点可增加停顿，不把长句压入固定包络。安全区容器保持固定，文字入退场在内部进行。
这些原语只依赖显式进度或传入帧号、窗口、种子与缓动，不读取挂钟或上一帧状态；路径采样与
锥形笔触分别复用 MIT 许可的 `svg-path-properties`、`perfect-freehand`，由采用后的本地模块导出；这些已有能力按需复用，需要其他能力时可按[原生样品规范](design-samples.md)扩展登记依赖。新增动效或可视化组件前先按 `AGENTS.md` 的「动效与组件先
调研外部方案」检索并记录选型，既有原语能满足时优先复用。

### 共享动效组件

图表几何已统一到 D3；自动图示、公式和图标通过按需采用的本地模块使用，不混入 Remotion 合成时钟。接口、就绪规则、许可与可执行示例见[外部表达组件与转场](visual-components.md)。

`web/src/code-scene/motion-components/` 提供可按需采用的组件；它们只把 `progress` 和显式
`easing` 映射成样式、几何或排版，不读挂钟、不启动动画、不依赖 Remotion context。

| 层 | 组件 | 用途 |
| --- | --- | --- |
| L1 | `FadeIn` / `SlideIn` / `ZoomIn` | 透明度、位移、缩放入场 |
| L1 | `Blur` / `Glow` | CSS 模糊与辉光 |
| L1 | `DrawLine` | SVG 路径按进度生长（含双层错位） |
| L2 | `RollingNumber` | 数字滚动，复用 `rollNumber` |
| L2 | `Typewriter` | 逐字显影，光标不能闪烁 |
| L2 | `MarkerHighlight` | 手绘高亮，粗糙几何由 roughjs 生成 |
| L2 | `BarGrowth` | 柱状生长，复用 `growSeries` |
| L2 | `Callout` | 引线标注，引线按进度生长 |
| 排版 | `AutoFitText` / `TextBlock` | 单行字号适配；CJK 感知换行与逐字显影 |
| 图形 | `PathMorph` / `MaskReveal` | 路径形变；wipe/iris 遮罩揭示 |
| 图形 | `ArcGauge` / `ProgressRing` | 圆弧仪表与环形进度 |
| 图形 | `NoiseDrift` / `noiseAt` / `noiseDrift` | 种子噪声的有机漂移与抖动 |
| 图表 | `LinePlot` / `AreaPlot` / `Sparkline` / `Axis` | 纯时间安全的折线、面积、迷你趋势与坐标轴 |
| 图表 | `Timeline` / `ChapterTrack` | 事件时间轴与等距章节轨 |
| 图形 | `Pictogram` / `IconGrid` | 一格代表一个单位的象形图与图标阵列 |
| 图形 | `Waveform` / `resamplePeaks` | 采样峰值波形，固定柱数 |

```tsx
const t = Math.min(1, elapsedSeconds / 3);
const content = <>
  <AutoFitText text={title} withinWidth={820} fontFamily="M2V Sans" maxFontSize={112}/>
  <TextBlock text={body} maxWidth={640} fontFamily="M2V Sans" fontSize={32} progress={t}/>
  <LinePlot series={[{values: revenue}]} progress={t} width={1200} height={600}>
    <Axis orientation="x" domain={[0, revenue.length - 1]} range={[64, 1136]} at={540} ticks={5}/>
  </LinePlot>
</>;
```

使用边界：

- **文本测量**：`AutoFitText` / `TextBlock` 只在浏览器测量，并在字体就绪后重测；
  Node 下回退到调用方给定的字号或原始分行，不猜近似值。`@remotion/layout-utils`
  的 `fillTextBox` / `fitTextOnNLines` 按空格切词，中文不会换行——多行中文必须走
  `TextBlock` 的 CJK 断行，不要直接调用这两个函数。
- **路径**：`@remotion/paths` 只用于 SVG path；`PathMorph` 调用 `interpolatePath`，
  只做逐点插值、不做拓扑匹配，复杂轮廓要自行保证对应点或先重采样。Canvas 点列、
  粒子、辉光与量测继续用 Painter。
- **样式**：`@remotion/animation-utils` 只用于 CSS 数值、颜色与 transform；SVG 数值
  属性、Three.js 数值继续用 `interpolate`/`growSeries`/`interpolateState`。
- **图表**：参考 `LinePlot` / `AreaPlot` / `Sparkline` / `Axis` 只做数值映射和静态 SVG，坐标轴由调用方组合。使用其他库时按实际逐帧证据选择采集模式，不凭库名宣称 pure-time；几何与依赖进入作品。
- **噪声**：`@remotion/noise` 的 `noise2D` 以显式种子和坐标求值，相同输入结果相同；
  页面卸载/重挂载不受影响。噪声只用于有机漂移与纹理，不替代编排。
- **gauge/时间轴/象形图/波形**：只输出静态 SVG，不自动动画；标签密集时由调用方
  自行错开或截断，组件不做自动避让。
- **roughjs** 只生成 MarkerHighlight 的草图几何，必须传显式 `seed`；不要用它草图化
  作品已有的艺术路径。
- 作品从实际采用的本地模块导入；直接采用第三方包时在作品声明精确版本、来源和许可，按[实现手段开放](design-samples.md#实现手段开放)验证，不沿用共享别名或旧包白名单。
- 新包按实际许可、资源和时钟边界评估；依赖 Remotion composition 上下文的实现不能直接当普通代码场景组件。代码场景运动模糊可用既有子帧方案，不因候选名单预先限制表达。
- 共享组件属于实现指纹；修改后引用作品的片段缓存与准备指纹失效，必须重新准备并复查。

### 二维绘制层

`web/src/code-scene/painter/` 提供可选的二维 Canvas 绘制层（与 R3F 的 `Canvas`
区分）。不导入时画面与没有这一层时相同。它补的是中间一档：

| 载体 | 什么时候用 |
|---|---|
| DOM / SVG | 需要可选中文本、就地排版、作品组件 |
| `painter` | 辉光质感、高密度粒子、线条生长、逐字显影 |
| `three` + `PostFX` | 真实三维、景深与画面后期 |

```tsx
import * as painter from '../src/code-scene/painter';
const {PainterCanvas} = painter;

<PainterCanvas width={width} height={height} bloom={0.85} grain={0.035} seed={11}
  paint={(frame, {elapsedSeconds}) => { frame.spark(960, 420, 6, '#F8D893', .9); }}
  overlay={frame => { frame.text('主体大字', 960, 838, {size: 76}); }}
/>
```

| 项 | 约定 |
|---|---|
| 层 | `background`（底）→ `under`（不参加辉光）→ `paint`（内容，参加辉光）→ `post`（全幅后期）→ `overlay`（锐利层）→ 颗粒 |
| 文字 | **必须画在 `overlay`**。画进 `paint` 会被自己的光晕冲出重影；`post` 的全幅效果也不作用于文字 |
| 像素密度 | 按录制配置的 `captureScale` 自动分配后备缓冲；2 倍原生采集时后备缓冲同步放大，不触发像素不足 |
| 时间 | 只读 `elapsedSeconds` 或帧号；不得使用挂钟、随机源、计时器或 CSS 动画 |
| 文案 | 必须由作品参数传入，不得内嵌在绘制层；否则字体缺字检查看不到它 |
| 指纹 | 实际采用的本地实现纳入来源绑定，修改后重新准备与复核 |

#### 四层怎么分工

层的边界不是「画得先后」，而是**这东西该不该发光**。实心、有体积、需要看清轮廓的
物体进 `under`——辉光会把它们糊成一片；只有「本身就在发光」的东西才留在 `paint`。

把大面积浅色实心块画进 `paint`，辉光可能使其接近纯白。此时优先改到 `under`，
或根据实际画面降低 `bloom`；文字与标注继续放在 `overlay`。

#### 相机求值

`painter.cameraAt(keys, progress, easing?)` 把关键帧表与进度求成 `{scale, focusX, focusY}`。
它是**纯函数**：不读挂钟、随机源或上一帧状态，不施加任何变换，只返回数值，由调用方决定
如何施加。连续推拉应据此在**固定世界坐标**下绘制，而不是每幕各算一套屏幕几何。

```tsx
import * as painter from '../src/code-scene/painter';

const CAM = [
  {at: 0,  scale: 0.4, focusX: 0,   focusY: 0},   // 全景
  {at: 90, scale: 2.3, focusX: -60, focusY: 0},   // 推近目标
  {at: 180, scale: 0.5, focusX: 0,  focusY: 0},   // 拉远看整体
];
const {scale, focusX, focusY} = painter.cameraAt(CAM, frame, t => t * t * (3 - 2 * t));
// 世界坐标 → 屏幕：中心对准焦点
frame.group({at: [width / 2 - focusX * scale, height / 2 - focusY * scale], scale}, () => {
  draw_world(frame);
});
// 或逐点换算：painter.project({scale, focusX, focusY}, [x, y], width / 2, height / 2)
```

| 项 | 约定 |
|---|---|
| 缩放插值 | **对数空间**：1 与 4 的中点返回 2，等距进度对应等倍率变化，视觉上等速 |
| 焦点插值 | 按 `1/scale` 反比加权：推近时焦点更快贴到目标对象，不平均滑过 |
| 端点 | 进度早于首帧或晚于末帧时返回端点值，**不外推** |
| 关键帧 | 按 `at` 升序，`scale` 必须为正有限数；违反时明确报错，不静默夹取 |
| 缓动 | 由调用方传入（`easing`），缺省恒等；相机不自带风格化曲线 |
| 跨幕 | 相机不跨场景自动延续；需要连续推拉时把整段时间轴放进单幕，或由作品显式传入一致状态 |

#### 离屏分组合成与数值轨道

`Painter.layer(options, draw)` 把回调中的对象画入透明离屏缓冲，再把整层作为一个对象参与 alpha、位置、旋转、缩放、模糊、裁剪或加法混合。缓冲按尺寸复用；嵌套层使用不同的在用缓冲，绘制报错时仍清空并释放缓冲。它适合多个重叠形状要一起淡入、一起运动的情况；普通 `group()` 仍用于逐对象混合、局部坐标和量测可精确跟随的分组。

```tsx
frame.layer({alpha: progress, at: [x, y], rotate: angle, scale: 1.2}, layer => {
  drawBody(layer);
  drawHighlights(layer);
});
```

离屏层保持实际变换、裁剪与合成；边界、遮挡与可读性通过当前媒体复核。逻辑尺寸和采集密度自动匹配，包括 2 倍采集。

`painter.keyframeAt([{at, value}, ...], time, mode?)` 为任意有限数值提供纯求值；`mode` 支持 `linear`、`hold` 和非均匀时间 Catmull-Rom `smooth`。关键帧至少一项且时间严格递增，非法值明确失败；首尾之外保持端点。平滑曲线不夹断过冲，有限量值由调用方显式约束。相机仍使用专用 `cameraAt`，不要把相机尺度换成线性数值曲线。

开发用能力货架在仓库根目录的 `web/gallery.html`：运行 `pnpm -C web dev` 后打开 `http://localhost:5178/gallery.html`。它展示真实 painter API、相机、轨道与固定种子模拟，提供播放/暂停、进度拖动、复位和最小调用代码；Vite 正式构建只含 `contract.html`，货架不会进入生产包。

### 讲解机制与已有能力的映射

可选表达方向见[可选讲解机制](scene-design.md#可选讲解机制)，实际取证按[评审契约](review-contract.md)。以下是已有能力的
使用方法，不是新 API，也不提供自动对象识别、任意形状变形或自动因果判断。

| 需求 | 可复用能力与作品职责 |
|---|---|
| 对象连续追踪 | 作品维护稳定对象数据与绘制函数；数值形态参数可用 `interpolateState`，身份线索由作品保留并实看片验证 |
| 相机与尺度 | 二维用 `painter.cameraAt` 在固定世界坐标下求缩放与焦点，由作品施加变换；三维使用现有 `CameraRig` 与路径风险检查；二维变换不是三维投影 |
| 过程与结果 | 在同一进度下求模型状态，图形与数字共同读取该状态；`rollNumber`、`growSeries`、`interpolateState` 只负责映射，不替代领域模型 |
| 回场 | 作品复用同一绘制函数与构图参数，以不同阶段状态呈现；不新增独立回场组件 |

状态从录制时刻或进度直接求值，不累积上一帧。跨场景不会自动延续对象或相机；连续空间优先放在
单幕内部，必须跨幕时由作品显式传入一致状态并验证边界。世界坐标、DOM role、相同参数只能辅助
核查，不能代替完整窗口中的视觉识别。数百粒子等高密度绘制仍按实际录制性能选择绘制载体。

### 电影级后期与镜头

`PostFX` 只作用于 canvas，不影响共享字幕 DOM 层。全部后期参数由 `elapsedSeconds`/帧号驱动：
颗粒使用「镜头 id 哈希 + 帧号」的自带确定性效果，`EffectComposer` 关闭 MSAA
（`multisampling={0}`），不使用库里依赖 `Math.random` 生成噪点纹理的 `Noise`。
`CameraRig` 的位置、朝向、FOV、滚转与曝光同样只由帧号算出；`pathIntersectsSphere`、
`cameraPathRisk` 与 `backgroundRisk` 在作品侧提供穿球与背景裁切的纯函数检查。

电影级参考元件按需采用；每部作品的实际依赖、画面和缓存绑定以本地实现与当前证据核对，不把原参考实现的历史实验当成本工程已验证。

连续编号 PNG 直接按作品实际30或60 fps 编码为实际画幅的无声视频，输入与解码帧数必须精确一致；
不使用 fps 重采样或尾帧复制掩盖缺失状态。缓存绑定源码、参数、时间窗、实际帧率、画幅、字幕几何、
媒体摘要、依赖、浏览器和受控时钟实现；旧实时采集缓存失效。检查和正式生成按区间复用录制缓存。
顺序采集不等于任意作品可随机求帧或逐像素复现；浏览器量测仍只检查共享字幕，
不会自动识别作品正文和主体遮挡。

### 低角度平面细线与相机保持段

相关低角度细线、相机保持段及天体轨道排错见本页[按需排错](#按需排错)。

## lookdev 原生关键帧

静帧采集就绪或运行失败时，`lookdev` 错误会包含场景 ID、入口路径及原始原因，用于直接定位多场景作品中的失败入口。

`m2v lookdev` 重新构建当前代码场景，从第 0 帧连续推进到选定帧，仅保存关键帧，
不录制完整成片。逻辑画幅不变，采集配置的 `captureScale: 2` 可供已采用的 `PainterCanvas` 等支持像素密度的实现分配 2 倍后备缓冲；不能假定所有第三方组件自动适配。普通录制未声明时继续使用作品原有设置。
自定义 canvas 必须按该像素密度分配后备缓冲，像素不足会明确失败，不以放大代替。

`--sheet` 给单个整数时，均匀取帧数为 1～24；多个数值表示具体秒数。
`--sheet`、`--motion`、`--det`、`--event` 复用同一条采集路径：按幕分组，每幕从第 0 帧
推进到该幕内最晚的选定帧，其余选定帧只截不录。运行时只接受连续帧，因此没有随机访问，
越靠后的时刻代价越高。四种模式的指定帧在启动浏览器前先校验范围与所属幕；事件模式还
先校验事件存在、选择器无歧义与 before/at/after/hold 四阶段都在所属幕内。

秒数越界提示同时给出末帧号及可直接输入的定位秒数；提示秒数向下保留到毫秒，避免四舍五入后再次越界。实际输入范围与取帧规则不变。

关键帧以 PNG 进入共享 composition，按全片时间叠加字幕及转场，横屏输出
3840×2160（竖屏为 2160×3840）；有声作品的样片复用准备片段与母版音轨，无声作品输出无音轨样片。
`outputs/lookdev.json` 的 `stillCapture: native-code-png-v1` 表示原生采集路径，
记录准备指纹和实际输出尺寸。旧放大静帧不能作为原生 4K 细节的验收证据。

#### 绘制量测的可见性边界

- `text()` / `chars()` 的文字外框来自同次 `measureText()` 的实际字形度量；`baseline`、字体与字距先在绘制 context 生效。代理使用墨迹外框，不用代理 DOM 的排版溢出推断 Canvas 单行是否溢出。
- 代理位置按当前 Canvas 矩阵换算回逻辑坐标，包含嵌套平移、旋转、缩放；字号按纵向缩放换算。采集倍数不改变逻辑量测。
- 分组透明度、文字透明度与颜色自身 alpha 共同决定可见性；完全透明、完全离屏、完全裁剪的记录保持不可见，不计入可见对象探针。逐字显影只报告实际出现的字，保留已绘制文字间的空格，不提前报告整句。
- 分组矩形裁剪按变换后的凸多边形相交；部分裁剪保留裁切标记供排错，不能通过缩小代理外框隐藏实际裁切。
- 此量测描述绘制时的几何与显影，不证明后画对象、其他图层、辉光、模糊或全幅后期造成的最终像素遮挡与可读性；这些仍需检查实际帧与适用独立评审。直接操作 `painter.ctx.clip()` 的自定义裁剪不会进入分组裁剪记录，需使用 `group({clip: ...})` 或补人工证据。


## 按需排错


仅在相应创作、填写或排错任务触发时读取；本页不新增门禁或审核轮次。

### 低角度平面细线与相机保持段

平面内的发光细线（前沿、画缘、轨道环）在低机位会因透视缩短而接近零像素宽。需要用随相机距离缩放的垂直薄幕或侧壁补足厚度，或按屏幕像素下限反推相机仰角；只加宽平面线会在俯视时过粗、侧视时消失。相机关键帧用分段三次插值时，首尾相同的保持段要把切线显式置零，否则相邻关键帧的切线会在保持段内产生漂移；验收时抽同段连续帧核对。

### 天体轨道、开场取景与关键道具

- 天体系统的轨道线必须与天体在同一平面采样。把圆/椭圆点写成 `(cos·r, sin·r, 0)` 再靠 tilt/node 旋转，容易得到看似合理、实际竖直于黄道面的轨道；验收时直接投影行星位置，确认每颗行星落在自己的轨道折线上，并检查椭圆中心不与太阳共点。
- “开场看到全貌”不是把系统放进画面即可。按 699×393 量外圈轨道与全部行星的屏幕占比；主体只占画面宽度一半以下时，观众会读成远景黑场。相机若靠拉近解决，注意近侧轨道透视放大会把压平后的盘缘推出画框，需同时量开场和 9/11 秒。
- 关键运动道具（薄片、卡片、飞行物）按连续帧与目标手机尺寸验收。世界尺寸、材质名或单帧静态图不能证明观众看得到；至少检查入画、接近主体、消失三个时刻，并避免大范围光晕把道具读成彗星。
- 单向运镜检查：对相机逐帧采样距离、仰角、方位，确认没有无信息理由的反向段。球坐标标量路径比逐分量 Hermite 更容易保证单调；目标点下移只改变构图，不应把相机位置带过黄道面。
