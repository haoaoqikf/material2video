# 渲染契约

画面实现与渲染/体检脚本之间只有这一个接口。只要画面实现满足本契约，渲染脚本就能把它
导出为 MP4；反过来，任何一项不满足都会在开渲前报错，而不是产出一段有问题的视频。

## 契约的两个提供者

当前仓库里有两个提供者，按引擎选择：

- **契约页（当前默认）**：`web/dist/contract/contract.html`，由 `pnpm -C web build`
  从 `web/src/contract/` 构建。它把共享 React composition
  （`web/src/compositions/A2VComposition.tsx`）挂进 `@remotion/player`，
  暴露 `window.__A2V__`（**version 2**）。分镜地址由查询参数 `a2v-storyboard` 给出
  （本地静态服务提供），因此这一个页面能服务任意作品——作品不需要自己的 HTML。
  体检（K 系列、M 系列、组件契约探针）用 Playwright 驱动它；
  渲染（`render.py` 默认）不走它，而是直接从 composition 源码打包渲染
  （见「渲染引擎与打包」）。
- **作品自己的动画网页（旧引擎，迁移期保留）**：实现 `window.__A2V__`（version 1），
  由 `assets/timeline.js` 的 `A2V.mount()` 自动创建。渲染与体检入口按引擎核对版本号，
  版本不符直接拒绝——`ready()` 的语义在两个版本间不同，继续执行只会得到一叠空画面。

## 必需接口

画面实现必须在 `window` 上暴露 `__A2V__` 对象。契约页（version 2）的字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `version` | `number` | 契约版本，当前为 `2` |
| `fps` | `number` | 帧率，必须与分镜 JSON 的 `fps` 一致 |
| `width` | `number` | 画面宽度，必须与分镜 JSON 的 `width` 一致 |
| `height` | `number` | 画面高度，必须与分镜 JSON 的 `height` 一致 |
| `durationInFrames` | `number` | 总帧数，必须等于分镜中所有 `durationInFrames` 之和 |
| `ready()` | `() => Promise<void>` | 资源就绪后 resolve |
| `seekToFrame(frame)` | `(frame: number) => Promise<void>` | 把画面切换到第 frame 帧，绘制完成后 resolve |
| `currentFrame()` | `() => number` | 诊断用：当前实际落在哪一帧。不属于契约要求，渲染脚本不依赖它 |

`frame` 从 `0` 开始，最大值是 `durationInFrames - 1`。

## ready() 的语义

渲染脚本在加载页面后调用一次 `ready()`，并等待它 resolve 才开始截图。
version 2 的 `ready()` 必须保证：

- 字体已加载完成（否则首帧会用回退字体排版，且首帧与后续帧字宽不一致）；
- **Player 已经挂载**（version 1 只要求字体与首帧，这是 1 → 2 的唯一差别）；
- 画面已经绘制过至少一次。

契约页的实现（`web/src/contract/bridge.ts`）：等字体 Promise（与渲染入口的
`delayRender` 等的是同一个）、等 `document.fonts.ready`、把 Player 定位到当前帧
并等画面落定，再确认一次字体。

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
未改动的示例页同样复现，且与页码无关。所以验收按「编码后不可见」判定：
JPEG q98 中间帧的量化步长本身就大于 1 个色阶，成片不受影响。
需要拦下的是**整块元素的位置/透明度不同**，那类差异的 PSNR 会远低于 60 dB，
因此自动抽查用 `PSNR ≥ 60 dB` 作为阈值，而不是逐字节相等。

### 开渲前的静态扫描

旧引擎路径上，`render.py` 在进入渲染模式后会读取本地网页，以及它引用的本地样式表与脚本
（含 skill 的共享资产），命中以下写法时输出警告并指出行号：

- 样式：`@keyframes`、`animation:`、`transition:`；
- 脚本：`Date.now(`、`performance.now(`、`Math.random(`。

只提示不阻断——是否真的闪烁由上面的确定性验收决定，但这类写法几乎必然出问题。
脚本里不查 `requestAnimationFrame`，因为预览播放本身需要它；渲染时 `seekToFrame`
会暂停播放，画面只由帧号决定。

扫描范围以**仓库根**（含 `.git` 或 `pyproject.toml` 的最近上层目录）与 `/__a2v__/`
别名目录为界：网页目录内的资源始终扫描，网页引用的 `/__a2v__/<文件>` 按别名解析到
skill 的 `assets/` 再扫描，仓库内其他位置的资源也扫描；仓库外的相对路径不读，
避免顺着相对路径读到仓库外的任意文件。远程 URL（`http://` / `https://`）不参与扫描。

