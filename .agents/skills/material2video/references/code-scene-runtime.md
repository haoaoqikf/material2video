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
| `durationInFrames` | `number` | 总帧数，必须等于准备产物派生的全片时长（通用 v8 由逐段实际配音编译，上限600秒，即30 fps为18000帧、60 fps为36000帧） |
| `ready()` | `() => Promise<void>` | 资源就绪后 resolve |
| `seekToFrame(frame)` | `(frame: number) => Promise<void>` | 把画面切换到第 frame 帧，绘制完成后 resolve |
| `currentFrame()` | `() => number` | 只读诊断：Player 当前实际帧号，不参与求帧判定 |

`frame` 从 `0` 开始，最大值是 `durationInFrames - 1`。

## 幕内事件查询

general 场景从 `CodeSceneProps.eventFrames` 取得 prepare 解析的本幕事件帧表；无事件时省略。用 SDK `createSceneEvents` 查询，不在动画和声音中重复写同一时刻：

```tsx
const events = useMemo(() => createSceneEvents(config.eventFrames), [config.eventFrames]);
const frame = clock.elapsedSeconds * config.fps;
const approach = events.progress('contact', frame, 18, -18); // 接触前18帧开始，接触时完成
const count = frame >= events.frame('contact') ? 1 : 0;
const emphasis = frame >= events.frame('contact') ? 1 - events.progress('contact', frame, 6) : 0;
```

从 `react` 导入 `useMemo`，从 `m2v/code-scene` 导入 `createSceneEvents`。`frame(id)` 对未声明事件明确抛错；`progress(id,currentFrame,durationFrames,offsetFrames=0)` 将结果夹到0–1，当前帧、持续帧和偏移须有限，持续帧须大于0。允许分数帧，纯求值不依赖上次调用，适合子帧采集。零时长状态直接比较事件帧。

