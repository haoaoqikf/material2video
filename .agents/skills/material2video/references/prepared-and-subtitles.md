# 准备记录与字幕

> **适用范围：** 本文描述所有类型共用的准备记录与字幕契约：`outputs/prepared.json` 的字段、
> 准备/校验/预演/渲染工作流、语音缓存与失败处理、字幕断句与成片验收口径。
> 音色、语速与停顿节奏见[配音音色与节奏](voice-and-rhythm.md)。
> 文章叙事只记录正文计数，**不再限制 130～170 字，也不再限制 35～45 秒**；
> 成片时长由实际口播派生（通用 v8 上限 36000 帧）。分镜与时间轴契约以
> [通用分镜 v8](storyboard-schema.md)、[文章媒体与音效](article-media-and-sound.md) 与
> [OpenSpec article-explainer](../../../../openspec/specs/article-explainer/spec.md) 为准。
> v4 的媒体清单、`stages` 时间轴与语义节拍已随旧子系统删除，本文不再描述。

## 准备记录（`outputs/prepared.json`）

配音与字幕不再有独立的媒体清单文件：`m2v prepare` 把配音、字幕与派生时间轴一起写进
作品 `outputs/prepared.json`（`contractVersion: 1`），渲染、预览与评审都从它取。

| 字段 | 含义 |
| --- | --- |
| `contractVersion` / `projectId` / `type` | 准备记录版本与归属 |
| `compositionId` | 该作品渲染用的 composition |
| `props` | 交给 composition 的完整材料（通用 v8 是 `compiledScenes` / `subtitleCues` / `durationInFrames` 等派生结果） |
| `width` / `height` / `fps` / `durationInFrames` | 画面参数与派生总时长 |
| `inputs` | 逐个输入的 sha256：作品材料、源文与图片、`tts` 记录、实现摘要、`renderer` 构建指纹、`audio:<场景>` 与声音配置；代码场景另记入口源码、可达依赖与录制片段摘要（`codeAssets`） |
| `materialFingerprint` / `preparedFingerprint` | 作品描述与整份准备记录的指纹 |
| `audio.segments` | 音轨分段：`sceneId`、相对路径、`startFrame`、`durationInFrames`、`sha256`。通用 v8 始终输出整片一条母版轨（`sceneId` 为 `master`），包含旁白、音效、音床或对应静音。`audio.cacheHits` 记本次命中数 |
| `subtitles` | 全片字幕 cue：`startFrame`、`endFrame`、`text` |

入口：

```bash
uv run m2v prepare --project videos/general/<slug>
uv run m2v validate --project videos/general/<slug>
# 可选局部片段检查：默认前十秒或显式短窗口，不能替代全片生成
uv run m2v preview --project videos/general/<slug>
uv run m2v review-template --project videos/general/<slug>
uv run m2v render --project videos/general/<slug>
```

## 工作流

1. 口播写在它所属的幕/场景里：通用 v8 用分段口播 `narrationSegments`（只接受分段形式，
   不接受整段字符串；代码幕可以为空）；静音镜头省略旁白。
2. `m2v prepare --project <目录>` 校验材料、合成配音、编译派生时间轴并写出准备记录。
   通用 v8 每段独立合成、按实际音频推导帧数、字幕与展示时间，并在每幕结束留 24 帧阅读时间；
   `code` 幕只构建源码并记录依赖，片段在检查或正式生成时按需录制并缓存（见
   [代码场景运行契约](code-scene-runtime.md)）。
3. `m2v validate --project <目录>` 检查材料、准备记录、字幕和 WAV 时长。
4. `m2v preview --project <目录>` 生成局部检查片段（默认前十秒，支持显式短窗口），不得用接近全片的窗口代替正式生成；
   `m2v general keyframes --storyboard <分镜>` 原生采集代表关键帧供静态检查。
5. `m2v render --project <目录>` 在当前准备有效时只生成一次完整候选，自动验收后复制交付同一文件；人工画面评审为可选工具。

通用 v8 在 `input.kind` 为 `article` 时，正式导出还要求源文已通过**讲解语义审查**：
`m2v general input-review --storyboard
<分镜>` 生成 `outputs/input-review.json`，填好后 status 为 `pass`、依据非空且 problemSpans
为空；源文或正文计数变化会让审查过期，须重新审查。计数只用于记录，不设字数区间。见
[讲解输入审查](input-review.md)。

