# 准备记录与字幕

> **适用范围：** 本文描述所有类型共用的准备记录与字幕契约：`outputs/prepared.json` 的字段、
> 准备/校验/预演/渲染工作流、语音缓存与失败处理、字幕断句与成片验收口径。
> 音色、语速与停顿节奏见[配音音色与节奏](voice-and-rhythm.md)。
> 文章叙事只记录正文计数，**不再限制 130～170 字，也不再限制 35～45 秒**；
> 有旁白时长结合实际口播与声明的留白派生，无旁白代码幕按 `durationFrames` 或 `targetSeconds` 分配帧窗组织；统一 v9 全片上限为 600 秒（总帧数不超过 `600 × fps`）。分镜与时间轴契约以
> [五类统一分镜 v9](storyboard-schema.md)、[文章媒体与音效](article-media-and-sound.md) 与
> [OpenSpec five-video-types](../../../../openspec/specs/five-video-types/spec.md) 为准。
> v4 的媒体清单、`stages` 时间轴与语义节拍已随旧子系统删除，本文不再描述。

## 准备记录（`outputs/prepared.json`）

配音与字幕不再有独立的媒体清单文件：`m2v prepare` 把配音、字幕与派生时间轴一起写进
作品 `outputs/prepared.json`（`contractVersion: 3`），渲染、预览与评审都从它取。

| 字段 | 含义 |
| --- | --- |
| `contractVersion` / `projectId` / `type` | 准备记录版本与归属 |
| `compositionId` | 该作品渲染用的 composition |
| `props` | 交给 composition 的完整材料（统一 v9 是 `compiledScenes` / `subtitleCues` / `durationInFrames` 等派生结果） |
| `width` / `height` / `fps` / `durationInFrames` | 画面参数与派生总时长 |
| `inputs` | 逐个输入的 sha256：作品材料、源文与图片、`tts` 记录、实现摘要、`renderer` 构建指纹、`audio:<场景>` 与声音配置；代码场景另记入口源码、可达依赖与录制片段摘要（`codeAssets`） |
| `materialFingerprint` / `preparedFingerprint` | 作品描述与整份准备记录的指纹 |
| `audio.segments` | 音轨分段：`sceneId`、相对路径、`startFrame`、`durationInFrames`、`sha256`。统一 v9 始终输出整片一条母版轨（`sceneId` 为 `master`），包含旁白、音效、音床或对应静音。`audio.cacheHits` 记本次命中数 |
| `subtitles` | 全片字幕 cue：`startFrame`、`endFrame`、`text` |

入口：

```bash
uv run m2v prepare --project videos/<type>/<slug>
uv run m2v validate --project videos/<type>/<slug>
# 可选局部片段检查：默认前十秒或显式短窗口，不能替代全片生成
uv run m2v preview --project videos/<type>/<slug>
uv run m2v review timeline --project videos/<type>/<slug>
uv run m2v render --project videos/<type>/<slug>
```

## 工作流

1. 口播写在它所属的幕/场景里：统一 v9 用分段口播 `narrationSegments`（只接受分段形式，
   不接受整段字符串；代码幕可以为空）；静音镜头省略旁白。
2. `m2v prepare --project <目录>` 校验材料、合成配音、编译派生时间轴并写出准备记录。
   统一 v9 有旁白段独立合成，按实际音频及声明的前后留白推导帧数与字幕；幕尾阅读停留由 `readingHoldFrames` 指定，默认 0.4 秒（30fps 为 12 帧），无旁白幕按 `durationFrames` 或剩余目标时长分配；
   `code` 幕只构建源码并记录依赖，片段在检查或正式生成时按需录制并缓存（见
   [代码场景运行契约](code-scene-runtime.md)）。
3. `m2v validate --project <目录>` 检查材料、准备记录、字幕和 WAV 时长。
4. `m2v preview --project <目录>` 生成局部检查片段（默认前十秒，支持显式短窗口），不得用接近全片的窗口代替正式生成；
   `m2v author keyframes --storyboard <分镜>` 原生采集代表关键帧供静态检查。
5. `m2v render --project <目录>` 使用当前有效准备生成完整技术候选，交付保持同一候选文件；制作完成还须按[审核策略](review-contract.md)完成适用独立评审，导出成功不等于视觉或整片通过。

