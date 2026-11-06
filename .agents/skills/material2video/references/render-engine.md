# 渲染引擎

> **适用范围：** 本文描述成片的渲染路径：Remotion 打包与缓存、渲染会话与并发、字幕量测、
> 视口与画布尺寸、成片编码与码流兼容性、失败表现与调试。
> 契约页与 `window.__M2V__` 接口、`ready()` / `seekToFrame()` 语义、代码场景采集与
> 电影级后期见[代码场景运行契约](code-scene-runtime.md)；交付权限、成片溯源与性能报告见
> [交付与溯源](delivery-and-provenance.md)；缺字机检见[设计令牌](design-tokens.md#缺字机检)。
> 分镜结构见 [通用分镜 v8](storyboard-schema.md)，制作顺序见 [制作流程](production-workflow.md)。

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
   （`output_validation.verify_output`）、搬到最终位置、交付权限修复
   （见[交付权限](delivery-and-provenance.md#交付权限)），
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
- 两侧只通过 stdout 上的前缀行通信（常量在 `src/m2v/engine/remotion/process.py`）：Node 报
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

报告的位置、完整字段与口径见[渲染性能报告](delivery-and-provenance.md#渲染性能报告)；
它是附加信息，写失败只告警，不会让一次已经验收通过的渲染失败。

### 字幕量测

量测不走渲染路径：preview / render 内部用 Playwright 驱动**契约页**，量测针对共享字幕层工作（不加载场景视频），作品画面由原生关键帧、样片和最终文件复核，
而契约页挂的正是渲染会画出的同一份 composition。

通用 v8 的画面是按需录制的**栅格片段**，合成层只回放片段与共享字幕，因此量测能负责的
只剩字幕：

| 判定 | 判据 |
| --- | --- |
| 字幕字号不符 | `data-m2v-subtitle` 的实际计算字号与 `prepared.props.subtitle.fontSize` 不一致 |
| 安全区不符 | `data-m2v-subtitle` 容器的实际矩形与画幅清单里的 `subtitle.safeArea` 不一致 |
| 字幕溢出 | 字幕文字的每一段 client rect 越出安全区 1px 以上 |
| 字幕遮挡 | 字幕文字中心点处的最上层元素不属于字幕层——文字在、但被盖住同样失败 |

判据来自 `prepared.props.subtitle`：prepare 读取 `web/src/frames.json` 默认样式并解析作品可选字号，
由 `measure_script` 注入完整样式 `S` 与安全区 `B`；脚本里不另写字号或几何常量。结果写
`outputs/layout-check.json`，失败会阻断预演与正式导出。

**边界：系统不声称能自动识别录制片段内全部正文或主体遮挡。** 作品正文在栅格片段里，
没有 DOM 可供量测；那部分由制作助手通过关键帧、全片高密度时间标注帧序列与屏幕投影量测复核，记录写进作品
`outputs/visual-notes.md`。此方式不覆盖采样间瞬时运动。旧的模板量测（`data-m2v-box` 容器溢出、正文分区边界、K 系列
观感闸门）已随受控模板一并删除。

### 手机观看字阶

通用横竖屏的共享字幕默认均为40px，默认样式来自 `web/src/frames.json`；general 可用
`project.json.output.subtitle.fontSize` 按作品覆盖为24至56的整数，安全区、行高和配色不变，见
[作品级字幕字号](prepared-and-subtitles.md#作品级字幕字号)。作品须复核手机尺寸下的字幕、正文与主体，不在作品中另画重复字幕。

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
- 通用作品的画幅只支持 1920×1080 与 1080×1920，舞台必须严格等于准备记录里的
  `width × height`；字幕安全区来自 `web/src/frames.json`，由准备阶段注入 props 与 SDK，
  作品代码据此避让。专用类型（金融）的安全性取值见
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

## 配音与字幕

配音与字幕由 `m2v prepare` 写进准备记录（`outputs/prepared.json` 的 `audio.segments` 与
`subtitles`）：音轨在帧渲染完成后由 FFmpeg 合入，字幕由画面自身绘制，**不用 FFmpeg
字幕滤镜**——那会产出与画面排版不同的一套字幕。正文预留字幕区域，判据见上文「字幕量测」的硬判定。

准备记录里的音轨路径相对作品根解析，越界或摘要不符直接报错，不跨作品合成；
字段与校验见[准备记录与字幕](prepared-and-subtitles.md)，音色与停顿节奏见
[配音音色与节奏](voice-and-rhythm.md)，成片命名与默认输出位置见
[目录约定与输出路径](paths.md)。

通用类型（`general`）的配音同样由 prepare 逐段合成并写入准备记录的母版音轨，音床与音效字段见
[文章媒体与音效](article-media-and-sound.md#声音)。
各类型的成片音轨使用同一组交付参数：**AAC-LC / 44.1kHz / 立体声**，通用片与文章同为 128k，
不能沿用源音轨 24kHz 单声道的规格——24kHz 单声道 AAC 会被 Windows Media Foundation 拒绝打开。

## 交付文件的访问权限

成片、准备音轨、代码场景录制片段、导入素材与缓存条目从临时目录交付时如何交回继承权限、
如何复核与排查，见[交付权限](delivery-and-provenance.md#交付权限)。

## 成片溯源（`<名字>.provenance.json`）

溯源文件的位置、字段、类型差异与三条指纹口径见[成片溯源](delivery-and-provenance.md#成片溯源)。

## 字体覆盖（缺字机检）

缺字机检的判据、扫描范围与边界见[设计令牌](design-tokens.md#缺字机检)。

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

材料本身的问题（未知字段、缺图片、缺少已准备的 v8 材料）会在契约页上直接显示错误说明
（`data-m2v-contract-error` 元素），渲染入口报「`__M2V__` 未定义」时先打开页面看它。