> 只扫网页目录是不够的：共享组件库在 skill 的 `assets/` 下，把动效写进组件库
> 曾经可以完全绕过这道检查；文章放到内容根之后，页面改用 `/__a2v__/` 引用共享资产，
> 漏掉别名这一路会重新打开同一个口子。

React 引擎路径上这道检查**明说跳过**（输出警告，不是安静照过）：画面由 composition
源码决定，契约页的 HTML 里只有一个挂载点与一个入口脚本，照旧按 HTML 查会连
「组件库」都找不到，报出来的全是假问题。它的结论由两处承担：组件源码里**不出现**
这些写法（web 侧测试与 lint 把守），以及同一套运行时量测与探针照常运行。

## 渲染引擎与打包

`render.py` 默认（`--engine remotion`）不经过浏览器截图，而是**直接从 composition
源码渲染**：

1. 打包：`remotion.bundle()` 把 `web/` 打成可渲染的 bundle（产物进临时目录）；
2. 元数据交叉校验：先向 composition 要一份真实元数据（fps / 尺寸 / 总帧数），
   用与网页路径**同一组判定函数**与分镜声明的值逐项比对，不一致时报错并列出两边取值；
3. 逐帧渲染：`remotion.render_frames()` 走 Remotion 的确定性渲染（按帧号 seek），
   输出 H.264；帧级 timeout 按分钟计，不沿用页面超时；
4. 收口与网页路径共用：合音轨、成片验收（`_verify_output`）、搬到最终位置、
   交付权限修复（见下文），一个字都不差。

体检路径（`review.py`）与此不同：它仍用 Playwright 驱动**契约页**——量测与探针
（约 90KB 已实测的判定逻辑）继续对着真实画面工作，而契约页挂的正是同一份
composition，体检看到的就是渲染会画出的画面。

## 可复用的动效原语

`web/src/runtime/motion.ts` 提供一组**纯函数**原语，全部只依赖入参，不保存跨帧状态。
配方与推荐帧数见 [竖屏视觉规范](visual-spec.md)。

| 原语 | 用途 |
| --- | --- |
| `progress(localFrame, start, duration, easing)` | 计算片段进度 0..1 |
| `since(localFrame, startFrame)` | 距起点已经过去的秒数——弹簧与所有物理量的输入 |
| `stagger(index, stepFrames, baseFrame)` | 逐项呈现时第 i 项的起始帧 |
| `enterStyle(runtime, seconds, { distance, axis, … })` | HTML 元素入场：透明度 + 位移 + 缩放（返回 React style） |
| `enterSvgAttrs(runtime, seconds, { distance, axis })` | SVG 分组入场（返回属性串） |
| `spring(seconds, SPRINGS[name])` | 物理弹簧：阻尼谐振子的闭式解（具名预设） |
| `range(p, from, to, { clamp })` | 把进度映射为任意数值（位移、光晕强度等） |
| `breath(localFrame, { periodFrames, amplitude })` | 常驻微动，避免后段完全静止 |
| `drawPathStyle(p, length)` | SVG 描边动画的样式；长度由调用方算一次后传入 |
| `revealCharOpacities(units, p, { frame, staggerFrames })` | 逐字揭示的不透明度，文本结构不变 |

**`spring` 收的是秒数，不是 0..1 的进度。** 弹簧本身就是曲线，
喂给它一条缓动过的进度会让它的自然周期失去意义（犯过：3 帧走完位移）。
`response` 是自然周期（秒，只决定快慢），`dampingFraction` 是阻尼比 ζ
（只决定过冲：峰值 ≈ `e^(-πζ/√(1-ζ²))`）。曲线来自 wobble 1.5.1
（MIT 的解析解），移植在 `web/src/runtime/spring.ts`。

`spring` 与 `breath` 都是闭式表达式（不迭代积分），因此同一帧永远得到同一结果——
这也是选闭式解而不是逐帧积分的原因：随机访问第 900 帧时，积分型必须重放全过程。
`drawPathStyle` 不每帧测量路径：连线长度在布局确定时用解析式算好并缓存
（React 组件不调用 `getTotalLength()`）。

## 视觉组件库

画面由共享 React composition（`web/src/compositions/A2VComposition.tsx`）按分镜逐幕
挂载组件：组件集合、标注键、容量、适用场景类型与默认映射都声明在组件注册表
`web/src/registry/registry.json`（唯一真源）；composition 按
`data.figure.kind`（没有则按场景类型取注册表的默认）解析出组件并挂载，
组件从 `useFigure()` 取帧号与场景。组件目录与选择方式见
[视觉组件目录](figure-catalog.md)。

