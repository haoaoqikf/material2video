# 渲染契约

> **适用范围：** 本文描述当前 3 个视频类型共用的渲染契约：契约页（`version: 6`）、Remotion
> 逐帧渲染、成片编码、交付权限与溯源。画面只有一条实现路径——共享 React composition 由准备
> 产物直接驱动；浏览器布局量测当前只覆盖文章 v7 模板。分镜结构见 [文章分镜 v7](storyboard-schema.md)，
> 设计令牌见 [设计令牌](design-tokens.md)，
> 制作顺序见 [制作流程](production-workflow.md)。v3/v4 的共享动画、场景树、节拍运行时与
> `version: 3/4` 契约页已随旧子系统删除，本文不再描述。

画面实现与渲染/量测脚本之间只有这一个接口。只要画面实现满足本契约，渲染脚本就能把它
导出为 MP4；反过来，任何一项不满足都会在开渲前报错，而不是产出一段有问题的视频。

## 契约的唯一提供者

画面契约由**契约页**提供：`web/dist/contract/contract.html`，由 `pnpm -C web build`
从 `web/src/contract/` 构建。它把共享 React composition（`ArticleExplainer`）挂进
`@remotion/player`，暴露 `window.__M2V__`（**version 6**）。作品参数（准备产物）由查询参数
`m2v-storyboard` 给出（本地静态服务提供），因此这一个页面能服务任意作品——作品不需要自己的 HTML。
布局量测（`m2v general keyframes`，以及 preview / render 内部）用 Playwright 驱动它；
渲染不走它，而是直接从 composition 源码打包渲染（见「渲染引擎与打包」）。

## 必需接口

### 评审输出的全局帧范围与缩放

文章的完整预演与量测由 `m2v preview --project <目录>` 生成（`m2v general samples` 与
`m2v general rehearsal` 现在只是它的别名）；`--limit-frames` 只用于调试，限帧预览不绑定评审。
帧范围、媒体时轴与缩放由类型内部渲染器统一处理，正式导出仍须经
`m2v render --project <目录>` 渲染完整时间轴并保持原分辨率。

画面实现必须在 `window` 上暴露 `__M2V__` 对象。契约页（version 6）的字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `version` | `number` | 契约版本，当前为 `6` |
| `fps` | `number` | 帧率，必须与准备记录一致 |
| `width` | `number` | 画面宽度，必须与准备记录一致 |
| `height` | `number` | 画面高度，必须与准备记录一致 |
| `durationInFrames` | `number` | 总帧数，必须等于准备产物派生的全片时长（文章 v7 由逐段实际配音编译，上限 18000 帧） |
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
- 布局量测与成片验收照常运行（见下文），成片仍要过上面的确定性验收。

### 代码场景不在确定性闸门内

作品 `scenes/` 下的 TSX **不进入 composition**，因此不受上面的源码闸门约束：它在准备阶段由
独立录制页实时录制（`web/src/code-scene/`）。打包只批准 React、`motion`、`three`、
`@react-three/fiber`、`@react-three/drei`、`gsap`、`echarts` 与 `m2v/code-scene`，
相对导入必须留在作品目录内，远程模块与未批准依赖在构建时报错，工具不安装作品依赖；
录制页阻断外网请求与 WebSocket，就绪超时、请求失败或运行异常都让 `prepare` 失败。
录制正文固定 864×920、位于标题下方，标题与字幕仍由共享外壳绘制且字幕层在片段之上；
片段标准化为与镜头帧数完全一致的 30 fps 无声视频，声音由统一音轨处理。
成片只回放这段已验收片段，正式导出不再执行作品代码；因此代码场景不保证逐像素复现，
文字包围盒量测也只覆盖共享外壳的标题与字幕，不检查作品代码画了什么。

## 渲染引擎与打包

正式渲染不经过浏览器截图，而是**直接从 composition 源码渲染**：

1. 打包：`remotion.bundle()` 把 `web/` 打成可渲染的 bundle。默认走本地缓存
   （见「打包缓存」）；缓存命中时跳过打包，但分镜校验与
   源码确定性扫描照常执行；