统一 v9 在 `input.kind` 为 `article` 时，正式导出还要求源文已通过**讲解语义审查**：
`m2v author input-review --storyboard
<分镜>` 生成 `outputs/input-review.json`，填好后 status 为 `pass`、依据非空且 problemSpans
为空；源文或正文计数变化会让审查过期，须重新审查。计数只用于记录，不设字数区间。见
[讲解输入审查](stage-design.md)。

渲染与预演都不会触发联网合成：没有跑过 `m2v prepare` 时它们直接报「缺少有效准备记录」
并停下，不会静默导出一段无声成片。要无声成片就不写口播、也不声明音床，prepare 会写出
空音轨（`audio.segments` 为空），此时 `m2v render` 照常产出无声画面。
成片与预演落在作品 `outputs/` 下（统一 v9 为 `outputs/video.mp4`，预演为
`outputs/previews/video.mp4`）。路径推导规则见 [目录约定与输出路径](paths.md)。

## 语音与字幕

### 合成后端

`project.json` 的 `tts.backend` 选择后端，省略时为 `edge-tts`；`m2v prepare --backend` 可临时覆盖作品声明。

| 后端 | 音色格式 | 语速 | 网络 |
| --- | --- | --- | --- |
| `edge-tts`（默认） | `zh-CN-XiaoxiaoNeural` | `tts.rate` 有符号百分比 | 首次合成需要联网 |
| `kokoro`（本地） | `zf_027`（zf 女声、zm 男声） | `tts.rate` 映射为模型 `speed`，+20% → 1.2 | 恢复模型后离线 |
| `qwen3-tts`（本地克隆） | `clone_<slug>`（作品内音色档案） | `tts.rate` 映射为不变调变速，+20% → 1.2 | 恢复主模型、对齐模型与参考音色后离线 |

音色必须明确选择，语速默认 `+0%`；`--voice` / `--rate` 可临时生成参数候选而不改作品文件，不要求播放或收听候选。后端与音色格式不匹配时在合成前失败。

Kokoro 使用 `Kokoro-82M-v1.1-zh` 本地模型。模型、config 与所选音色按作品 `models/registry.json` 登记的大小和 SHA256 校验，通过 `python models/fetch.py --download --voice <音色>` 恢复；`models/files/` 不入库，`setup --download` 会按作品当前音色恢复，`validate` 与准备前检查缺失。模型缺失或摘要不符时失败并给出恢复命令，不自动联网。

Kokoro 每次合成按文本、音色、语速派生固定随机种子，同版本环境下重复合成的音频逐位一致。时间戳来自模型时长预测与中文前端 token；数字会被改写、拉丁文本没有词 token，当前会明确失败，请把旁白写成纯中文口语或改用 `edge-tts`。完整参数选择见[配音音色与节奏](voice-and-rhythm.md)。

Qwen3-TTS 使用 `Qwen3-TTS-12Hz-0.6B-Base` 做零样本克隆，参考音频、参考文本、语言、来源与用户授权登记在作品 `models/qwen3-tts/registry.json` 的 `voices` 数组；主模型、speech tokenizer 与 stable-ts 使用的 `Systran/faster-whisper-small` 对齐模型同样按大小与 SHA256 校验，通过 `python models/qwen3-tts/fetch.py --download --voice <音色>` 恢复。参考音色是作品资产，不能从模型仓库恢复；更换参考音频或参考文本会改变语音缓存键。Qwen3-TTS 不返回词级时间戳，合成后在变速后的最终音频上用 stable-ts 按旁白原文强制对齐；零时长 token 只做文本保序合并，不按字符比例估算。数字与拉丁字母当前同样明确失败。

### 双语字幕与自适应柔光

分镜旁白可选带 `translation`。prepare 按与中文相同的标点规则把英文翻译拆成与中文 cue 相同数量的片段，写入 `props.subtitleCues[].secondary`；缺少翻译时不显示英文，存在翻译但条数不符时失败并指出段 ID。英文只作次行，阅读速度仍按中文计算。

`frames.json` 的 subtitle 可声明 `fontFamily`、`secondary`（字体、字号、行高、颜色、透明度）与 `backing`（`adaptiveHalo`、颜色、最大透明度、羽化半径）。启用 `adaptiveHalo` 时，prepare 按每条字幕中点从该幕登记素材采样字幕区域的平均色与亮度，写入 `backing.color/opacity/background`；渲染只画无硬边的径向柔光，不画矩形底板。采样值参与准备指纹；同一素材与时间点结果一致。旧作品没有这些字段时继续使用底板路径。