事件表是初始化快照，建议每份配置只创建一次。事件只规定时刻，不触发回调、不自动模拟碰撞、不重排字幕与旁白。录制页仍顺序逐帧推进；纯事件函数可乱序求值不表示录制页新增随机 seek 能力。声明与音效定位见[幕内事件](storyboard-schema.md#幕内事件)。

事件发生前后的画面取证用 `m2v lookdev --event <sceneId:eventId> --before <帧> --after <帧> [--hold <帧>]`：窗口由作者显式声明，工具从当前准备记录解析事件并取 before/at/after/hold 四类帧。它是看图预览，不自动绑定检查点，也不替代 G4 证据；事件越靠后，顺序采集仍从所属幕第 0 帧推进，pure 场景则直接 seek。

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
  return <Room state={state} shot={SHOT[config.chapter.id]} />;
}
```

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
因此 `PSNR ≥ 60 dB` 是判定同帧一致性的阈值。`m2v lookdev --det` 可用两次独立采集核对
同帧一致性；pure 场景还会在采集时自动做正序/倒序探针。确定性仍由源码闸门与源码指纹保证。

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
（`web/src/code-scene/`）采集。**未声明 pure-time 时**，内部接口 `start()` 后只接受连续的
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

- **静态**：扫描作品根与所选风格包源码，拒绝计时器、随机源、CSS 动效、`useFrame`、
  ECharts 动画、`new Date`、`element.animate` 与自走媒体播放；
- **动态**：每段选 2–4 个探针帧，正序与倒序截图 PSNR ≥ 60 dB；相邻块边界见证帧跨进程比对。

任一失败会明确指出场景与帧号，不写缓存、不回退 sequential。`elapsedSeconds` 的既有语义
不变；全局时间写法见[全局时间与连续行为](#全局时间与连续行为)。

### 分进程最终渲染

`m2v render --jobs N` 在渲染层按帧区间启动 N 个独立进程，每段解码核对帧数、尺寸与帧率，
拼接后复核总帧数，最后统一混音。默认 1，走原有单会话；目前仅 `general` 支持大于 1。
`--jobs` 不进入候选绑定，改变 jobs 仍可复用同一内容候选。

作品绘制实际横竖画幅的完整不透明画布，重要内容避让 `subtitleSafeArea`；共享层只叠加字幕。
系统只开放已登记媒体和仓库字体，阻断外网及 WebSocket，打包仍只批准文档列出的共享依赖
（含电影级后期所需的 `postprocessing` 与 `@react-three/postprocessing`；依赖缺失时在打包前
明确失败，不会静默渲染成没有后期的画面）。
字体、组件与显式资源未就绪、运行异常或逐帧绘制超时均使 prepare 失败，不发布有效缓存。

### 可选风格

场景可从 `m2v/style` 读取只读身份与参数，从 `m2v/style/components/<name>` 和 `m2v/style/assets/<name>` 导入所选包的登记入口；未选择风格时身份为 null、参数为空对象，资源导入失败。加载边界、就绪要求和缓存规则见[风格接入契约](style-pack.md)。风格不自动换肤。

### 共享动效原语

`web/src/code-scene/primitives.ts` 提供五类只做数值映射的共享原语，作品从 `m2v/code-scene`
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
  **必须显式传入**，没有缺省恒等；曲线从 `motion.ts` 的命名曲线中选择，`linear` 只用于
  匀速跟踪、进度或旋转等有说明的用途。粒子随机性只来自显式 `seed`，缺省使用固定种子。
- `web/src/code-scene/motion.ts` 提供相机与原语共用的命名曲线：线性、缓入、缓出、
  缓入缓出、指数、五阶和回弹落定。曲线只依赖输入 0–1，不读时间或随机源；不得在作品内
  复制近似曲线。设计与帧数换算见[运动设计](../../motion-design/SKILL.md)。
- 原语不能用于关闭信息推进、母题可信度或版式重复问题，也不提供绕过复核的默认表现。
- 原语属于共享渲染资产：`implementation_inputs()` 递归收集 `web/src/code-scene/` 下的
  `.tsx`、`.ts` 与 `.js`，修改原语会使引用作品的片段缓存与准备指纹失效，必须重新准备并复查。
- 单元测试在 `web/src/code-scene/primitives.test.ts`，覆盖重复求值、跳帧一致性、种子、
  0 与 1 边界；`tests/common/test_motion_primitives.py` 另检查实现指纹与确定性源码闸门。

### 二维绘制层

`m2v/code-scene` 以 `painter` 命名空间提供可选的二维 Canvas 绘制层（与 R3F 的 `Canvas`
区分）。不导入时画面与没有这一层时相同。它补的是中间一档：

| 载体 | 什么时候用 |
|---|---|
| DOM / SVG | 需要可选中文本、就地排版、风格包组件 |
| `painter` | 辉光质感、高密度粒子、线条生长、逐字显影 |
| `three` + `PostFX` | 真实三维、景深与画面后期 |

```tsx
import {painter} from 'm2v/code-scene';
const {PainterCanvas} = painter;

<PainterCanvas width={width} height={height} bloom={0.85} grain={0.035} seed={11}
  paint={(frame, {elapsedSeconds}) => { frame.spark(960, 420, 6, '#F8D893', .9); }}
  overlay={frame => { frame.text('主体大字', 960, 838, {size: 76, role: 'subject'}); }}