```
分镜 ──▶ composition ──▶ registry 解析 kind ──▶ web/src/components/<Kind>.tsx
                │                                        │
                └──────────── useFigure()：帧号、场景、动效原语 ──┘
```

对契约的影响只有一条：**组件也是画面的一部分，因此组件的渲染必须满足与
`seekToFrame` 完全相同的确定性要求**。具体地说：

| 要求 | 原因 |
| --- | --- |
| 画面只由帧号、场景与时长推导 | 同帧重复渲染必须一致 |
| 禁止 `Date.now` / `performance.now` / `Math.random` / CSS 动画 | 同上；React 路径的静态检查跳过，靠组件测试与运行时量测把守 |
| 几何不读实时布局，测量只做一次并缓存 | 每帧测量会随排版抖动，也会拖慢渲染 |
| 组件不保存默认文案 | 文案只存在于分镜，避免两处漂移 |

## 中间帧格式

旧引擎路径（浏览器逐帧截图）默认用 JPEG（q98）截取中间帧，再交给 x264 编码。
原因是有实测依据的：1080 × 1920 下单帧截图 JPEG 约 66ms，PNG 约 225ms，差距约
3.4 倍；q98 对文字画面几乎无可感损失，且最终输出的 H.264 `yuv420p` 本身也是
4:2:0 有损格式。需要逐像素比对或存档无损中间帧时，改用 `--capture-format png`。

React 引擎路径不产生中间帧文件：Remotion 在引擎内逐帧渲染并直接编码，
成片的画质由 `--crf` 控制（默认 18）。溯源里该路径的 `captureFormat` 记为
`remotion`，以便与截图路径区分。

## 预览缩放与渲染模式

旧引擎路径上，`assets/base.css` 让舞台（`[data-a2v-stage]`）保持 1080 × 1920 的
逻辑尺寸，预览时由 `timeline.js` 用 `transform: scale()` 整体缩放，**不改变内部布局**，
因此预览与导出共用同一套坐标；渲染脚本在截图前给 `<html>` 加 `a2v-rendering` 类，
`base.css` 据此隐藏预览控件并取消缩放。

契约页不缩放：Player 以分镜声明的 `width × height` 原始尺寸挂载，
体检时视口也设为该尺寸，画面 1:1 落进视口。它没有播放控件
（`controls` 已关闭），调试手段见下文。

## 视口与画布尺寸

渲染/体检把浏览器视口设置为分镜声明的 `width × height`，并按该尺寸截图整个视口。
所以：

- 舞台（composition 根节点）必须严格等于 `width × height`，不要在外层加 margin 或 padding；
- 页面不能出现滚动条；
- 所有正文放在 `.a2v-safe` 安全区内，避免被平台 UI 遮挡。

渲染前渲染脚本会检查舞台实际尺寸与契约是否一致，不一致时输出警告日志。

## 码流兼容性

成片的码流参数由编码器固定，不由网页决定，原因是「ffmpeg 能解码」并不等于
「播放器能播放」：

| 项目 | 取值 | 为什么 |
| --- | --- | --- |
| 像素格式 | `yuv420p` + `-color_range tv` + `bt709` | JPEG 中间帧带的是全范围色彩，直接进 libx264 会产出 `yuvj420p(pc)`；ffmpeg 自己解码正常，但 Windows 的 Media Foundation 会以 `0xc00d36c4` 拒绝打开整个文件 |
| 尺寸 | 宽高都取偶数 | H.264 `yuv420p` 要求宽高可被 2 整除 |
| 配音 | AAC-LC / 44.1kHz / 立体声 / 128k | 24kHz 单声道 AAC 在 Media Foundation 上会被直接拒绝；44.1kHz 立体声是各平台默认支持的组合 |

`_verify_output()` 在解码验收之外会再读一次码流信息，命中全范围像素格式或非标准
4:2:0 时**报错终止**，避免把「能解码但播不了」的成片交付出去。这条检查有独立的
回归测试（`tests/test_output_compatibility.py`）。

## 交付文件的访问权限

成片、字幕与媒体清单都先写在临时目录里，再移动到最终位置。Windows 的
`tempfile.TemporaryDirectory()` 会创建一个**刻意收紧**的目录，ACL 只有
`SYSTEM / Administrators / OWNER RIGHTS` 且关闭继承；文件把这份 ACL 带到最终位置后，
管理员账号自己仍能读写，但**以标准权限运行的打包应用会读不到**——
Windows 11 新版「媒体播放器」打开成片时报 `0x80070005 你没有访问该文件的权限`，
而 ffmpeg 与浏览器上传都不受影响，所以问题只在用户双击播放时暴露。

