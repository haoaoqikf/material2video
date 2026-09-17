# 渲染契约

动画网页与渲染脚本之间只有这一个接口。只要网页满足本契约，渲染脚本就能把它导出为 MP4；
反过来，任何一项不满足都会在开渲前报错，而不是产出一段有问题的视频。

## 必需接口

网页必须在 `window` 上暴露 `__A2V__` 对象。使用 `assets/timeline.js` 时由
`A2V.mount()` 自动创建，无需手写。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `version` | `number` | 契约版本，当前为 `1` |
| `fps` | `number` | 帧率，必须与分镜 JSON 的 `fps` 一致 |
| `width` | `number` | 画面宽度，必须与分镜 JSON 的 `width` 一致 |
| `height` | `number` | 画面高度，必须与分镜 JSON 的 `height` 一致 |
| `durationInFrames` | `number` | 总帧数，必须等于分镜中所有 `durationInFrames` 之和 |
| `ready()` | `() => Promise<void>` | 资源就绪后 resolve |
| `seekToFrame(frame)` | `(frame: number) => Promise<void>` | 把画面切换到第 frame 帧，绘制完成后 resolve |

`frame` 从 `0` 开始，最大值是 `durationInFrames - 1`。

## ready() 的语义

渲染脚本在加载页面后调用一次 `ready()`，并等待它 resolve 才开始截图。
`ready()` 必须保证：

- 字体已加载完成（否则首帧会用回退字体排版，且首帧与后续帧字宽不一致）；
- 图片等外部资源已加载或已明确失败；
- 画面已经绘制过至少一次。

`timeline.js` 的默认实现会在 `document.fonts.ready` 与所有 `<img>` 完成后，
再渲染第 0 帧。

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

`render.py` 在进入渲染模式后会读取本地网页（含同目录的 `<link>` 样式表），
命中 `@keyframes`、`animation:`、`transition:` 时输出警告并指出行号。
只提示不阻断——是否真的闪烁由上面的确定性验收决定，但这类写法几乎必然出问题。

远程 URL（`http://` / `https://`）与网页目录之外的样式不参与扫描。

## 可复用的动效原语

`assets/timeline.js` 提供一组**纯函数**原语，全部只依赖入参，不保存跨帧状态。
配方与推荐帧数见 [竖屏视觉规范](visual-spec.md)。

| 原语 | 用途 |
| --- | --- |
| `progress(localFrame, start, duration, easing)` | 计算片段进度 0..1 |
| `stagger(index, stepFrames, baseFrame)` | 逐项呈现时第 i 项的起始帧 |
| `enter(el, p, { distance, axis, scale, opacity })` | 透明度 + 位移 + 缩放 |
| `spring(p, { damping, frequency })` | 解析式阻尼振子，给入场一点微过冲 |
| `range(p, from, to, { clamp })` | 把进度映射为任意数值（位移、光晕强度等） |
| `breath(localFrame, { periodFrames, amplitude })` | 常驻微动，避免后段完全静止 |
| `drawPath(svgPath, p, { length })` | SVG 描边动画；长度由调用方测一次后传入 |
| `revealChars(el, text, p, { frame, staggerFrames })` | 逐字揭示，文本结构不变 |

`spring` 与 `breath` 都是闭式表达式（不迭代积分），因此同一帧永远得到同一结果。
`drawPath` 不每帧测量路径：调用方用 `getTotalLength()` 量一次并缓存。
`revealChars` 会重建单字节点，页面需提供基础样式：

```css
.reveal-char { display: inline-block; white-space: pre; }
.reveal-char.is-break { display: block; height: 0; }
```

## 中间帧格式

渲染脚本默认用 JPEG（q98）截取中间帧，再交给 x264 编码。原因是有实测依据的：
1080 × 1920 下单帧截图 JPEG 约 66ms，PNG 约 225ms，差距约 3.4 倍；q98 对文字
画面几乎无可感损失，且最终输出的 H.264 `yuv420p` 本身也是 4:2:0 有损格式。

需要逐像素比对或存档无损中间帧时，改用 `--capture-format png`。

## 预览缩放与渲染模式

`assets/base.css` 默认让舞台（`[data-a2v-stage]`）保持 1080 × 1920 的逻辑尺寸，
预览时由 `timeline.js` 用 `transform: scale()` 整体缩放，**不改变内部布局**，
因此预览与导出共用同一套坐标。

渲染脚本在截图前会给 `<html>` 加上 `a2v-rendering` 类，`base.css` 据此：

- 隐藏所有 `[data-a2v-controls]` 与 `.a2v-preview-only` 元素；
- 用 `transform: none !important` 取消预览缩放。

因此播放控件、调试标记请加上 `a2v-preview-only` 类或放在 `[data-a2v-controls]` 内，
它们不会出现在成片里。

## 视口与画布尺寸

渲染脚本把浏览器视口设置为分镜声明的 `width × height`，并按该尺寸截图整个视口。
所以：

- 舞台必须严格等于 `width × height`，不要在外层加 margin 或 padding；
- 页面不能出现滚动条（`base.css` 已在 `html, body` 上设置 `overflow: hidden`）；
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
| 未定义 `window.__A2V__` | 等待超时后报错，并附带页面控制台的报错信息 |
| `ready` 或 `seekToFrame` 不是函数 | 报错终止 |
| `fps` / `durationInFrames` / `width` / `height` 不是正整数 | 报错终止 |
| 网页与分镜的 fps 或总帧数不一致 | 报错终止，并列出两边的值 |
| 舞台尺寸与契约不一致 | 警告，继续渲染 |
| 文档尺寸超出视口 | 警告，提示可能存在溢出裁切 |
| 样式里出现 `animation` / `transition` / `@keyframes` | 警告并指出行号，继续渲染（是否闪烁由确定性验收决定） |

## 调试

使用 `assets/timeline.js` 时，浏览器控制台里可以直接驱动时间轴：

```js
A2V.controller.seek(300);        // 跳到第 300 帧
A2V.controller.play();           // 播放
A2V.controller.currentFrame();   // 当前帧号
A2V.timeline.scenes;             // 场景起止帧
```

渲染脚本只依赖上表的 `__A2V__` 契约，不使用 `A2V.controller`，
因此自建网页可以不实现它。

## 可选配音与字幕

使用 `--media` 时，命令为页面 URL 添加 `a2v-media` 查询参数。共享运行时通过
`A2V.fetchStoryboard()` 读取清单、比对原分镜并在 mount 前应用派生时长，返回值仍为分镜对象。
页面 mount 后等待 `__A2V__.ready()`，包括字体、音频就绪与首帧。

契约增加可选 `mediaFingerprint`（源分镜 SHA-256，无媒体时为 null）；有声渲染必须匹配。
`durationInFrames` 声明派生后的总帧数。`seekToFrame` 始终暂停播放，字幕只由指定帧确定。
预览播放使用音轨 currentTime 驱动画面；导出模式不播放音频，合成由 FFmpeg 完成。

正文预留字幕区域，字幕在同一网页绘制，禁止另用 FFmpeg 字幕滤镜产生不同排版。
内联分镜或自建运行时的无声契约继续兼容；有声功能要求采用上述加载流程。
媒体服务器只绑定回环地址，支持 CORS 和字节 Range，允许素材在仓库外并支持音频跳转。
清单字段与校验见 [配音与字幕](media-contract.md)；
成片命名与默认输出位置见 [目录约定与输出路径](paths-and-outputs.md)。
