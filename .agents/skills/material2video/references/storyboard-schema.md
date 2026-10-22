# 通用分镜 v8

本页配合[节奏、美术、声音与制作阶段](creative-production.md)执行：先整片粗预演、风险优先，再按阶段完成条件精制与复查；不增加用户确认或 CLI 人工门禁。

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
每项可选 `holdFrames`（0～1800）：本段旁白结束后、下一段开始前的静默帧数，只用于同一幕内的
连续旁白；最后一段不得声明，收尾留白用 `tailFrames`。静默计入 `durationFrames` 的最小值，
`segmentWindows` 仍只表示发声窗口，字幕与音效引用自动后移。段间静默是**单幕一镜到底**在
不打断口播的前提下保留观察时间的唯一方式。

整片只有音床、没有旁白的作品，`durationFrames` 决定全片长度：先取音频的 60 fps 总帧数
`(samples × 60 + sampleRate - 1) // sampleRate`，再分配到各幕。全部幕使用 `cut` 时
`sum(durationFrames)` 等于总帧数；使用 `fade`/`crossfade` 时另加重叠帧。`soundtrack.music`
必须显式写 `gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`，否则默认 −24 dB 与
500ms 淡化会改变原音频。音轨来源与授权要求见
[文章媒体与音效](article-media-and-sound.md#复用参考音轨受控例外)。

### 一镜到底

真正的一镜到底必须写成**单幕 + 多个首尾相接的镜头**：每一幕都会独立录制，跨幕相机必然跳变，
叠化只能掩盖。约定：

- 所有镜头窗口严格相接（`shots[i].endFrame === shots[i+1].startFrame`，`startFrame` 从 0 起、
  末镜到幕时长），不得使用 `cut: true`；
- 相邻镜头路径的末点与首点完全相同；所有镜头 `easing: "linear"`，因为 `sineInOut` /
  `quintInOut` 会让速度在每个镜头边界归零；
- 站点镜头写成「远入点 → 接近 → 近天体绕行 → 拉远 → 远出点」：远点在 1.6–2.0 倍特写距离之外，接近段放在旁白开始前，旁白开口时已经在特写，最后再拉远。只靠短位移加朝向混合会让换站看起来像闪切。
- 站点之间的过场 MUST 抬升到黄道面上方，从上一站远出点穿过两星之间的空间再下降到下一站远入点；过场两端速度接住相邻站点的出口/入口速度，控制点按分段速度曲线采样。
- 土星这类依赖特定视角的 hero 可单独指定轨道形状（例如跨环平面的 4 点弧），不要为了统一公式牺牲已验证的构图。
- 所有镜头使用**同一组 `post` 参数**：`PostFX` 不做边界混合，逐镜不同值会硬跳；
- 幕级 `body`/`chapter` 不再有意义，作品代码应按 `segmentWindows` 与当前镜头自行推导身份。

## 可选字段

下面是统一制作流程中的**可选**字段。作品不写它们时，准备记录、缓存键与时间轴保持默认；
写了就进入准备指纹与代码片段缓存键，改任意一项都要重新 prepare。
可选字段、电影级共享套件与 `lookdev` / `qa` / `assets audit` 入口已经落地；
太阳系一镜到底参考片保留旧版135秒的历史记录；当前预算与复核状态见示例文档；旧用户确认不代替当前版本完整复核。
镜头语法与检查表见[电影级表现与质量工具](cinematic-video.md)。

制作档位已经删除：`project.json` 不得再写 `productionProfile`（包括 `null`），`prepare` 也不再接受
`--profile`；旧声明会被明确拒绝，需要删除后重新 prepare。

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
  整片至少 3 个 hero，每个 hero 是一段 8～12 秒（480～720 帧）的连续镜头。可选 `cut: true`
  表示这一镜**硬切**进入：路径不接上一个镜头的出口，而是直接跳到本章的建立机位（只能向前跳，
  不能退回上一个镜头之前）。
- `look`：look bible 的代码化参数，`profile`（必填）加可选 `lut`（内置调色档名，见下）、`grain`、`bloom`、`dof`、
  `vignette`、`exposure` 与 `motion`。`motion` 只在需要时用：
  `{"subframes": 1–4, "supersample": 1–2}`——`subframes` 是 **hero 镜头内每帧**的子帧数
  （等效快门时间内的运动模糊，非 hero 镜头始终 1 帧），`supersample` 为 2 时按 2 倍设备像素
  采集、编码时降采样回目标画幅（SSAA）。两者都进片段缓存键；未声明 `motion` 时缓存键与既有一致。

镜头时间窗在**准备阶段**校验（真实分段时长来自 TTS）：每个镜头必须落在本幕时长内；声明
`segment` 的镜头还必须**完整覆盖**该旁白段的窗口，没有声明的镜头只查幕时长（8–12 秒的 hero
通常跨过留白与相邻旁白）。非法时错误按 `scenes[<幕>].content.props.shots[<镜头 id>]` 定位。

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
- `useMediaAsset(id)` 按素材 ID 返回已导入素材的 `{src, kind, width, height, durationSeconds,
  colorSpace, alpha, license}`；未知 ID 明确抛错。映射由准备阶段复核 `assets/media-sources.json`
  后注入，本地服务器只暴露登记过的文件。`colorSpace`/`alpha` 由实测像素格式推导、`license` 取
  登记原文，因此不需要为了拿到它们重新导入素材。
- 可用的共享依赖为 React、`motion`、`three`、`@react-three/fiber`、`@react-three/drei`、
  `gsap`、`echarts`（`Chart` 是 ECharts 封装，宽高默认取当前画布）以及电影级后期所需的
  `postprocessing` 与 `@react-three/postprocessing`。依赖缺失时在打包前明确失败，不会静默
  渲染成没有后期的画面。

### 电影级共享套件

`m2v/code-scene` 另外导出电影级元件；作品不引用它们时画面与既有一致（已验证：
把套件从 SDK 导出里摘掉后，标准画面逐像素相同）。

| 元件 | 作用 |
|---|---|
| `LookProvider` / `useLook` / `useShot` | look 与镜头清单的上下文；不套 provider 时读录制配置里的 `props` |
| `CameraRig` | 按镜头路径（CatmullRom 或关键帧）与缓动推进相机，含每镜头 FOV/滚转/曝光与焦点拉移 |
| `PostFX` | Bloom、DOF、grain、vignette、色散与具名调色，全部帧驱动 |
| `Starfield` / `ParticleBelt` / `OortCloud` | 固定种子的点云：星空、环带与远距离壳层 |
| `SunSurface` / `Corona` / `Prominence` / `Atmosphere` / `Rings` | 日面、日冕、日珥、大气与行星环 |
| `Comet` | 彗核与背向太阳的尾迹 |
| `pathIntersectsSphere` / `cameraPathRisk` / `backgroundRisk` | 穿球、余量不足与背景裁切的纯函数检查 |
| `activeShot` / `ease` / `seededRandom` / `hashSeed` | 帧到镜头的映射、缓动与确定性随机 |

- **一切随时间变化的东西由 `elapsedSeconds`/帧号驱动**：不使用挂钟、`Math.random`、CSS 动画或
  组件计时器。粒子与噪声用「固定种子 + 帧号」的确定性哈希，同一帧在任何一次录制里都相同
  （真实浏览器验证：同帧两次独立录制 PSNR ≥ 60dB）。
- `lut` 是**内置调色档名**（`neutral`、`deep-space`、`teal-amber`、`warm-film`），不是外部
  `.cube` 文件：录制期不取外网，也不读作品目录。
- `PostFX` 使用 `multisampling={0}` 且自带确定性颗粒效果；库里的 `Noise` 依赖 `Math.random`
  生成的噪点纹理，跨次运行不一致，因此不采用。
- 作品的焦点目标通过 `CameraRig` 的 `targets` 传入（`Object3D`、`Vector3` 或无参函数），
  镜头 `focus.target` 按名字在其中查找。

录制在无头 Chromium 中按受控时钟逐帧进行：viewport、页面根元素、ffmpeg 标准化尺寸与 composition 都用
同一画幅。只开放**已登记媒体**与仓库字体，作品目录下的其他文件、导入记录、源文都不暴露；
外网请求、WebSocket、超时与运行异常都会让录制失败，不生成有效候选；准备阶段只检查材料与源码。片段是不带音轨的
60 fps 视频，声音一律由统一音轨处理；素材原声不会进入母版。

录制按源码可达输入、`props`、本幕时间窗、**画幅与字幕安全区**、**媒体映射与导入摘要**、
共享实现与锁文件、浏览器及编码配置绑定缓存，片段与摘要落在 `outputs/code-cache/`，缓存额外绑定采集区间，整幕生成复用已录区间并只补齐缺口；任何一项
变化都会让旧准备失效并要求重新准备并生成当前候选。检查和正式生成按区间复用录制缓存，完整成片只生成一次，
最终合成只回放片段；缺少片段时先按需执行作品代码录制；每帧以 n/fps 秒完成绘制再采集，截图和磁盘等待不推进动画；缺帧明确失败，不以重复帧补齐。不提供任意倒序求帧，也不保证任意作品逐像素复现。

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
能自动识别其中的全部正文或主体遮挡——那部分由制作助手通过关键帧、全片时间标注帧序列及屏幕投影量测补足，并披露采样间运动风险。

最小示例：

```json
{"version":8,"schemaVersion":8,"fps":60,"width":1920,"height":1080,"title":"反馈帮助改进","input":{"kind":"article"},"targetSeconds":60,"scenes":[{"id":"opening","template":"code","content":{"title":"开场","entry":"scenes/opening.tsx"},"narrationSegments":[{"id":"line","text":"观察结果，根据反馈修正下一次的做法。"}]}]}
```

完整示例：[从电报到大模型](../../../../examples/american-science-milestones/storyboard.json)、
[交通拥堵波](../../../../examples/traffic-jam-wave/storyboard.json)、
[太阳系之旅](../../../../examples/solar-system-journey/storyboard.json)。当前规格见
[article-explainer](../../../../openspec/specs/article-explainer/spec.md)。