因此 `a2v/security.py` 在文件落到最终位置后调用 `grant_inherited_access()`
（`icacls /reset`），让文件重新遵循父目录的继承规则；`render.py` 与 `prepare.py`
在每个交付文件上都会执行一次，失败只记警告日志、不影响已经渲染好的成片。

排查时注意两点，否则很容易误判为「文件没问题」：

- 缺陷在 `%TEMP%` 下**不会复现**——那里的临时目录额外继承了一条宽松的
  `CREATOR OWNER`，会把问题掩盖掉；用例必须把临时目录建在目标目录里；
- `needs_access_repair()` 只解析 icacls 的**授权行**。icacls 输出的第一行含文件路径，
  而用户名往往就在路径里（`C:\Users\<名>\...`），按整份输出做子串匹配会一律
  误判为「权限正常」。

## 失败表现

| 情况 | 结果 |
| --- | --- |
| 未定义 `window.__A2V__` | 等待超时后报错，并附带页面控制台的报错信息（契约页加载或解析分镜失败时也是这一表现：`__A2V__` 保持未定义，页面上有错误说明） |
| `__A2V__.version` 与引擎期望的不一致 | 报错终止（两个版本的 `ready()` 语义不同，混用只会得到一叠空画面） |
| `ready` 或 `seekToFrame` 不是函数 | 报错终止 |
| `fps` / `durationInFrames` / `width` / `height` 不是正整数 | 报错终止 |
| composition 元数据与分镜的 fps 或总帧数不一致 | 报错终止，并列出两边的值（两条渲染路径共用同一组判定函数） |
| `seekToFrame` 在超时内没有落到目标帧 | 报错终止，报出目标帧与实际所在帧 |
| 舞台尺寸与契约不一致 | 警告，继续渲染 |
| 文档尺寸超出视口 | 警告，提示可能存在溢出裁切 |
| 旧引擎路径：样式里出现 `animation` / `transition` / `@keyframes` | 警告并指出行号，继续渲染（是否闪烁由确定性验收决定） |

## 调试

契约页暴露了一个诊断字段（不属于契约要求）：

```js
window.__A2V__.currentFrame();   // Player 当前实际落在哪一帧
```

排查「画面没到目标帧」时先看它：`seekToFrame` 报超时时，错误信息里也带这个值。
分镜本身的问题（未知组件、未知布局）会在契约页上直接显示错误说明
（`data-a2v-contract-error` 元素），渲染入口报「`__A2V__` 未定义」时先打开页面看它。

旧引擎路径上，`A2V.controller` 提供播放与跳帧（`seek` / `play` / `currentFrame` /
`A2V.timeline.scenes`）供预览调试；渲染脚本只依赖上表的 `__A2V__` 契约，
不使用 `A2V.controller`。

## 可选配音与字幕

使用 `--media` 时，命令为页面 URL 添加 `a2v-media` 查询参数（旧引擎路径）。
共享运行时通过 `A2V.fetchStoryboard()` 读取清单、比对原分镜并在 mount 前应用派生时长，
返回值仍为分镜对象。页面 mount 后等待 `__A2V__.ready()`，包括字体、音频就绪与首帧。

React 引擎路径上，媒体清单在渲染前加载并校验：清单里的源分镜必须与命令行给的
分镜一致（不一致报「媒体与分镜不匹配，请重新 prepare」），随后以清单派生后的
分镜（时长按口播延长）驱动 composition；音频在帧渲染完成后由 FFmpeg 合入
（两条路径共用同一段收口代码），字幕按清单导出为同名 `.srt`。

旧引擎路径的契约细节：`mediaFingerprint`（源分镜 SHA-256，无媒体时为 null）必须匹配；
`durationInFrames` 声明派生后的总帧数；`seekToFrame` 始终暂停播放，字幕只由指定帧确定；
预览播放使用音轨 currentTime 驱动画面；导出模式不播放音频，合成由 FFmpeg 完成。

正文预留字幕区域，字幕在同一网页绘制，禁止另用 FFmpeg 字幕滤镜产生不同排版。
媒体服务器只绑定回环地址，支持 CORS 和字节 Range，允许素材在仓库外并支持音频跳转。
清单字段与校验见 [配音与字幕](media-contract.md)；
成片命名与默认输出位置见 [目录约定与输出路径](paths-and-outputs.md)。

## 成片溯源（`<名字>.provenance.json`）

渲染成功后会在成片旁边写一份溯源，例如 `voiced.mp4` →
`voiced.provenance.json`。它回答的是「这支片子是哪一版资产渲的」，
因为成片不入库、也没有别的东西会提醒你它已经落后于源码：
实测发生过两支作品的成片比动效重写早了几个小时，仍然带着被修掉的旧曲线，
看上去却仍然是「上次验收通过」的样子。