使用外部字体时，字体必须在作品 `fonts/registry.json` 登记来源、版本、摘要与许可，并由 `fonts/fetch.py` 恢复；字体缺失或摘要不符时构建/准备失败。片尾只显示画面来源平台（如“画面素材来自 Pixabay”），作者、许可与作品说明保留在 `assets/media-sources.json`、`SOURCES.md` 与发布说明，不进入画面。

### 时间戳、字幕与缓存

每个口播单元必须由合成结果提供真实词边界：edge-tts 使用 WordBoundary 事件（100ns 时间单位），Kokoro 使用 `pred_dur` 与实际 token，Qwen3-TTS 使用 stable-ts 对最终音频与旁白原文的强制对齐；三者在从原文恢复标点后按句断开，不按字符比例估算。长句仅在真实词边界拆分，每条最多 28 字符。不支持逐字高亮、导入录音或段级语速与停顿。音频损坏、时间戳缺失/倒退/越界、时间戳文字未覆盖原文时失败，不猜测字幕时长。

语音缓存键包含实际后端。edge-tts 键保持原有字段，不因新增后端重新合成；Kokoro 键加入模型 revision、Kokoro/misaki/torch 版本与种子策略；Qwen3-TTS 键加入模型 revision、对齐模型 revision、qwen-tts/transformers/torch/stable-ts 版本、参考音色档案摘要与种子策略。切换后端、参考音频或参考文本不会命中旧缓存。缓存保存未整形的原始合成，整形参数变化不重新合成。

字幕时间以视频开头为零点，采用开始包含、结束不包含的区间。音频统一解码为 24000Hz、
单声道、16bit PCM WAV，再按派生时间轴补静音并拼接；拼接位置按**累计帧数**换算采样位置，
避免逐幕取整误差累积——逐幕各自取整会让音轨比画面短出若干帧，而校验只差一点就报错。

统一 v9 的每段口播独立合成、独立推导时间，因此段与段之间不存在共享的词边界；
不再有「按原文顺序消费词边界、段末标点落到下一段」这类跨段约定。

字幕使用准备记录中的同一几何与样式；量测、代码场景与合成都读取它，不在配色令牌另存一套边界。横竖屏按实际画幅与手机显示复核字号、换行和停留，参考实现的固定值不等于所有作品的美术目标，也不宣称已符合任一外部字幕规范。

### 作品级字幕字号

五类独立作品均可在 `project.json` 的 `output.subtitle` 声明共享旁白字幕字号，示例：

```json
{
  "output": {
    "subtitle": {"fontSize": 52}
  }
}
```

`subtitle` 必须且只能包含 `fontSize`，取24至56的整数；空对象、未知子字段、布尔、浮点、字符串、null 和范围外数值均拒绝。该字段为 null 同样拒绝。该字段不属于分镜，不能设置字幕开关、安全区、颜色或行高。

省略时完整沿用作品 `src/frames.json` 所选画幅的默认样式（主项目参考为 `web/src/frames.json`），当前横竖屏均为40px。prepare 仅覆盖字号，把解析后的同一完整样式写入 `props.subtitle` 与序列化的 `inputs.subtitle`；预演、正式合成、代码片段配置、布局量测和字幕 QA 使用该准备样式。修改、添加或移除字号配置会让旧准备及候选失效，须重新 prepare，不要手改 `outputs/prepared.json`。

增大字号不扩大安全区，也不自动缩字；须按手机尺寸复核字幕，换行溢出时精简字幕文本。字号示例不是所有作品统一的视觉要求。

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

字幕由共享层绘制并烧录在成片里，安全区取自作品画幅配置（`src/frames.json`），与本地场景接收的
作品的是同一份；见 [渲染引擎](render-engine.md) 的字幕量测硬判定。不依赖外置字幕文件。
准备记录的 `props` 携带 `subtitleCues`，共享 composition 按当前帧绘制字幕并预留安全区；
**分镜不能手写该字段**——它由 prepare 从真实词边界派生，手写会和音轨各说各话。
渲染按帧 seek，不播放音频；有声作品先编码画面，再复制视频流合入 AAC 母版，无二次视频编码。无声作品的静音准备母版仅供内部时间线，正式成片不含音频流，见[无声作品](article-media-and-sound.md#无声作品)。
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
