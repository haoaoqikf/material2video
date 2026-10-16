# 配音与字幕

> **适用范围：** 本文描述当前所有类型的配音、字幕与混音契约：音色与语速的三级优先级、
> 语音缓存与失效、字幕断句规则、成片音轨参数，以及音床。
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
| `audio.segments` | 音轨分段：`sceneId`、相对路径、`startFrame`、`durationInFrames`、`sha256`。通用 v7 始终输出整片一条母版轨（`sceneId` 为 `master`），包含旁白、音效、音床或对应静音。`audio.cacheHits` 记本次命中数 |
| `subtitles` | 全片字幕 cue：`startFrame`、`endFrame`、`text` |

入口：

```bash
uv run m2v prepare --project videos/general/<slug>
uv run m2v validate --project videos/general/<slug>
uv run m2v preview --project videos/general/<slug>
uv run m2v review-template --project videos/general/<slug>
uv run m2v render --project videos/general/<slug>
```

## 工作流

1. 口播写在它所属的幕/场景里：通用 v8 用分段口播 `narrationSegments`（只接受分段形式，
   不接受整段字符串；代码幕可以为空）；静音镜头省略旁白。
2. `m2v prepare --project <目录>` 校验材料、合成配音、编译派生时间轴并写出准备记录。
   通用 v8 每段独立合成、按实际音频推导帧数、字幕与展示时间，并在每幕结束留 24 帧阅读时间；
   `code` 幕在这一步实时录制片段并按摘要缓存（见 [渲染契约](render-contract.md)）。
3. `m2v validate --project <目录>` 检查材料、准备记录、字幕和 WAV 时长。
4. `m2v preview --project <目录>` 生成完整预演（通用 v8 会先跑浏览器字幕量测）；
   `m2v general keyframes --storyboard <分镜>` 单独输出各幕结果帧供静态检查。
5. `m2v render --project <目录>` 在准备和完整预演均绑定当前材料并通过自动验收时输出正式视频；人工画面评审为可选工具。

通用 v8 在 `input.kind` 为 `article` 时，正式导出还要求源文已通过**讲解语义审查**：
`m2v general input-review --storyboard
<分镜>` 生成 `outputs/input-review.json`，填好后 status 为 `pass`、依据非空且 problemSpans
为空；源文或正文计数变化会让审查过期，须重新审查。计数只用于记录，不设字数区间。见
[讲解输入审查](input-review.md)。

渲染与预演都不会触发联网合成：没有跑过 `m2v prepare` 时它们直接报「缺少有效准备记录」
并停下，不会静默导出一段无声成片。要无声成片就不写口播、也不声明音床，prepare 会写出
空音轨（`audio.segments` 为空），此时 `m2v render` 照常产出无声画面。
成片与预演落在作品 `outputs/` 下（通用 v8 为 `outputs/video.mp4`，预演为
`outputs/previews/video.mp4`）。路径推导规则见 [目录约定与输出路径](paths-and-outputs.md)。

## 语音与字幕