/>
```

| 项 | 约定 |
|---|---|
| 层 | `background`（底）→ `under`（不参加辉光）→ `paint`（内容，参加辉光）→ `post`（全幅后期）→ `overlay`（锐利层）→ 颗粒 |
| 文字 | **必须画在 `overlay`**。画进 `paint` 会被自己的光晕冲出重影；`post` 的全幅效果也不作用于文字 |
| 像素密度 | 按录制配置的 `captureScale` 自动分配后备缓冲；2 倍原生采集时后备缓冲同步放大，不触发像素不足 |
| 时间 | 只读 `elapsedSeconds` 或帧号；不得使用挂钟、随机源、计时器或 CSS 动画 |
| 文案 | 必须由作品参数传入，不得内嵌在绘制层；否则字体缺字检查看不到它 |
| 指纹 | 目录内任何改动都会使引用作品的准备与片段缓存失效 |

#### 四层怎么分工

层的边界不是「画得先后」，而是**这东西该不该发光**。实心、有体积、需要看清轮廓的
物体进 `under`——辉光会把它们糊成一片；只有「本身就在发光」的东西才留在 `paint`。
`styles/vibe-night/examples/fold/` 是这个分工的实例：

| 层 | 画什么 | 为什么 |
|---|---|---|
| `background` | 近黑底、中央深蓝光池、暗角 | 不参与辉光，铺满即可 |
| `under` | 血红细胞、细胞内的分子点 | 实体，边缘必须清晰；参考片同样把实物画在底层 |
| `paint` | 珠串、密团、氧分子、长杆 | 自发光主体，越亮光晕越大是想要的效果 |
| `overlay` | 字母行、对象标注、引线 | 文字要锐利，不能带重影 |

```tsx
<PainterCanvas
  background={P => { P.clear('#010104'); /* 光池与暗角 */ }}
  under={P => redCell(P, bend, 0, 0, alpha)}
  paint={P => beads.forEach(([x, y]) => bead(P, x, y, 14, ICE))}
  overlay={P => P.text('第 6 颗', x, y, {size: 30, role: 'annotation'})}
/>
```

反例：把大面积浅色实心块画进 `paint`，辉光会把它顶到接近纯白（`styles/vibe-fable/examples/`
的鸽子示例早期版本就踩过，米墙实测被推到 253）。此时要么改到 `under`，要么把
`bloom` 压到 0.1 量级。

#### 相机求值

`painter.cameraAt(keys, progress, easing?)` 把关键帧表与进度求成 `{scale, focusX, focusY}`。
它是**纯函数**：不读挂钟、随机源或上一帧状态，不施加任何变换，只返回数值，由调用方决定
如何施加。连续推拉应据此在**固定世界坐标**下绘制，而不是每幕各算一套屏幕几何。

```tsx
import {painter} from 'm2v/code-scene';