字段：

| 字段 | 说明 |
| --- | --- |
| `version` | 溯源格式版本。当前 `4`：画面来源区分为「网页」与「React composition」，后者指纹整个构建输入 |
| `renderer` | 画面来源：`page`（网页逐帧截图）或 `remotion`（composition 直接渲染） |
| `workspace` | 产物目录 → 工作区根的相对路径（如 `../..`），用于反解页面与资产在哪 |
| `renderedAt` | 渲染时刻（UTC） |
| `page` / `storyboard` | 网页（React 路径记 composition 入口）与分镜，相对工作区根；共享页面等落在 skill 别名目录里的记 `/__a2v__/` 别名键；两者之外只记文件名（不写绝对路径） |
| `frames` / `fps` / `width` / `height` / `captureFormat` | 成片参数；React 路径的 `captureFormat` 为 `remotion` |
| `assets.files` | 逐个的 sha256。网页路径是**网页真正引用**的本地资源，外加分镜文件与（有声导出时）媒体清单指纹；React 路径是**构建输入**——composition 可达的全部源码文件、`package.json` 与锁文件、字体，外加分镜与媒体清单指纹 |
| `assets.digest` | 上表的规范化 JSON 摘要，与媒体清单的 `sourceFingerprint` 同一套算法 |

两条口径值得记住：

- **只指纹真正影响画面的东西**：网页路径只指纹被引用的资源（改一个用不到的图形
  不会让成片报落后）；React 路径指纹从 composition 入口 import 可达的文件——
  改一个没被任何组件用到的文件不该让成片报落后，而改一个被引用的组件文件
  就该报。裸包名导入的第三方依赖（如 dagre）由 `package.json` 与锁文件覆盖：
  依赖版本变了，成片同样判落后。否则闸门会变成噪音，人开始忽略它——那等于没有闸门。
- **文本资产按 LF 归一化后哈希，二进制按原字节**：git 的换行归一化会在工作区
  静默翻转行尾，只差行尾的文件不该被判成落后（否则会出现人怎么重渲都消不掉的
  假落后）。
- **键记文件在哪，不记引用怎么写**：别名目录里的文件一律记 `/__a2v__/…` 键，
  内容根里的文章自己的资产记工作区相对键，两者都在别的树里时只记文件名。
  复核时按同一套规则反解，因此换机器、换目录、换内容根都读得回来，也不需要
  再传 `--content-root`。`version` 不是 3/4 的溯源按旧格式处理，报「无法判断，请重渲」，
  而不是报落后。

体检命令（`review.py`）会读这份溯源并在 `report.json` 的顶层 `provenance` 键
与终端摘要里给结论：`current`（对得上）/ `stale`（落后，并指名是哪几个文件变了）/
`unknown`（没有溯源、读不出来、旧格式或网页已不在——**如实说无法判断，不默认放行**）。
这份结论**只提示、不拦人**：不参与错误数，也不改退出码。

## 字体覆盖（缺字机检）

体检会逐个字符检查分镜里**会被渲染**的文本是否在字体里有字形，缺字按错误处理
（进错误数与退出码）。判据不是拿某支字体去量，而是**网页实际声明过的字体**：
从页面与它引用的样式表的 `@font-face` 里解析出字体文件，只有当这些字体加起来
都没有某个字形时，浏览器才真的会回退到系统字体——那正是要抓的东西。
网页没声明任何字体文件时（例如不启用预设、走系统字体的专属页面）
不报缺字——无从判断，也不凭空拦人——但会**写明「字体覆盖检查不适用」**：
一声不吭的检查和通过的检查在报告里长得一样，那是要避免的。

为什么它必须存在：缺字是唯一一种**静默失败**。浏览器不报错、不警告，直接用
系统字体顶上，字宽、字重、基线全变，而 K4 对齐与 K7 溢出量的都是元素框，
照过。它也是 webfont 子集化的前置条件——不做逐字检查就切字体，
等于把这种漂移变成常态。

范围与边界：

- 扫描分镜里会被渲染的字段（`text`/`title`/`subtitle`/`label`/`quote`/`caption`/
  `value`/`unit` 等）以及样式表里会被渲染的固定字串（`content:`）；
  `narration` 当前不渲染，**不进扫描**；
- 结论定位到 `sceneId.字段`——只说「缺字」不可修；
- 只判「字体里有没有这个字形」，不判字宽字重是否合适，也不判断浏览器
  实际选了哪个字体（那要跑浏览器）。