使用 [edge-tts](https://github.com/rany2/edge-tts) 7.2.x（`>=7.2.8,<8`），音色必须明确选择，
语速默认 `+0%`；`m2v prepare` 的 `--voice` / `--rate` 可临时试听而不改作品文件。首次合成需要
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
作品的是同一份；见 [渲染契约](render-contract.md) 的字幕量测硬判定。不依赖外置字幕文件。
准备记录的 `props` 携带 `subtitleCues`，共享 composition 按当前帧绘制字幕并预留安全区；
**分镜不能手写该字段**——它由 prepare 从真实词边界派生，手写会和音轨各说各话。
渲染按帧 seek，不播放音频；先编码画面，再复制视频流合入 AAC 配音，无二次视频编码。
合成时配音统一转码为 **AAC-LC / 44.1kHz / 立体声 / 128k**：准备记录里的 WAV 是 24kHz
单声道，但 24kHz 单声道 AAC 会被 Windows 的 Media Foundation 拒绝（`0xc00d36c4`），
44.1kHz 立体声是各平台兼容性最好的组合。画面像素格式固定为 `yuv420p(tv, bt709)`，
原因与对应校验见 [渲染契约](render-contract.md) 的「码流兼容性」。
准备记录与音轨都经临时目录原子落盘，之后会把访问权限交回目标目录的继承规则，
原因见 [渲染契约](render-contract.md) 的「交付文件的访问权限」。
最终 MP4 检查视频解码帧数、实际尺寸、帧率、时长及音轨解码长度，时长容差 100ms。
`m2v preview --limit-frames N` 只渲前 N 帧，成片写入 `outputs/previews/`，不覆盖正式成片，
也不生成可绑定评审的预演记录。
支持本地音床混音；节拍音效（`soundtrack.effects`）当前不渲染，自动选曲未实现。

## 配音音色与语速

音色与语速属于**作品属性**，在 `project.json` 的 `tts` 对象里声明；有自身旁白时必须明确音色，无旁白可省略：

```json
{
  "tts": {"voice": "zh-CN-YunxiNeural", "rate": "-6%"}
}
```

音色按「命令行 > 作品配置」解析，不再回落默认晓晓；语速独立按「命令行 > 作品配置 > +0%」解析，只在共享 `engine/tts.py` 实现一次：

| 层 | 写法 | 说明 |
| --- | --- | --- |
| 命令行 | `m2v prepare --project <目录> --voice ... --rate=...` | 临时试听用，不改作品文件 |
| 作品 | `project.json` 的 `tts.voice` / `tts.rate` | 作品的正式选择 |
| 缺失 | 音色阻断、语速 `+0%` | 有旁白但未选音时提示由助手选择或 `--voice` 指定 |

- `voice` 必须是合成服务的音色名（形如 `zh-CN-XiaoxiaoNeural`）；`rate` 为 −50% 至 +50% 的有符号百分比。
- 用 `m2v voices` 看当前可用音色（可用 `--locale all`、`--json`）。这条命令需要联网，只读，不写文件。
  音色**是否真实存在**只在合成时才能确定：准备前不联网是既有约束，所以配置校验只查格式。
- 旧有声作品缺少 `tts.voice` 时需先选音；无旁白及仅音床作品不要求选音。
- 改音色或语速会让已有语音缓存失效并重新合成，这正是"换声音"应有的代价。

### 助手自动选择与溯源

制作助手阅读完整旁白，运行 `m2v voices --json` 查询当前候选（其他语言用 `--locale`），结合语言、受众、内容和服务的风格标签选择；查询失败明确报告，不虚构候选、不回落默认音色。CLI 不调用模型，只读取结果并合成。选定后自动继续制作，无需试听确认；标签与技术验收不等于听感自然。

助手在 `tts.voice` 之外保存可选记录，例如：

```json
{
  "tts": {
    "voice": "zh-CN-YunxiNeural",
    "selection": {
      "mode": "assistant",
      "rationale": "旁白讲解低成本试错与行动反馈，采用有活力的叙事表达。",
      "narrationSha256": "0000000000000000000000000000000000000000000000000000000000000000"
    }
  }
}
```

上面的零摘要仅示意字段，必须换为真实值：调用 `m2v.engine.tts.narration_digest(texts)`，对按播放顺序排列的非空自身旁白字符串数组，以保留中文、无额外空格的 JSON UTF-8 计算 SHA256。通用类型逐幕逐段收集 `text`（图片与视频幕的旁白段同样计入）。保留原文和分段边界，忽略空白段。

助手记录只接受 mode、非空 rationale 和 64 位小写 narrationSha256。旁白改变会阻断 prepare，要求重新判断并更新记录；画面变化不要求重选。手动选择只填 voice，无需 selection；手动修改作品音色时删除旧 selection。`--voice` 覆盖会标记 command-line 来源，并丢弃助手理由；仅覆盖语速不跳过旁白摘要检查。

`outputs/prepared.json` 与成片旁车的 `inputs.tts` 保存 JSON 字符串，包含实际 backend、voice、rate、source（assistant/project/command-line）、有效 selection 及作品级 speech。逐幕停顿参数保存在 `props.compiledScenes[].speech`，原始分镜摘要参与指纹；旧 `inputs.speech:<场景ID>` 不再生成。音色、语速、来源参与准备指纹，修改作品配置必须重新准备和完整预演。语音缓存仍按实际文本、音色、语速等键复用，不因为选择理由变化重复合成。

**换音色比调语速更能改变节奏。** 同一篇长稿、同一标点，量测句间停顿：

| 音色（−6%） | 停顿中位 | 最短 / 最长 | 停顿个数 |
| --- | --- | --- | --- |
| 晓晓 | 0.218s | 0.051 / 0.729 | 44 |
| 云扬 | 0.247s | 0.052 / 0.840 | 54 |
| 云健 | 0.306s | 0.050 / 0.736 | 38 |
| 云希 | 0.404s | 0.053 / 0.764 | 47 |

调语速只是把同一套停顿等比拉长（实测比例恒为 1.08），语流密度不变；换音色才会改变
停顿的中位长度与个数。选中音色后再微调语速。

## 停顿节奏（韵律整形）

停顿的长短由合成服务的标点规则决定，无法主动控制——这是"念稿感"最直接的一层。
声明 `tts.speech` 后，合成结果会按标点给停顿分类，再把每一类调到目标长度：

```json
{
  "tts": {
    "speech": {
      "headPad": 0.08,
      "pause": {"comma": 0.15, "period": 0.55, "paragraph": 0.70}
    }
  }
}
```

| 字段 | 含义 | 允许区间 |
| --- | --- | --- |
| `pause.comma` | `，、；：` 处的停顿；短句读要短，节奏才不拖 | 0.03–0.45s |
| `pause.period` | `。？！…` 处的停顿；句末要有明显留白 | 0.03–0.90s |
| `pause.paragraph` | 整段结尾的停顿 | 0.03–1.40s |
| `headPad` | 每段口播开头的静音长度；实测每段原本有约 0.18s 引子 | 0–0.80s |

要点：

- **起伏来自对比，不是来自"停顿更长"**。逗号 0.15s 对句号 0.55s 是约 3.7 倍的差距；
  把所有停顿都拉长只会更慢、更平。
- 整形只改**停顿长度**，不改音色、语速与词本身。音频与词边界同源重映射，
  字幕与时间轴自动跟随——不需要第二处补丁。
- 只对能同时确认「这是停顿」与「这是标点」的位置生效；对不上的位置原样保留。
- 缓存里保存的始终是**未整形**的原始合成，所以开关或调整韵律**不会**让语音缓存失效，
  也不必重新合成（但会改变准备记录，需重新 prepare）。
- 命令行可临时试听：`--pause-comma` / `--pause-period` / `--pause-paragraph` / `--head-pad`。
- 逐幕覆盖：幕里写 `"speech": {"pause": {"comma": 0.12}}`，
  未提到的字段跟随作品配置；通用 v8 把它写在幕上，旁白段本身只接受
  `id` 与 `text`。逐幕停顿会改变该幕语音时长，固定帧容量的作品要一并腾挪。`speech.rate` 当前不渲染，实际语速使用作品或命令行设置。
- 历史实测（7 段口播）：语音合计 74.5s → 70.5s，
  短句读压到 0.15s、句末留 0.55s、起段引子 0.18s → 0.08s。

## 口播合成与混音

通用 v8 逐段合成（`narrationSegments[].text`），统一使用上面解析出的音色与语速。
实际语音时长向上取整到帧，通用 v8 再留出 12 帧稳定阅读时间；缓存按文本、音色、语速与
媒体契约版本区分，音乐不进入语音请求缓存键。

通用 v8 拒绝 `narrationSegments[].speech`（分镜的旁白段只接受 `id` 与 `text`，逐幕节奏写在
幕的 `speech` 上）：整片的停顿节奏改用
作品级 `tts.speech`（见「停顿节奏」），它不写进分镜、也不改变分段结构；幕上的 `speech`
覆盖作品级停顿，声明保存在准备画面参数中；逐幕 `speech.rate` 当前不渲染。

旁白二遍 loudnorm 目标 −16 LUFS/−1 dBTP，静音保留。音乐默认 −24 dB，讲话时额外压低 10 dB，
攻击/恢复 80/250ms（重叠包络合并）。混音限制到 −2 dBFS 以留编码余量，AAC 编码后量测真峰值；
超过 −1 dBTP 时降低增益重新合成，最多三次，否则失败。增益修正不改变时间轴。

准备记录用 `inputs.sound`（声音配置）与 `inputs.audio:<场景>`（音轨摘要）绑定声音输入：
改音床素材或任一参数都会让准备记录过期，必须重新 prepare。素材与作品目录整体迁移时
相对关系须保留。

## 音床与音效（`soundtrack`）

通用类型（`general`）的 v7 分镜顶层 `soundtrack` 接受 `music` 与 `effects`：作品目录内本地相对路径的音床素材、增益、循环与淡入淡出，
以及按幕定位的音效（内置提示音或本地素材）。通用 v8 的媒体与音效细节见
[文章媒体与音效](article-media-and-sound.md)。

```json
{
  "soundtrack": {
    "music": {"sourceRef": "assets/bed.wav", "gainDb": -26, "loop": true, "fadeInMs": 3000, "fadeOutMs": 4000}
  }
}
```

`sourceRef` 相对**声明它的材料文件所在目录**解析（文章分镜、通用片计划文件），
不支持 URL、绝对路径、`..` 或反斜线，解析后不可越界；`gainDb` 为 −60 至 0；`loop` 默认
false；淡入淡出 0–60000ms，默认各 500ms。素材缺失或损坏让 prepare 失败，旧准备记录保持有效。

上面的 `assets/bed.wav` 就是示例目录里的那份 CC0 合成音床：它由同目录的
`examples/buffer-smoothing/assets/generate.py` 原创合成（无第三方采样、按 CC0 1.0 分发，
见同目录 `LICENSE.md`），8 秒长。音床素材与生成器属于作品内容、不入库；仓库里这一份是
刻意保留的可复用示例输入，可以照抄做法生成自己的音床。

- **音床素材必须能无缝循环**。混音用 `-stream_loop -1` 铺满全片，接缝不连续就会在每个循环点响一下。
  判据不是「首尾采样值接近」，而是「末采样到首采样的步进不超过素材内部的最大相邻步进」：
  频率取循环长度的整数分之一、漂移用相位调制，才能让循环点与信号内部同样平滑。
- 声明音床或音效后，音轨不再是逐幕轨，而是**整片一条母版轨**：先按全片帧边界拼出旁白，
  再按字幕讲话区间生成闪避包络与音床混合，并把音效按幕/段起点叠上去。口播保持清晰、
  音床在讲话时被压低。母版轨严格裁到全片时长，循环音床不会把成片拖长。
- 拼接按**全片帧边界**推进：每幕占它到下一幕起点为止的帧数，没有口播的幕补静音，
  闪避包络和字幕一样用全片时间。
  不能按口播时长首尾相接——那样人声会整体前移，音床在旁白结束处就断了。
- **音效按通用 v7 契约执行**：它按 `sceneId`（可选 `segmentId`）与 `offsetMs` 定位，
  起点必须落在全片时长内，使用幕或旁白段窗口与 offsetMs 定位。
  内置提示音为 `ding`、`ding-dong`、`click`、`transition`，由工具确定性合成。