2. 元数据交叉校验（同一会话）：向 composition 要一份真实元数据（fps / 尺寸 /
   总帧数），与准备记录逐项比对，不一致时报错并列出两边取值，同时终止会话
   ——**一帧都不会渲**；
3. 逐帧渲染（同一会话，校验通过后下发渲染参数）：Remotion 按帧号 seek，
   输出 H.264；渲染与编码在 Remotion 内部重叠，报告里记一段合并耗时；
   帧级 timeout 按分钟计，不沿用页面超时；
4. 收口（各类型渲染入口共用同一批函数）：合音轨、成片验收
   （`output_validation.verify_output`）、搬到最终位置、交付权限修复（见下文），
   一个字都不差。

### 打包缓存

- 位置：`web/.cache/m2v-bundles/<键>/`（已被 `.gitignore` 忽略，可随时整目录删除）。
- 键覆盖**全部会改变产物的输入**：共享源码可达集合、字体、`public/` 静态资产、`remotion.config.ts` /
  `tsconfig.json` / `package.json` / `pnpm-lock.yaml` 以及 Node 版本。
  因此改代码、换字体、换作品或升级依赖都会换键，不会交付上一份画面。
- 命中判定是**逐文件复核摘要与大小**，不是「目录存在」；清单缺少完成标记
  （上次构建被中断）即判未命中并重建。
- 构建先写临时目录，产物清单写全后整体改名发布；同一把键由锁串行，等待者拿到锁后
  复查一次，不重复打包；同一前端工作区的构建使用全局锁，避免并发构建冲突。
- `bundle(cache=False)` 本次强制重新打包（诊断与基准对照用）；
  缓存只省掉打包，**不跳过任何门禁**。

### 渲染会话与并发

- 一次渲染只起一个 Node 进程、只开一个浏览器：选择 composition、报出元数据、
  等待 Python 的确认行，之后用同一个浏览器渲染。两次进程调用各冷启动一次浏览器的
  开销因此消失。`--metadata-only` 诊断路径保留。
- 两侧只通过 stdout 上的前缀行通信（常量在 `src/m2v/engine/remotion.py`）：Node 报
  `__M2V_SESSION__`（会话信息）、`__M2V_COMPOSITION__`（composition 元数据）、
  `__M2V_READY__`（元数据已报出、等确认）、`__M2V_PROGRESS__<百分比>`（渲染进度）与
  `__M2V_DONE__`（渲染完成）；Python 回 `__M2V_CONFIRM__{...}`（校验通过，可以开渲）
  或 `__M2V_ABORT__{...}`（校验没过，立即退出）。**先握手再渲染**是刻意的：
  元数据不匹配时一帧都不会渲。
- 会话异常时 Node 走 `finally` 关掉浏览器后退出；父进程 EOF、静默超时、渲染失败
  同样收掉整棵进程树（Windows 用 `taskkill /T`），不留下孤儿 Chromium。
- 并发（`concurrency`）透传给 Remotion，**默认 1**。提高并发会抬高峰值内存，
  Windows 长片在多并发页签下可能被系统关闭并报 `Target closed`，因此不按 CPU 数
  自动提高；非法取值在打包前即报错，早于渲染。当前各类型都固定用 1。

### 性能报告（`<名字>.performance.json`）

每次 Remotion 渲染在成片同级写一份结构化报告（已被 `.gitignore` 忽略），字段包括：
各阶段秒数（`cache` / `bundle` / `metadata` / `render` / `mux` / `probe`）、跳过阶段列表、
缓存命中状态与键、实际并发、帧数与分辨率、`entry`（`render` 还是 `preview`）、
`generatedAt` / `executedSeconds` / `totalSeconds`，以及 `environment`（平台、CPU 与内存、
Python / Node / Remotion / ffmpeg 版本）——两次报告的数字只有在这个前提下才可比。
`render` 已含编码，因此没有独立的 `encode` 阶段——两段在 Remotion 里是同一段时间，
拆开相加会让总耗时重复累计。未执行的阶段写 `null` 并列入 `skipped`，不写 0 冒充实测。
报告是附加信息：写失败只告警，不会让一次已经验收通过的渲染失败。

