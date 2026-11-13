# 五类统一分镜 v9

> **独立工程**：作品从本地 `src/code-scene/` 导入接口；按需采用的参考组件连同递归依赖、资源和许可落到作品，不解析 `m2v/*`。

本页提供制作技术契约；创作从[研究与试制](stage-research.md)进入，先解决影响方向判断的关键未知，再按[正式设计](stage-design.md)组织全片预演。

五类只接受 `version: 9`、`schemaVersion: 9`。v8 及更早分镜必须重新编排，不自动迁移；
历史测试分镜不属于制作入口。

v9 的画幅、配色、构图与动效都由**作品代码**决定：分镜里没有模板，没有主题，也没有屏幕摘要
字段。作品说明与创作依据见各示例的 `DESIGN.md`。

帧率规则：`project.json.output.fps` 与本文件 `fps` 均声明时必须一致，仅一处声明时使用该值，都省略则默认30；只接受整数30或60。所有显式帧数字段按实际fps解释，不自动缩放；切换帧率须由作者调整帧预算并重新 prepare。现有显式60帧示例保持原值。

共享旁白字幕字号可在 `project.json.output.subtitle.fontSize` 设置24至56的整数；省略仍为画幅默认40px。它不属于分镜字段，配置与准备绑定见[作品级字幕字号](prepared-and-subtitles.md#作品级字幕字号)。

## 全片与场景

全片可声明 `fps: 30` 或 `fps: 60`，并声明 `title`、`input`、可选 `width`/`height`、可选 `targetSeconds`、可选顶层
`soundtrack` 和非空 `scenes`（最多 300 幕）。

`soundtrack.effects` 可以用 `assetId` 引用统一音效库，也可以使用内置 `builtin` 或本地 `sourceRef`（三选一）。`offsetFrames` 默认相对本幕开始帧，与 `offsetMs`、`segmentId` 互斥；声明 `eventId` 后改为相对本幕事件帧，详见下方「幕内事件」。播放支持 `trimStartMs`、`durationMs`、`loop`、`fadeInMs`、`fadeOutMs` 与 `pan`，均实际参与混音。字段范围、来源登记与示例见[媒体与音效](article-media-and-sound.md#统一音效库)。

**画幅**只支持 1920×1080 横屏与 1080×1920 竖屏：两边都省略时规范化为横屏并写进准备产物；
只写一边、写成非整数、方屏或其他组合一律拒绝。全片使用同一画幅，不自动裁切或重新排版。
`targetSeconds` 为 1～600 的整数，默认 60，只用于分配无旁白镜头的剩余时长。

`input` 为 `{"kind":"article"}` 时绑定作品 `article.md` 或明确采用的 `article.accepted.md`
（也可在 `project.materials.article` 指定作品内文件），必须先通过源文语义审查；为
`{"kind":"topic","topic":"<非空主题>"}` 时只声明主题，跳过源文与源文语义审查，此时每幕必须
声明 `keywords`。

每幕声明 `id`、`template`（只能是 `code`）、`content`、`narrationSegments`，可选 `keywords`、
`durationFrames`、`transition`、`transitionFrames`、`speech`、`events`。转场支持 `cut`、`fade`、
`crossfade`、`slide-left`、`slide-right`、`wipe-left`、`wipe-right`、`iris`、`clock-wipe`，首幕只能 cut；名称/方向以 `web/src/transitions.json` 为准，说明见[通用转场](visual-components.md#通用转场)。`transitionFrames` 为1～`60 × fps`的整数，默认 `round(8 / 30 × fps)`（30/60 fps下为8/16帧）。`durationFrames` 为
1～`600 × fps`的整数，声明后必须容得下旁白、默认0.4秒阅读停留与转场，不得截断口播，它同时是录制片段
长度。场景及旁白 ID 全片唯一；未知字段、`visual`、`aspectRatio` 与旧的展示元素字段一律拒绝。

`content` 接受 `title`（可选，仅作元数据）、`entry`（必填）、`props`（可选，默认空对象）与 `sourceIds`（可选，当前幕引用的结构化来源 ID）。
`content.props` 可声明保留键 `capture`：

```json
{"mode": "sequential", "timebase": "local", "jobs": 1, "blockFrames": 30, "verifyFrames": 4}
```

- `mode` 为 `sequential`（默认）或 `pure-time`；`pure-time` 隐含 `timebase: "global"`，且画面只能由时间、props 与事件推导。
- `timebase: "global"` 让录制上下文提供 `globalSeconds/globalFrame`；`local` 保持幕内时间。
- `jobs` 为 1–4，`blockFrames` 默认等于 fps，`verifyFrames` 为 2–4；这些是运行时参数，不进入片段缓存键。
- `mode` 与 `sceneStartFrame` 进入缓存键；未声明 `capture` 时配置与缓存键保持原样。

写法见[全局时间与连续行为](code-scene-runtime.md#全局时间与连续行为)与[纯时间采集](code-scene-runtime.md#纯时间采集opt-in)。
`narrationSegments` 每项为 `{id,text,translation?}`，文字非空；`translation` 可选，为英文次行提供文本，prepare 按与中文相同的标点规则拆分并与中文字幕逐条配对，条数不符直接失败。`code` 幕可以没有旁白（0～30 项），此时镜头
长度取声明的 `durationFrames`，未声明时与其余无旁白镜头平分 `targetSeconds` 的剩余帧数。
每项可选 `holdFrames`（0～`30 × fps`）：本段旁白结束后、下一段开始前的静默帧数，只用于同一幕内的
连续旁白；最后一段不得声明，收尾留白用 `tailFrames`。静默计入 `durationFrames` 的最小值，
`segmentWindows` 仍只表示发声窗口，字幕与音效引用自动后移。段间静默是**单幕一镜到底**在
不打断口播的前提下保留观察时间的唯一方式。

整片只有音床、没有旁白的作品，`durationFrames` 决定全片长度：先按作品实际fps从采样数向上取整计算总帧数
`(samples × fps + sampleRate - 1) // sampleRate`，再分配到各幕。全部幕使用 `cut` 时
`sum(durationFrames)` 等于总帧数；使用 `fade`/`crossfade` 时另加重叠帧。`soundtrack.music`
必须显式写 `gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`，否则默认 −24 dB 与
500ms 淡化会改变原音频。音轨来源与授权要求见
[文章媒体与音效](article-media-and-sound.md#复用参考音轨受控例外)。

### 幕内事件

每幕可选 `events: [{"id":"contact","frame":90}]`，最多1024项；每项只接受非空 `id` 和0～36000整数 `frame`。ID在本幕唯一，不同幕可重名，不同事件可同帧。事件帧必须小于实际幕长：显式时长在校验时检查，自动时长在 prepare 确定后检查，不自动延长幕。

音效写 `{"builtin":"click","sceneId":"experiment","eventId":"contact","offsetFrames":0}`，引用本幕事件；`offsetFrames` 可省略为0，事件引用与 `segmentId`、`offsetMs` 互斥。偏移后的起点仍须位于所属幕内，素材播放尾部沿既有全片裁切规则处理。独立音效保留原定位方式。

prepare 将事件解析为场景 `eventFrames`（ID→幕内帧）和准备产物 `props.resolvedEvents`（含 `sceneId/id/frame/globalFrame`）；音效实际全片起点保存在 `props.effectStartFrames`，毫秒定位可能产生分数帧。`outputs/events.json` 绑定 `preparedFingerprint` 并列出事件与音效起点。改事件后须重新 prepare，相关录制配置与准备指纹变化。场景使用方式见[事件查询](code-scene-runtime.md#幕内事件查询)；围绕事件看图用 `m2v lookdev --event <sceneId:eventId> --before <帧> --after <帧> [--hold <帧>]`，它是预览，不替代独立评审证据。

需要声画同步时，画面与音效共用同一 `eventFrames` 来源，避免重复维护动作时刻；声音预告或延迟反馈可以通过既有 `offsetFrames` 明确偏移，独立氛围与情绪声音也可按原有显式时间定位，不强制每个声音对应可见动作。设计意图复用现有记录，不要求固定角色、稳定素材或单独 `SOUND.md`；来源与混音字段仍按[声音契约](article-media-and-sound.md#声音)核对。现有能力没有 effect 级音高参数，不因引入风格参考扩展字段或修改混音契约。

### 一镜到底

真正的一镜到底必须写成**单幕 + 多个首尾相接的镜头**：每一幕都会独立录制，跨幕相机必然跳变，
叠化只能掩盖。约定：

- 所有镜头窗口严格相接（`shots[i].endFrame === shots[i+1].startFrame`，`startFrame` 从 0 起、
  末镜到幕时长），不得使用 `cut: true`；
- 相邻镜头路径的末点与首点完全相同；所有镜头 `easing: "linear"`，因为 `easeInOutSine` /
  `easeInOutQuint` 会让速度在每个镜头边界归零；
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
镜头语法与检查表见[代码场景运行时契约](code-scene-runtime.md)。

制作档位已经删除：`project.json` 不得再写 `productionProfile`（包括 `null`），`prepare` 也不再接受
`--profile`；旧声明会被明确拒绝，需要删除后重新 prepare。

幕级新增三个可选帧数字段：

| 字段 | 范围 | 说明 |
|---|---|---|
| `leadInFrames` | 0～`30 × fps` | 旁白之前的留白（冷开场），默认 0 |
| `tailFrames` | 0～`30 × fps` | 阅读停留之后的留白（收尾），默认 0 |
| `readingHoldFrames` | 0～`6 × fps` | 本幕声音结束后的稳定阅读帧数，默认0.4秒（30/60 fps下为12/24帧） |

`content.props` 新增两个可选对象：

- `shots`：镜头清单。每项声明 `id`（全片唯一）、`target`、`tier`（`hero`/`major`/`minor`）、
  可选 `segment`（本幕的旁白段 id）、`startFrame`/`endFrame`（**幕内相对帧**），以及可选的
  `camera`（`path`/`fov`/`roll`/`easing`/`keyframes`）、`focus`（`target`/`distance`/`aperture`）、
  `exposure`（`ev`）与 `post`（`bloom`/`dof`/`grain`/`vignette`/`chromaticAberration`/`lut`）。
  整片至少 3 个 hero，每个 hero 是一段 8～12 秒（按作品fps换算为帧数）的连续镜头。可选 `cut: true`
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

### 导演设计映射

复杂未决风险需要导演说明或时间结构时，放在作品 `DESIGN.md` 的必要附件中，不属于 v9 storyboard JSON，也不增加运行时字段。已有镜头等级（A/B/C）仍只记录在设计中，不因等级补造导演卡。用 `scene.id`、`shots[].id` 引用镜头；`shots[].target` 标明观察对象，`startFrame` / `endFrame` 及 `camera` 路径落实实际时序与相机参数。普通场景只需最简设计记录，低成本原型可用于探索未决问题；执行帧与参数不在设计附件中重复维护。

## 全画布代码场景（code）

`content.entry` 必须是作品 `scenes/` 下存在的相对 TSX 路径。路径越界、缺少文件、非 TSX 后缀、
未声明/未安装的依赖或远程模块都会在构建时拒绝；工具不会安装作品自己的依赖。
组件从本地模块取得上下文，第三方包由作品直接声明与导入：

```tsx
import {useSceneContext, type CodeSceneProps} from '../src/code-scene/context';

// 作品本地包装；当前模板不提供共享 useMediaAsset 导出。
function useMediaAsset(id: string) {
  const asset = window.__M2V_CODE_CONFIG__?.media?.[id];
  if (!asset) throw new Error(`未声明或尚未准备的媒体：${id}`);
  return asset;
}
```

- `useSceneContext()` 给出 `running`、`elapsedSeconds`、`progress` 与 `ready()`；
  组件必须在字体与自有素材就绪后调用 `ready()`，否则录制会超时失败。
- 组件同时收到 `props`（分镜里的 JSON 对象）、`fps`、`durationInFrames`、`width`、`height`、
  `subtitleSafeArea`（`{x,y,width,height}`）与 `segmentWindows`（本幕各旁白段在本幕内的帧窗口）。
- **作品代码控制整张画布**：自己铺满 `width`×`height` 并绘制不透明背景。录制页不按任何主题设置
  前背景，页面底色只是编码兜底——没有铺满的作品会在成片里留出这块底色。
- **`subtitleSafeArea` 是硬约束**：共享字幕层会盖在这个矩形里，重要文字与主体必须避让，
  背景可以延伸进去。矩形取值来自画幅清单，两种画幅各有取值。
- 准备阶段复核 `assets/media-sources.json` 后，将素材 ID 到 `{src, kind, width, height, durationSeconds, colorSpace, alpha, license}` 的映射注入 `window.__M2V_CODE_CONFIG__.media`；作品按 ID 读取并对缺失项明确报错。本地服务器只暴露登记过的文件，`colorSpace`/`alpha` 来自实测，`license` 来自登记原文。当前模板不导出 `useMediaAsset`，使用上面的作品本地包装，不从 context 导入不存在的 hook。在组件内用 `useMediaAsset('photo-1')` 这类字面量 ID 调用，便于既有依赖扫描和素材报告识别；动态拼接或直接任意读取不在该扫描覆盖内，须显式核对完整素材来源绑定，不能凭报告宣称无依赖。
- 作品自行选择并在 `package.json` 与锁文件声明精确版本的依赖，记录来源和许可；需要参考封装时递归采用源码。模板没有预装图表或三维组件，不能把参考导出当作工程已有能力。依赖缺失在构建时失败。
- `painter` 命名空间提供可选的二维 Canvas 绘制层，用于辉光质感、高密度粒子、线条生长与逐字
  显影；文字须画在 `overlay` 层，实际画面由媒体证据独立复核。
  用法、层顺序与绘制边界见[运行时契约](code-scene-runtime.md#二维绘制层)。

### 电影级共享套件

主项目 `web/src/code-scene/cinematic/` 提供可采用的电影级参考元件；采用源码、资源及递归依赖后从作品本地模块导入。不采用时不要求安装这些组件，实际表现和确定性须按本片验证。

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
作品实际30或60 fps视频，声音一律由统一音轨处理；素材原声不会进入母版。

录制按源码可达输入、`props`、本幕时间窗、**画幅与字幕安全区**、**媒体映射与导入摘要**、
共享实现与锁文件、浏览器及编码配置绑定缓存，片段与摘要落在 `outputs/code-cache/`，缓存额外绑定采集区间，整幕生成复用已录区间并只补齐缺口；任何一项
变化都会让旧准备失效并要求重新准备并生成当前候选。检查和正式生成按区间复用录制缓存，完整成片只生成一次，
最终合成只回放片段；缺少片段时先按需执行作品代码录制；每帧以 n/fps 秒完成绘制再采集，截图和磁盘等待不推进动画；缺帧明确失败，不以重复帧补齐。不提供任意倒序求帧，也不保证任意作品逐像素复现。

## 时间轴与字幕

每段使用共享 TTS 独立合成，以实际音频推导帧数、字幕与画面时间窗。每幕声音结束后默认保留0.4秒（按作品fps换算为帧数）
稳定阅读，默认硬切。`fade`/`crossfade` 在前一幕完整阅读尾段之后按 `transitionFrames` 交叉淡化，
其他非 cut 转场同样使用这一重叠窗口；下一幕配音在转场结束后开始，前后口播不重叠。音轨不截断、不重叠，母版轨严格裁到全片时长。
完整成片含停留及淡化最多 `600 × fps` 帧（600秒）。

默认根据旁白原文自动生成中文主行字幕；旁白带 `translation` 时同时生成英文次行，预演和正式导出共用同一字幕层，无需配置开关；字幕烧录进
画面，不导出外置字幕文件，因此「有字幕」只能以成片里的可见文字为准。字幕使用真实配音派生的
帧边界，开始帧显示、结束帧隐藏，无讲话的停顿及阅读尾段不显示。字幕层可在 `frames.json` 选择**自适应柔光**（无矩形底板，按每条 cue 的背景亮度/色相采样）或旧的不透明深色底板，
**独立于作品配色**，两种画幅各有字号、行高、安全区与柔光参数，取值与 SDK 给出的是同一份配置。

准备输出 `compiledScenes`、`subtitleCues`、`subtitle`、`width`、`height` 与 `durationInFrames`，
每幕另派生 `mediaPath`（录制的片段）与 `trimStartFrames`（恒为 0）；这些为派生字段，不写回分镜。
浏览器量测只检查**字幕**：安全区矩形、换行范围与实际可见性。作品正文在栅格片段里，系统不声称
能自动识别其中的全部正文或主体遮挡——那部分由制作助手通过关键帧、全片时间标注帧序列及屏幕投影量测补足，并披露采样间运动风险。

最小示例：

```json
{"version":9,"schemaVersion":9,"fps":30,"width":1920,"height":1080,"title":"反馈帮助改进","input":{"kind":"article"},"targetSeconds":60,"scenes":[{"id":"opening","template":"code","content":{"title":"开场","entry":"scenes/opening.tsx"},"narrationSegments":[{"id":"line","text":"观察结果，根据反馈修正下一次的做法。"}]}]}
```

完整示例：[从电报到大模型](../../../../examples/documentary-edit/american-science-milestones/storyboard.json)、
[复利](../../../../examples/data-evolution/compound-interest/storyboard.json)、
[太阳系之旅](../../../../examples/spatial-3d/solar-system-journey/storyboard.json)。当前规格见
[five-video-types](../../../../openspec/specs/five-video-types/spec.md)。

## 结构化来源（v9）

顶层可声明 `sources`：来源 ID 到 `{kind, files}` 的映射。`financial-series` 只可用于 `data-evolution`，文件角色为 `request`、`prices`、`plan`；`construction` 和 `vehicle-model` 只可用于 `spatial-3d`，角色分别为 `building`/`construction`/`assets` 和 `showcase`/`assets`。文件均须在作品内存在，不能越界。幕内 `content.sourceIds` 必须引用已声明的 ID，不能重复。准备验证来源材料与资产摘要，把数据与实现绑定到准备指纹，并要求来源画幅、帧率和时长与本幕一致。

当前只渲染这三种来源的场景绘制入口：采用后的本地 `../src/code-scene/sources` 提供 `FinancialSeriesScene`、`ConstructionScene`、`VehicleScene`；也可从同一本地模块的 `useSceneSource(id)` 取经验证数据自行绘制。普通分镜中的 `sources` 只是准备输入，不会自动在画面出现。
