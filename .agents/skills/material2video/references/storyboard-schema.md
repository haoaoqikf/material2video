# 通用分镜 v8

`general` 只接受 `version: 8`、`schemaVersion: 8`。v7 及更早分镜必须重新编排，不自动迁移；
历史测试分镜不属于制作入口。

v8 的画幅、配色、构图与动效都由**作品代码**决定：分镜里没有模板，没有主题，也没有屏幕摘要
字段。作品说明与创作依据见各示例的 `DESIGN.md`。

## 全片与场景

全片声明 `fps: 60`、`title`、`input`、可选 `width`/`height`、可选 `targetSeconds`、可选顶层
`soundtrack` 和非空 `scenes`（最多 300 幕）。

**画幅**只支持 1920×1080 横屏与 1080×1920 竖屏：两边都省略时规范化为横屏并写进准备产物；
只写一边、写成非整数、方屏或其他组合一律拒绝。全片使用同一画幅，不自动裁切或重新排版。
`targetSeconds` 为 1～600 的整数，默认 60，只用于分配无旁白镜头的剩余时长。

`input` 为 `{"kind":"article"}` 时绑定作品 `article.md` 或明确采用的 `article.accepted.md`
（也可在 `project.materials.article` 指定作品内文件），必须先通过源文语义审查；为
`{"kind":"topic","topic":"<非空主题>"}` 时只声明主题，跳过源文与源文语义审查，此时每幕必须
声明 `keywords`。

每幕声明 `id`、`template`（只能是 `code`）、`content`、`narrationSegments`，可选 `keywords`、
`durationFrames`、`transition`、`transitionFrames`、`speech`。转场支持 `cut`、`fade`、
`crossfade`，首幕只能 cut；`transitionFrames` 为 1～3600 的整数，默认 16。`durationFrames` 为
1～36000 的整数，声明后必须容得下旁白、24 帧阅读停留与转场，不得截断口播，它同时是录制片段
长度。场景及旁白 ID 全片唯一；未知字段、`visual`、`aspectRatio` 与旧的展示元素字段一律拒绝。

`content` 只接受 `title`（可选，仅作元数据）、`entry`（必填）与 `props`（可选，默认空对象）。
`narrationSegments` 每项为 `{id,text}`，文字非空；`code` 幕可以没有旁白（0～30 项），此时镜头
长度取声明的 `durationFrames`，未声明时与其余无旁白镜头平分 `targetSeconds` 的剩余帧数。

## cinematic 可选字段

下面是 cinematic 档位新增的**可选**字段。standard 作品不写它们，准备记录、缓存键与时间轴
都与现在完全一致；写了就进入准备指纹与代码片段缓存键，改任意一项都要重新 prepare。
档位、字段与命令随 cinematic 变更落地，实现完成前仓库实际可用的仍是 standard 链路；
档位模型、镜头语法与检查表见[电影级制作档位](cinematic-video.md)。

档位声明在**作品** `project.json`（不在分镜里）：

```json
{"productionProfile": "cinematic"}
```

`productionProfile` 只接受 `standard`/`cinematic`，缺省 standard；`prepare --profile` 可临时覆盖，
准备记录、预演与溯源记录实际生效的档位与来源。

幕级新增三个可选帧数字段：

| 字段 | 范围 | 说明 |
|---|---|---|
| `leadInFrames` | 0～1800 | 旁白之前的留白（冷开场），默认 0 |
| `tailFrames` | 0～1800 | 阅读停留之后的留白（收尾），默认 0 |
| `readingHoldFrames` | 0～360 | 本幕声音结束后的稳定阅读帧数，默认 24 |

`content.props` 新增两个可选对象：

- `shots`：镜头清单。每项声明 `id`（全片唯一）、`target`、`tier`（`hero`/`major`/`minor`）、
  可选 `segment`（本幕的旁白段 id）、`startFrame`/`endFrame`（**幕内相对帧**），以及可选的
  `camera`（`path`/`fov`/`roll`/`easing`/`keyframes`）、`focus`（`target`/`distance`/`aperture`）、
  `exposure`（`ev`）与 `post`（`bloom`/`dof`/`grain`/`vignette`/`chromaticAberration`/`lut`）。
  整片至少 3 个 hero，每个 hero 是一段 8～12 秒（480～720 帧）的连续镜头。
- `look`：look bible 的代码化参数，`profile`（必填）加可选 `lut`、`grain`、`bloom`、`dof`、
  `vignette` 与 `exposure`。

镜头时间窗在**准备阶段**校验（真实分段时长来自 TTS）：声明 `segment` 的镜头必须落在该旁白段
窗口内；没有声明的镜头只能落在留白区（前导段或收尾段），不允许横跨旁白。非法时错误按
`scenes[<幕>].content.props.shots[<镜头 id>]` 定位。

`narrationSegments` 每项新增可选 `claims`：本段旁白声称的画面特征（最多 12 条、每条不超过
80 字符、不得重复）。它不改变时间轴，只用于预演后检查该时间窗内特征是否真的可见。

## 全画布代码场景（code）

