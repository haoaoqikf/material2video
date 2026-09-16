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

> 判断标准：把第 300 帧连续渲染两次，两次截图应该完全一致。

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

## 失败表现

| 情况 | 结果 |
| --- | --- |
| 未定义 `window.__A2V__` | 等待超时后报错，并附带页面控制台的报错信息 |
| `ready` 或 `seekToFrame` 不是函数 | 报错终止 |
| `fps` / `durationInFrames` / `width` / `height` 不是正整数 | 报错终止 |
| 网页与分镜的 fps 或总帧数不一致 | 报错终止，并列出两边的值 |
| 舞台尺寸与契约不一致 | 警告，继续渲染 |
| 文档尺寸超出视口 | 警告，提示可能存在溢出裁切 |

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
清单字段与校验见 [配音与字幕](media-contract.md)。