### 布局量测（三项硬判定）

布局量测不走渲染路径：`m2v general keyframes`（以及 preview / render 内部）用 Playwright
驱动**契约页**，量测对着真实画面工作，而契约页挂的正是渲染会画出的同一份 composition。
量测只剩三项硬判定，全部按真实文字包围盒判定：

| 判定 | 判据 |
| --- | --- |
| 画布分区溢出 | 文字包围盒越出正文分区（左 106 / 右 974 / 上 158 / 下 1502；字幕区内文字到 1782） |
| 字幕遮挡 | 字幕文字中心点处的最上层元素不属于字幕层——文字在、但被背景盖住同样失败 |
| 容器内溢出 | 文字越出它所属的 `data-m2v-box` 容器 2px 以上 |

量测读取画面自己打的标记：`data-m2v-copy`（文字）、`data-m2v-box`（容器）、
`data-m2v-subtitle`（字幕层）、`data-m2v-content`（正文内容区）。结果写
`outputs/layout-check.json`，失败会阻断预演与正式导出。旧的 K 系列观感闸门已随旧子系统
删除，不再有那套「约 90KB 判定逻辑」的量测。

## 成片编码

渲染路径不产生中间帧文件：Remotion 在引擎内逐帧渲染并直接交给 x264 编码，
成片的画质由 CRF 控制（默认 18，`preset` 默认 `medium`）。溯源里记
`renderer: "remotion"` 与 `compositionId`，与历史上「网页逐帧截图」路径的产物区分。

## 预览缩放与渲染模式

契约页不缩放：Player 以准备记录里的 `width × height` 原始尺寸挂载，
量测时视口也设为该尺寸，画面 1:1 落进视口。它没有播放控件
（`controls` 已关闭），调试手段见下文。

## 视口与画布尺寸

渲染/量测把浏览器视口设置为准备记录里的 `width × height`，并按该尺寸截图整个视口。
所以：

- 舞台（composition 根节点）必须严格等于 `width × height`，不要在外层加 margin 或 padding；
- 页面不能出现滚动条；
- 正文放在安全区内（`--m2v-safe-top` / `--m2v-safe-bottom` / `--m2v-safe-x`，有字幕时用
  `--m2v-safe-bottom-with-subtitles`），避免被平台 UI 遮挡；取值与栅格见
  [设计令牌](design-tokens.md)。

渲染前渲染脚本会检查舞台实际尺寸与契约是否一致，不一致时输出警告日志。

## 码流兼容性

成片的码流参数由编码器固定，不由画面决定，原因是「ffmpeg 能解码」并不等于
「播放器能播放」：

| 项目 | 取值 | 为什么 |
| --- | --- | --- |
| 像素格式 | `yuv420p` + `-color_range tv` + `bt709` | 全范围色彩（`yuvj420p(pc)`）ffmpeg 自己解码正常，但 Windows 的 Media Foundation 会以 `0xc00d36c4` 拒绝打开整个文件 |
| 尺寸 | 宽高都取偶数 | H.264 `yuv420p` 要求宽高可被 2 整除 |
| 配音 | AAC-LC / 44.1kHz / 立体声 / 128k | 24kHz 单声道 AAC 在 Media Foundation 上会被直接拒绝；44.1kHz 立体声是各平台默认支持的组合 |

`output_validation.verify_output()` 在解码验收之外会再读一次码流信息，命中全范围像素格式或
非标准 4:2:0 时**报错终止**，避免把「能解码但播不了」的成片交付出去。

## 交付文件的访问权限

成片与准备音轨都先写在临时目录里，再移动到最终位置。Windows 的
`tempfile.TemporaryDirectory()` 会创建一个**刻意收紧**的目录，ACL 只有
`SYSTEM / Administrators / OWNER RIGHTS` 且关闭继承；文件把这份 ACL 带到最终位置后，
管理员账号自己仍能读写，但**以标准权限运行的打包应用会读不到**——
Windows 11 新版「媒体播放器」打开成片时报 `0x80070005 你没有访问该文件的权限`，
而 ffmpeg 与浏览器上传都不受影响，所以问题只在用户双击播放时暴露。