const CAM = [
  {at: 0,  scale: 0.4, focusX: 0,   focusY: 0},   // 全景
  {at: 90, scale: 2.3, focusX: -60, focusY: 0},   // 推近到第 6 颗
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

子绘制的量测项会加入同一帧清单，并套用离屏层的变换和裁剪；其边界仍是各标记矩形经变换后的外框，不含模糊与辉光的最终像素外沿。复杂变形后的实际边界、遮挡与可读性仍须复核最终画面。逻辑尺寸和采集密度自动匹配，包括 2 倍采集。

`painter.keyframeAt([{at, value}, ...], time, mode?)` 为任意有限数值提供纯求值；`mode` 支持 `linear`、`hold` 和非均匀时间 Catmull-Rom `smooth`。关键帧至少一项且时间严格递增，非法值明确失败；首尾之外保持端点。平滑曲线不夹断过冲，有限量值由调用方显式约束。相机仍使用专用 `cameraAt`，不要把相机尺度换成线性数值曲线。

开发用能力货架在仓库根目录的 `web/gallery.html`：运行 `pnpm -C web dev` 后打开 `http://localhost:5178/gallery.html`。它展示真实 painter API、相机、轨道与固定种子模拟，提供播放/暂停、进度拖动、复位和最小调用代码；Vite 正式构建只含 `contract.html`，货架不会进入生产包。

#### 量测代理与状态探针

绘制层每帧都会输出两类可量测信息，**两者都来自同一次绘制记录**：

- **代理 DOM**：`div[data-m2v-role][data-m2v-state]`，位置尺寸对应实际绘制包围盒、字号与绘制一致、
  `textContent` 反映实际显影文字，完全显示后须与活动文字计划相等。它是让 Canvas 内容脱离「观测范围：未验证」的**必需项**。
- **状态探针**：`window.__M2V_REVIEW_STATE__`，形如 `[{role, count, state}]`，供合同断言交叉校验。

三个已知陷阱：

1. **只写探针不够**。探针只产出独立的「可选状态探针」检查，不消除「观测范围：未验证」；
   该帧若有活动文字计划而页面没有 DOM 标记，文字状态会直接判失败，人工证据也翻不回来。
2. **代理文字必须用 `-webkit-text-fill-color: transparent` 隐藏**。这里的透明填充只隐藏代理本身；实际绘制不可见时，代理另以 `opacity: 0` 如实报告不可见。
   不用 `color: transparent` 隐藏代理，避免丢失用于颜色断言的实际颜色。
3. **`text()` / `chars()` 传 `role` 才进代理**。没传 `role` 的绘制不产生代理元素，也不计入文字预算。

写合同断言时，`expected` 的 `role` 用绘制层给的角色（如 `lead`、`axis-label`）；
需要固定状态时同时声明 `state`。

### 讲解机制与已有能力的映射

机制设计与取证要求见[四种讲解机制](explainer-design.md#四种讲解机制的执行方法)。以下是已有能力的
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

作品不引用这些元件时画面与既有一致：真实浏览器验证「把套件从 SDK 导出里摘掉后，
标准画面逐像素相同」，且 look、shots 与 `claims` 只在非默认时进入片段缓存键。

连续编号 PNG 直接按作品实际30或60 fps 编码为实际画幅的无声视频，输入与解码帧数必须精确一致；
不使用 fps 重采样或尾帧复制掩盖缺失状态。缓存绑定源码、参数、时间窗、实际帧率、画幅、字幕几何、
媒体摘要、依赖、浏览器和受控时钟实现；旧实时采集缓存失效。检查和正式生成按区间复用录制缓存。
顺序采集不等于任意作品可随机求帧或逐像素复现；浏览器量测仍只检查共享字幕，
不会自动识别作品正文和主体遮挡。

### 低角度平面细线与相机保持段

相关低角度细线、相机保持段及天体轨道排错见本页[按需排错](#按需排错)。

## lookdev 原生关键帧

`m2v lookdev` 重新构建当前代码场景，从第 0 帧连续推进到选定帧，仅保存关键帧，
不录制完整成片。逻辑画幅不变，采集配置的 `captureScale: 2` 使 SDK `Canvas`
及 `Chart` 原生绘制 2 倍像素；普通录制未声明时继续使用作品原有设置。
自定义 canvas 必须按该像素密度分配后备缓冲，像素不足会明确失败，不以放大代替。

`--sheet`、`--motion`、`--det`、`--event` 复用同一条采集路径：按幕分组，每幕从第 0 帧
推进到该幕内最晚的选定帧，其余选定帧只截不录。运行时只接受连续帧，因此没有随机访问，
越靠后的时刻代价越高。四种模式的指定帧在启动浏览器前先校验范围与所属幕；事件模式还
先校验事件存在、选择器无歧义与 before/at/after/hold 四阶段都在所属幕内。

关键帧以 PNG 进入共享 composition，按全片时间叠加字幕及转场，横屏输出
3840×2160（竖屏为 2160×3840）；有声作品的样片复用准备片段与母版音轨，无声作品输出无音轨样片。
`outputs/lookdev.json` 的 `stillCapture: native-code-png-v1` 表示原生采集路径，
记录准备指纹和实际输出尺寸。旧放大静帧不能作为原生 4K 细节的验收证据。

#### 绘制量测的可见性边界

- `text()` / `chars()` 的文字外框来自同次 `measureText()` 的实际字形度量；`baseline`、字体与字距先在绘制 context 生效。代理使用墨迹外框，不用代理 DOM 的排版溢出推断 Canvas 单行是否溢出。
- 代理位置按当前 Canvas 矩阵换算回逻辑坐标，包含嵌套平移、旋转、缩放；字号按纵向缩放换算。采集倍数不改变逻辑量测。
- 分组透明度、文字透明度与颜色自身 alpha 共同决定可见性；完全透明、完全离屏、完全裁剪的记录保持不可见，不计入可见对象探针。逐字显影只报告实际出现的字，保留已绘制文字间的空格，不提前报告整句。
- 分组矩形裁剪按变换后的凸多边形相交；部分裁剪保留裁切标记，使检查点报告失败，不能通过缩小代理外框隐藏裁切。
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