`content.entry` 必须是作品 `scenes/` 下存在的相对 TSX 路径。路径越界、缺少文件、非 TSX 后缀、
未批准的依赖或远程模块都会在构建时拒绝；工具不会安装作品自己的依赖。
组件从 `m2v/code-scene` 取得上下文与 SDK：

```tsx
import {useSceneContext, useMediaAsset, Chart, motion, gsap, THREE, Canvas, Float, echarts,
  type CodeSceneProps} from 'm2v/code-scene';
```

- `useSceneContext()` 给出 `running`、`elapsedSeconds`、`progress` 与 `ready()`；
  组件必须在字体与自有素材就绪后调用 `ready()`，否则录制会超时失败。
- 组件同时收到 `props`（分镜里的 JSON 对象）、`fps`、`durationInFrames`、`width`、`height`、
  `subtitleSafeArea`（`{x,y,width,height}`）与 `segmentWindows`（本幕各旁白段在本幕内的帧窗口）。
- **作品代码控制整张画布**：自己铺满 `width`×`height` 并绘制不透明背景。录制页不按任何主题设置
  前背景，页面底色只是编码兜底——没有铺满的作品会在成片里留出这块底色。
- **`subtitleSafeArea` 是硬约束**：共享字幕层会盖在这个矩形里，重要文字与主体必须避让，
  背景可以延伸进去。矩形取值来自画幅清单，两种画幅各有取值。
- `useMediaAsset(id)` 按素材 ID 返回已导入素材的 `{src, kind, width, height, durationSeconds}`；
  未知 ID 明确抛错。映射由准备阶段复核 `assets/media-sources.json` 后注入，本地服务器只暴露
  登记过的文件。
- 可用的共享依赖为 React、`motion`、`three`、`@react-three/fiber`、`@react-three/drei`、
  `gsap` 与 `echarts`（`Chart` 是 ECharts 封装，宽高默认取当前画布）。

录制在无头 Chromium 中按受控时钟逐帧进行：viewport、页面根元素、ffmpeg 标准化尺寸与 composition 都用
同一画幅。只开放**已登记媒体**与仓库字体，作品目录下的其他文件、导入记录、源文都不暴露；
外网请求、WebSocket、超时与运行异常都会让 `prepare` 失败且不保存准备记录。片段是不带音轨的
60 fps 视频，声音一律由统一音轨处理；素材原声不会进入母版。

准备按源码可达输入、`props`、本幕时间窗、**画幅与字幕安全区**、**媒体映射与导入摘要**、
共享实现与锁文件、浏览器及编码配置绑定缓存，片段与摘要落在 `outputs/code-cache/`；任何一项
变化都会让旧准备失效并要求重新准备与完整预演。完整预演和正式导出复用同一段已验收片段，
导出不再执行作品代码；每帧以 n/fps 秒完成绘制再采集，截图和磁盘等待不推进动画；缺帧明确失败，不以重复帧补齐。不提供任意倒序求帧，也不保证任意作品逐像素复现。

## 时间轴与字幕

每段使用共享 TTS 独立合成，以实际音频推导帧数、字幕与画面时间窗。每幕声音结束后保留 24 帧
稳定阅读，默认硬切。`fade`/`crossfade` 在前一幕完整阅读尾段之后按 `transitionFrames` 交叉淡化，
下一幕配音在淡化结束后开始，前后口播不重叠。音轨不截断、不重叠，母版轨严格裁到全片时长。
完整成片含停留及淡化最多 36000 帧（600 秒）。

默认根据旁白原文自动生成画面字幕，预演和正式导出共用同一字幕层，无需配置开关；字幕烧录进
画面，不导出外置字幕文件，因此「有字幕」只能以成片里的可见文字为准。字幕使用真实配音派生的
帧边界，开始帧显示、结束帧隐藏，无讲话的停顿及阅读尾段不显示。字幕层用白字配不透明深色底板，
**独立于作品配色**，两种画幅各有字号、行高与安全区，取值与 SDK 给出的是同一份配置。

准备输出 `compiledScenes`、`subtitleCues`、`subtitle`、`width`、`height` 与 `durationInFrames`，
每幕另派生 `mediaPath`（录制的片段）与 `trimStartFrames`（恒为 0）；这些为派生字段，不写回分镜。
浏览器量测只检查**字幕**：安全区矩形、换行范围与实际可见性。作品正文在栅格片段里，系统不声称
能自动识别其中的全部正文或主体遮挡——那部分由制作助手实际观看补足。

最小示例：

```json
{"version":8,"schemaVersion":8,"fps":60,"width":1920,"height":1080,"title":"反馈帮助改进","input":{"kind":"article"},"targetSeconds":60,"scenes":[{"id":"opening","template":"code","content":{"title":"开场","entry":"scenes/opening.tsx"},"narrationSegments":[{"id":"line","text":"观察结果，根据反馈修正下一次的做法。"}]}]}
```

完整示例：[缓冲](../../../../examples/buffer-smoothing/storyboard.json)、
[试错](../../../../examples/darts-trial-and-error/storyboard.json)、
[太阳系之旅](../../../../examples/solar-system-journey/storyboard.json)。当前规格见
[article-explainer](../../../../openspec/specs/article-explainer/spec.md)。