因此 `src/m2v/core/security.py` 在文件落到最终位置后调用 `grant_inherited_access()`
（`icacls /reset`），让文件重新遵循父目录的继承规则；`m2v render` 与 `m2v prepare`
在每个交付文件上都会执行一次，失败只记警告日志、不影响已经渲染好的成片。

排查时注意两点，否则很容易误判为「文件没问题」：

- 缺陷在 `%TEMP%` 下**不会复现**——那里的临时目录额外继承了一条宽松的
  `CREATOR OWNER`，会把问题掩盖掉；用例必须把临时目录建在目标目录里；
- `has_usable_access()` 只解析 icacls 的**授权行**。icacls 输出的第一行含文件路径，
  而用户名往往就在路径里（`C:\Users\<名>\...`），按整份输出做子串匹配会一律
  误判为「权限正常」。

## 失败表现

| 情况 | 结果 |
| --- | --- |
| 未定义 `window.__M2V__` | 等待超时后报错，并附带页面控制台的报错信息（契约页加载或解析材料失败时也是这一表现：`__M2V__` 保持未定义，页面上有错误说明） |
| `__M2V__.version` 与 composition 的契约版本不一致 | 报错终止，并说明当前支持的契约版本（版本不同的 `ready()` 语义不同，混用只会得到一叠空画面） |
| `ready` 或 `seekToFrame` 不是函数 | 报错终止 |
| `fps` / `durationInFrames` / `width` / `height` 不是正整数 | 报错终止 |
| composition 元数据与准备记录的 fps 或总帧数不一致 | 报错终止，并列出两边的值 |
| `seekToFrame` 在超时内没有落到目标帧 | 报错终止，报出目标帧与实际所在帧 |
| 舞台尺寸与契约不一致 | 警告，继续渲染 |
| 文档尺寸超出视口 | 警告，提示可能存在溢出裁切 |

## 调试

契约暴露只读的 `currentFrame()` 诊断读数，返回 Player 实际所在的帧号，不参与求帧完成判定。
`seekToFrame` 超时时也会报告目标帧与实际帧（`web/src/contract/bridge.ts` 的 `settleOnFrame`）。

材料本身的问题（未知字段、缺图片、缺少已准备的 v7 材料）会在契约页上直接显示错误说明
（`data-m2v-contract-error` 元素），渲染入口报「`__M2V__` 未定义」时先打开页面看它。

## 配音与字幕

配音与字幕由 `m2v prepare` 写进准备记录（`outputs/prepared.json` 的 `audio.segments` 与
`subtitles`）：音轨在帧渲染完成后由 FFmpeg 合入，字幕由画面自身绘制，**不用 FFmpeg
字幕滤镜**——那会产出与画面排版不同的一套字幕。正文预留字幕区域，判据见上文的三项硬判定。

准备记录里的音轨路径相对作品根解析，越界或摘要不符直接报错，不跨作品合成；
字段与校验见 [配音与字幕](media-contract.md)，成片命名与默认输出位置见
[目录约定与输出路径](paths-and-outputs.md)。

通用类型（`general`）的配音不走准备记录里的分段音轨，而是由计划里的 `narration` 与可选
`soundtrack.music` 在 prepare 阶段合成，字段见 [配音与字幕](media-contract.md) 的音床一节。
各类型的成片音轨使用同一组交付参数：**AAC-LC / 44.1kHz / 立体声**，通用片与文章同为 128k，
不能沿用源音轨 24kHz 单声道的规格——24kHz 单声道 AAC 会被 Windows Media Foundation 拒绝打开。

## 成片溯源（`<名字>.provenance.json`）

渲染成功后会在成片旁边写一份溯源，例如 `video.mp4` → `video.provenance.json`。
它回答的是「这支片子是哪一版资产渲的」，因为成片不入库、也没有别的东西会提醒你它
已经落后于源码：实测发生过两支作品的成片比动效重写早了几个小时，仍然带着被修掉的
旧曲线，看上去却仍然是「上次验收通过」的样子。只有正式导出写溯源，预演不写。