渲染与预演都不会触发联网合成：没有跑过 `m2v prepare` 时它们直接报「缺少有效准备记录」
并停下，不会静默导出一段无声成片。要无声成片就不写口播、也不声明音床，prepare 会写出
空音轨（`audio.segments` 为空），此时 `m2v render` 照常产出无声画面。
成片与预演落在作品 `outputs/` 下（通用 v8 为 `outputs/video.mp4`，预演为
`outputs/previews/video.mp4`）。路径推导规则见 [目录约定与输出路径](paths.md)。

## 语音与字幕

使用 [edge-tts](https://github.com/rany2/edge-tts) 7.2.x（`>=7.2.8,<8`），音色必须明确选择，
语速默认 `+0%`；`m2v prepare` 的 `--voice` / `--rate` 可临时生成参数候选而不改作品文件，不要求播放或收听候选。首次合成需要
联网；服务可能变化，缓存音频可离线复用，不承诺再次强制生成时波形完全相同。

每个口播单元采用 WordBoundary 事件，将 100ns 时间单位转换为秒，从原文恢复标点后按句断开。
长句仅在真实词边界拆分，每条最多 28 字符。不支持逐字高亮、导入录音或段级语速与停顿。
音频损坏、时间戳缺失/倒退/越界、时间戳文字未覆盖原文时失败，不猜测字幕时长。
如果服务把数字或缩写改写成读音导致文字不匹配，请把 `narrationSegments[].text` 写成明确的
口语文本。

字幕时间以视频开头为零点，采用开始包含、结束不包含的区间。音频统一解码为 24000Hz、
单声道、16bit PCM WAV，再按派生时间轴补静音并拼接；拼接位置按**累计帧数**换算采样位置，
避免逐幕取整误差累积——逐幕各自取整会让音轨比画面短出若干帧，而校验只差一点就报错。

通用 v8 的每段口播独立合成、独立推导时间，因此段与段之间不存在共享的词边界；
不再有「按原文顺序消费词边界、段末标点落到下一段」这类跨段约定。

## 缓存与失败处理

作品 `outputs/audio-cache/` 保存按文本、音色、语速、媒体契约版本、生成器版本与 edge-tts
版本计算键的 WAV 和字词时间戳 JSON。缓存校验包括音频长度、SHA-256 与时间戳；损坏时重新
合成该幕。未改变的幕复用缓存——改画面文案或幕时长不会重新请求同一段口播。

连接超时 10 秒、接收超时 30 秒、单个口播单元请求总超时 90 秒；网络失败最多重试两次，
间隔 1 秒、2 秒。无效参数不重试。日志包含幕标识、缓存命中与失败原因。

准备过程在输出目录内写临时文件，最后原子替换 `outputs/prepared.json`；失败保留上次可用的
准备记录。旧音轨为避免破坏已打开的预览不自动删除；不再使用后可清理整个输出目录。
音轨路径相对作品根解析：越界或摘要不符直接报错，不跨作品合成。
请把产物放在已忽略的 `outputs/`，生成媒体与缓存均不提交 Git。

## 渲染与验收

字幕由共享层绘制并烧录在成片里，安全区取自画幅配置（`web/src/frames.json`），与 SDK 交给
作品的是同一份；见 [渲染引擎](render-engine.md) 的字幕量测硬判定。不依赖外置字幕文件。
准备记录的 `props` 携带 `subtitleCues`，共享 composition 按当前帧绘制字幕并预留安全区；
**分镜不能手写该字段**——它由 prepare 从真实词边界派生，手写会和音轨各说各话。
渲染按帧 seek，不播放音频；先编码画面，再复制视频流合入 AAC 配音，无二次视频编码。
合成时配音统一转码为 **AAC-LC / 44.1kHz / 立体声 / 128k**：准备记录里的 WAV 是 24kHz
单声道，但 24kHz 单声道 AAC 会被 Windows 的 Media Foundation 拒绝（`0xc00d36c4`），
44.1kHz 立体声是各平台兼容性最好的组合。画面像素格式固定为 `yuv420p(tv, bt709)`，
原因与对应校验见 [渲染引擎](render-engine.md) 的「码流兼容性」。
准备记录与音轨都经临时目录原子落盘，之后会把访问权限交回目标目录的继承规则，
原因见[交付权限](delivery-and-provenance.md#交付权限)。
最终 MP4 检查视频解码帧数、实际尺寸、帧率、时长及音轨解码长度，时长容差 100ms。
`m2v preview --limit-frames N` 只渲前 N 帧，成片写入 `outputs/previews/`，不覆盖正式成片，
也不生成可绑定评审的预演记录。
支持本地音床与节拍音效（`soundtrack.effects`）混音：两者都已进入母版音轨，详见
[文章媒体与音效](article-media-and-sound.md#声音)；自动选曲未实现。