字段（`schemaVersion` 当前为 `1`）：

| 字段 | 说明 |
| --- | --- |
| `schemaVersion` | 溯源格式版本，当前为 `1` |
| `type` / `projectId` | 视频类型与作品标识 |
| `compositionId` | 渲染用的 composition |
| `renderer` | 画面来源；金融与房价类型写 `remotion`。通用类型的溯源不含这个键——它只可能是当前渲染路径，写不写都一样 |
| `durationInFrames` / `frames`、`fps`、`width`、`height` | 成片参数；金融与房价类型用 `frames`，其余用 `durationInFrames` |
| `preparedFingerprint` / `inputs` | 通用类型：准备记录指纹，以及逐个输入的 sha256（作品材料、源文与图片、`tts` 记录、实现摘要、`renderer` 构建指纹、`audio:<场景>`） |
| `materialsAndAssetsSha256` | 金融与房价类型：材料与资产的整体摘要 |
| `bundleKey` | 打包缓存键，用于确认这份成片用的是哪一份 bundle；金融与房价类型写它，通用类型不写 |

几条口径值得记住：

- **只指纹真正影响画面的东西**：`inputs.renderer` 是 composition 入口沿 import 可达的
  文件摘要——改一个没被任何组件用到的文件不该让成片报落后，而改一个被引用的组件文件
  就该报。第三方依赖由 `package.json` 与锁文件覆盖：依赖版本变了，成片同样判落后。否则闸门会变成噪音，
  人开始忽略它——那等于没有闸门。
- **文本资产按 LF 归一化后哈希，其余按原字节**：git 的换行归一化会在工作区静默翻转
  行尾，只差行尾的文件不该被判成落后（否则会出现人怎么重渲都消不掉的假落后）。
  归一化清单是 `.css` / `.mjs` / `.json` / `.html` / `.svg` / `.md` 一类文本后缀；
  `.ts` / `.tsx` 不在其中，按原字节哈希。
- **键记文件在哪，不记引用怎么写**：仓库 `web/` 别名目录里的文件一律记
  `/__m2v_web__/…` 键，作品自己的文件记 `__m2v_workspace__/…` 键，两者都不在时
  只记文件名。复核时按同一套规则反解，因此换机器、换目录、换内容根都读得回来，
  也不需要再传 `--content-root`。

当前没有自动复核溯源的命令：溯源只如实记录这批指纹，判落后要拿它记的值与当前值比对。
旧的 `version: 3/4` 溯源（含 `captureFormat`、`assets.files` 与页面路径）属于已删除的
网页截图链路，只作历史参考，不要拿来判断当前成片。

## 字体覆盖（缺字机检）

布局量测的第一步会逐个字符检查材料里**会被渲染**的文本是否在字体里有字形，
缺字直接报错并阻断预演与正式导出。判据不是拿某支字体去量，而是**画面实际注册过的
字体**：字体由 `web/src/assets/fonts.json` 声明、`web/src/fonts.ts` 在运行时注册
（文件清单见该目录的 README），量测按清单取出字体文件逐个核对字形——
只有当这些字体加起来都没有某个字形时，浏览器才真的会回退到系统字体——
那正是要抓的东西。清单为空时（画面一个字体文件都没注册）不报缺字：
无从判断，也不凭空拦人。

为什么它必须存在：缺字是唯一一种**静默失败**。浏览器不报错、不警告，直接用
系统字体顶上，字宽、字重、基线全变，而布局量测量的是元素框，照过。
它也是 webfont 子集化的前置条件——不做逐字检查就切字体，
等于把这种漂移变成常态。

范围与边界：

- 扫描材料里会被渲染的字段（`text`/`title`/`subtitle`/`label`/`quote`/`caption`/
  `value`/`unit` 等）；`narrationSegments` 是口播文本、不画在画面上，**不进扫描**；
- 结论定位到 `sceneId.字段`——只说「缺字」不可修；
- 只判「字体里有没有这个字形」，不判字宽字重是否合适，也不判断浏览器
  实际选了哪个字体（那要跑浏览器）。
