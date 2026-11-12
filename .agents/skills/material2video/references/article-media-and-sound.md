# 文章媒体与音效

设计样品及正式交付遵守[网页原生样品的 AI 边界](design-samples.md#ai-图片的边界)：生图仅作内部构思/参考，不能直接交付，也不能贴入网页加镜头运动代替核心实现。本页生成记录和素材导入说明不构成样品通过；真实照片、档案及外部模型等仍按各自用途与许可核验。

本页提供制作技术契约；创作从[研究与试制](stage-research.md)进入，先解决影响方向判断的关键未知，再按[正式设计](stage-design.md)组织全片预演。

统一 v9 的五类作品都使用自己的全画布 React 场景，图片与视频按准备阶段注入的媒体映射以素材 ID 取用，声音用内置提示音与本地音床混成一条母版轨。本文说明媒体来源边界、实测校验与混音规则；分镜字段见[分镜结构](storyboard-schema.md)，制作顺序见[制作流程](production-workflow.md)。

## 媒体进入作品的唯一路径

准备与渲染只读本地文件，不联网取素材。无论素材来自助手检索、公开媒体直链还是图库，进入作品的方式只有一条：

```powershell
uv run m2v author assets import --project videos/<类型>/<slug> --manifest <清单.json> [--base <清单里 localPath 的基准目录>]
```

清单为 `{"schemaVersion":1,"assets":[...]}`，1～300 项，每项：

| 字段 | 要求 |
|---|---|
| `id` | 1～80 位字母、数字、`_`、`-`，一批内唯一 |
| `kind` | `image` 或 `video` |
| `localPath` 或 `mediaUrl` | 二选一：作品内（或 `--base` 下）本地文件，或 HTTP(S) 媒体直链 |
| `sourceUrl` | 可选公开网页地址；不是从网页下载时省略 |
| `role`、`target` | 可选；`role: "other"` 表示二维媒体，`target` 关联镜头目标；缺省仍为颜色贴图与素材ID。 |
| `author`、`license` | 可选；未知时如实记为「未知」，不猜测 |

导入过程下载或复制到临时目录，JPEG／PNG／WEBP图片由Pillow验证结构并完整解码，视频用ffmpeg探测尺寸、时长并验证可解码；实测类型不符时失败。通过后按内容摘要落盘为 `assets/media/<sha256><后缀>`，最后把来源页、作者、许可、实测尺寸、时长与文件摘要写进 `assets/media-sources.json`。一批素材全部通过后才发布记录：任何一项失败都不会修改已有记录或留下半成品文件。同一文件可被多个 `id` 引用。

未知署名与未知许可必须明确记录为「未知」；不要为了填满字段而编造来源。

### 来源与采用依据字段

以下可选字段在候选清单和导入项中共用，导入后保存在 `media-sources.json`；缺省值为 `other`、`未知`、空描述和 `not-checked`。这些是制作元数据，当前不作为画面内容渲染。

| 字段 | 要求与作用 |
|---|---|
| `sourceType` | `official`（官网）、`official-account`、`archive`、`research`、`news`、`industry`、`open-library`、`stock`、`other` |
| `publisher` | 非空发布主体；与原作者 `author` 分开，未知如实记录 |
| `description` | 内容描述，帮助判断叙事相关性 |
| `usableSegment` | 仅视频可填 `{startSeconds, endSeconds}`，0 ≤ start < end ≤ 实测时长；仅作候选检查窗口，**当前不渲染、不自动裁切**，实际入出点仍由场景代码决定 |
| `usage.status` | `explicit-allowed`、`no-explicit-restriction`、`conditional`、`prohibited`、`not-checked` |
| `usage.evidenceUrl` | 无用户名密码的 HTTP(S) 依据页；通常为素材页或适用条款页 |
| `usage.checkedAt` | 实际检查日期，`YYYY-MM-DD` |
| `usage.note` | 本次用途、检查范围和结论，适用条件及额外依据地址可一并记入 |
| `usage.conditionsMet` | 仅 `conditional` 使用，必须是布尔值；声明本次用途下条件是否满足 |

前三种已检查状态必须同时有 `evidenceUrl`、`checkedAt` 与非空 `note`。`prohibited` 可以先记录禁止，无需为了阻断补完全部字段。缺省或 `not-checked` 不会被程序推断为已检查或已授权。未知许可和未核实只提示；明确禁止当前用途或条件未满足在 prepare、report、audit 中阻断采用；非法元数据明确失败。导入本身允许保留被禁止的候选以供留证，不表示可入片。

默认采用政策与实际来源检查步骤见[采用政策与署名](material-sourcing.md#5-采用政策与署名)。修改采用依据后重新 import 和 prepare；来源记录摘要和媒体摘要都参与准备失效判断。此规则针对画面图片／视频，不改变下文第三方音效、字体或地图专用要求。

导入后用 `m2v assets report` 交叉核对记录、场景引用与 `SOURCES.md` 素材表；候选片段或多张图片可用 `m2v assets contact-sheet` 抽帧拼表检查。两者只读、不联网，不替代本页的导入留证、prepare 检查与 `m2v assets audit`；操作步骤见[素材检索与台账](material-sourcing.md)。

视觉素材的选择、使用与替换复核统一见[视觉素材选择与使用](visual-material-selection.md)；本页保留素材导入、来源登记、一致性校验与声音契约。

## 素材一致性

分镜不再引用素材路径：作品用[本地素材包装](storyboard-schema.md#全画布代码场景code)以 `useMediaAsset('素材ID')` 字面量调用取用，内部读取注入映射并对缺失项报错，地址与实测信息由准备阶段
复核后注入。prepare 复核的是**全部**登记素材，不是「本幕用到的那几项」：

- 记录项指向 `assets/media/` 之外、文件缺失、摘要变化或实测尺寸/类型/时长与记录不符 → 准备失败；
- 没有登记过的文件不会出现在映射里，作品拿不到它的地址；
- 每个素材文件的摘要都进入准备输入，因此替换任何一个都会让准备、候选与评审过期。

## 素材比例

素材比例**不受画幅限制**：横图、方图、竖视频都可以进同一个作品，裁切、缩放与播放入点由作品
代码决定（`objectFit`、容器尺寸、播放头）。图库检索不按画布比例或横竖方向过滤，作品方向只作候选排序偏好，比例维度显式声明为不设限。

代码幕的片段不是导入素材，而是在检查或正式生成时从作品 `scenes/` 的 TSX 入口逐帧录制：录制页只挂载
**已登记媒体**与仓库字体，作品目录下的其他文件、导入记录与源文都不暴露；入口、依赖与运行
异常都会让准备失败；片段按内容摘要落在 `outputs/code-cache/`，与素材一样进入准备输入，因此
源码、`props`、画幅、字幕安全区、媒体映射或时间窗变化都会让准备、候选与评审过期。
详见[分镜结构](storyboard-schema.md)的代码场景一节。

## 可选图库检索

```powershell
uv run m2v author assets search --project <目录> [--provider pixabay] [--kind video|photo|both] [--query <关键词> ...] [--per-page 15]
```

按幕顺序检索：不传 `--query` 时读取每幕的 `keywords`（`input.kind` 为 `topic` 时必填），传了就按顺序覆盖。检索只输出候选清单（含尺寸、时长、来源页、作者、许可、`mediaUrl`、说明、`sourceType: "stock"`、发布主体及 `usage.status: "not-checked"`），不下载、不写作品材料；候选为空不是失败，助手可以改用其他公开媒体直链，再由 `import` 统一留证。图库照片候选 `kind: "photo"` 在导入清单中写为 `image`，导入用合法作品素材 ID；去掉候选尺寸等非清单字段，实测值由导入生成。默认且唯一启用的图库为 Pixabay，凭据只从环境变量 `M2V_PIXABAY_API_KEY` 读取；Pexels 固定停用，显式指定会提示改用 Pixabay，即使配置其密钥也不会自动启用。缺少凭据时直接失败并指出变量名，不会静默匿名请求。Pixabay 检索响应在作品 `outputs/gallery-cache/` 缓存 24 小时，缓存不含 Key。

候选优先方向跟随作品画幅（`height >= width` 取竖屏，否则横屏），其他方向仍保留，比例不设限；检索只用于挑候选，
不用于系统性批量下载。

## 声音

音效风格见创作前必读的[听觉灵感](visual-expression-inspiration.md#四音效风格12-种)，采用自选。音效、配乐与旁白可按需组合，也可无声；实际声明与用户明确要求须兑现，不要求固定声音职责、密度或角色表。以下维护字段、素材与混音技术约定，不规定声音模板。

### 无声作品

全部场景无旁白且未配置音乐、音效时，预览与正式成片均不含音频流；准备阶段的静音母版仅用于内部时间线，不混入无声交付。只要存在任意声音声明，仍使用下述混音与音轨验收。最终溯源以 `audio.mode: "none"` 标识无声，不在交付后手工改写成片。

顶层 `soundtrack` 可选，包含 `music` 与 `effects`：

```json
{
  "soundtrack": {
    "music": {"sourceRef": "assets/bed.wav", "gainDb": -24, "loop": true, "fadeInMs": 800, "fadeOutMs": 1200},
    "effects": [
      {"builtin": "ding-dong", "sceneId": "opening", "offsetMs": 0, "gainDb": -20},
      {"sourceRef": "assets/click.wav", "sceneId": "steps", "segmentId": "steps-1", "offsetMs": 200}
    ]
  }
}
```

可选的 `envelopes` 与 `silence` 为全片音乐、音效轨增加层级曲线和主动留静：

```json
{
  "soundtrack": {
    "music": {"sourceRef": "assets/bed.wav", "gainDb": -24, "loop": true},
    "effects": [{"builtin": "transition", "sceneId": "turn", "offsetFrames": 0}],
    "envelopes": [{"track": "music", "curve": "smooth", "keyframes": [
      {"frame": 0, "gainDb": 0}, {"frame": 240, "gainDb": -10}, {"frame": 480, "gainDb": 0}
    ]}],
    "silence": [{"startFrame": 720, "endFrame": 780, "fadeFrames": 12}]
  }
}
```

- `envelopes` 最多两条，`track` 每种只能出现一次，取 `music` 或 `effects`。每条须有 2～256 个严格递增的 `{frame, gainDb}` 关键帧；帧号按全片时间轴从 0 开始，增益为 −60～0 dB。相邻点按 `curve`（`linear` 或 `smooth`）在 dB 域插值，首尾之外保持端值；要恢复原层级，需显式补回目标 dB 关键帧。音乐包络需要 `music`，音效包络需要至少一项 `effects`。
- `silence` 最多 128 段，按全片帧升序且不得重叠；每段含 `{startFrame, endFrame, fadeFrames}`，淡化帧数至少为 1 且不超过窗口一半。窗口中部音乐和音效静音，进入和退出用平滑曲线淡化；旁白保持原样，因此这是声音设计层的留静，不是整条母版静音。窗口和关键帧越过实际成片长度会在准备时失败。
- 需要完全无声的窗口时，还须安排对应无旁白；仅声明 `silence` 不会关闭人声，不新增全声静音字段。全片无声沿上方无声作品约定执行。
- 帧号按实际项目帧率转换到 24 kHz 混音采样位置。静音优先于音乐与音效包络及旁白闪避；不存在包络或静音字段时沿用既有混音行为。母版响度与真峰值目标不变。

- `music`：`sourceRef` 为作品目录内本地音频，`gainDb` 为 −60～0 dB，`loop` 为布尔值（默认 false），`fadeInMs`/`fadeOutMs` 为 0～60000 整数毫秒（默认各 500ms）；音床在旁白区间自动压低。
- `effects`：最多 128 项，`builtin`、`sourceRef` 与 `assetId` 三选一。内置提示音为 `ding`、`ding-dong`、`click`、`transition`，由工具确定性地合成，不依赖外部资产许可；`sourceRef` 指向本地音频；常见动作音效优先使用下方统一音效库的 `assetId`。
- 定位：`sceneId` 必填且必须是分镜里的幕；可选 `segmentId` 指向该幕旁白段，给出时从该段开始帧计时，否则从幕开始帧计时；`offsetMs` 为 ±60000 的整数，`gainDb` 为 −60～0 dB；音效按幕或旁白段窗口与 `offsetMs` 定位，起点必须落在全片时长内，否则准备失败。
- `sourceRef` 相对**声明它的材料文件所在目录**解析，不支持 URL、绝对路径、`..` 或反斜线，解析后不可越界；素材缺失或损坏让 prepare 失败，旧准备记录保持有效。

上面的 `assets/bed.wav` 是作品自备本地音床的路径示例；仓库音效测试使用独立合成夹具，不依赖固定视频示例。作品音床与生成产物不入库。

- **需要连续循环时核对素材接缝**。只有 `music.loop: true` 才使用 `-stream_loop -1` 重复素材，未循环的素材不要求具备循环接缝；`loop` 不自动修补断点。连续音床的接缝可比较末采样到首采样的步进与素材内部相邻步进，不能仅看首尾值接近。故意断续、重复或故障声按声明的表达目标判断，交付峰值等技术要求仍须满足。
- 声明音床或音效后，音轨不再是逐幕轨，而是**整片一条母版轨**：先按全片帧边界拼出旁白，
  再按字幕讲话区间生成闪避包络与音床混合，并把音效按幕/段起点叠上去，口播保持清晰。
  拼接按**全片帧边界**推进——每幕占它到下一幕起点为止的帧数，没有口播的幕补静音，
  闪避包络和字幕一样用全片时间。不能按口播时长首尾相接：那样人声会整体前移，
  音床在旁白结束处就断了。母版轨严格裁到全片时长，循环音床不会把成片拖长。
- **音效混音验收口径**：每条音效按定位起点延迟叠入母版轨，与旁白、音床一起经
  `amix`、限幅和 `atrim` 严格裁到全片时长；起点越界、引用未知 `sceneId`/`segmentId`
  或 `builtin`/`sourceRef`/`assetId` 非三选一都在 prepare 阶段失败。音效增益默认 −18 dB。
  叠入音效后母版轨仍须通过同一响度与真峰值复核（旁白 −16 LUFS、成片 ≤ −1 dBTP），
  修正只改增益、不改变时间轴；音效素材摘要进入准备指纹，换素材或改参数都要重新 prepare。

包络增益在素材的 `gainDb` 之后叠加，随后还有旁白闪避。例如上例基础 −24 dB、包络 −10 dB 时，闪避前合计为 −34 dB；包络恢复为 0 dB 才回到基础层级，不能把基础 −24 dB 再写入包络当作恢复。

没有 `soundtrack` 时母版轨只做响度归一化；有音床或音效时按字幕讲话区间做闪避、混音并限幅。

稀疏事件音也遵守同一母版目标。源音轨门限响度为非有限值时保留静音并统一格式，避免将纯静音送入动态归一。动态归一后重新量测实际响度；偏低时只在实测真峰值余量内作有限线性增益，并为后续AAC保留0.5dB余量。这样保留事件间强弱、声像和数字静音，不添加持续音床补足响度；峰值余量不足时不强行追平目标，仍由当前成片QA指出差距。滤波器依据见[FFmpeg loudnorm](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)。

### 声音语义与事件化

声音角色、重复素材、密度与强弱变化都可按需使用，不要求预先固定角色、每个角色使用同一 `assetId` 或另建 `SOUND.md`。全片声音方向归 `DESIGN.md`，详细意图与配合归[场景设计](scene-design.md)，精确时间引用既有分镜，素材来源、许可、参数和摘要仍登记在声音台账。

需要同步的动作可共用幕内事件：场景查询 `eventFrames`，音效引用 `eventId`，prepare 输出 `outputs/events.json` 供核对。声音预告或延迟反馈可用已有 `offsetFrames`；独立氛围与情绪声音可按现有显式时间定位，不要求每个声音都对应可见动作。事件或声音位置变化后仍须重新 prepare。

时间偏移、`gainDb`、淡入淡出与不同素材是现有编排手段，不是固定创作顺序。允许稀疏、密集和重复，不以数量或复杂度判断质量；只核对实际目标、必要旁白可懂度与相应技术边界。

现有音效能力没有 effect 级音高参数。不要为了单次动作在混音链里临时加 pitch；确有需要时按合成配方的可选半音参数单独评估。

## 统一音效库

来源只有两类：**代码合成**与**第三方音频**。均先落盘到作品的 `assets/sound/<sha256>.wav`，来源登记在 `assets/sound-sources.json`，分镜用 ID 编排；渲染不联网、不随机挑音。音效目录不在画面服务器白名单内。

独立工程 v3 将恢复配方保存为作品的 `assets/sound-recipe.json`，在作品目录执行 `uv run python scripts/video.py setup`，由随作品携带的本地运行时生成并登记；`prepare` 继续校验本地来源。下列共享 `author sounds` 命令用于共享工程材料，不能将其生成器身份记录直接当作 v3 本地运行时记录，也不要手改生成器身份绕过核验。

```powershell
uv run m2v author sounds catalog
uv run m2v author sounds import --project <目录> --manifest <音效清单.json> [--base <本地文件基准目录>]
uv run m2v author sounds audit --project <目录>
```

`catalog` 输出名称、类别、描述、默认时长、循环能力及变体方式。当前有 `keyboard-key`、`keyboard-typing`、`mouse-click`、`switch`、`spark`、`electric-crackle`、`electric-hum`、`whoosh`、`impact-soft`、`impact-metal`、`success`、`warning`。这些是风格化合成拟音，不能标作真实录音；对真实材质要求高时选择第三方实录。

导入清单 `schemaVersion: 1`，`assets` 为1～300项，音效库总数最多300项。每项 `id` 为1～80位字母、数字、下划线或连字符；`synthesis`、`localPath`、`mediaUrl` 三选一：

```json
{
  "schemaVersion": 1,
  "assets": [
    {"id": "typing", "synthesis": {"name": "keyboard-typing", "seed": 42, "durationMs": 2000, "eventsMs": [100, 280, 500, 900, 1400]}},
    {"id": "spark", "synthesis": {"name": "spark", "seed": 17}},
    {"id": "recorded-key", "localPath": "recordings/key.wav", "sourceUrl": "https://example.org/sounds/key", "author": "原作者", "license": "CC0-1.0"}
  ]
}
```

上面的第三方条目是格式示意，须替换为实际文件和核验过的来源许可。`localPath` 相对清单目录或 `--base` 解析，允许从作品外导入；`mediaUrl` 仅接受 HTTP(S) 音频直链，不解析网页。第三方必须提供明确 `author`、`license` 和 HTTP(S) `sourceUrl`，未知值拒绝；不能将下载成功当作已获许可。当前没有第三方音效搜索 API，助手检索候选后填写清单。导入保留原文件摘要、来源和许可，将音频完整解码为PCM16、24kHz、立体声WAV；单文件输入最多256MiB，时长大于0且最多600秒。损坏／截断文件拒绝，一批全部通过才发布；失败不更新已有记录或已有文件。

合成配方记录生成器版本和规范化参数，输出按CC0-1.0使用。同版本、同配方可复现。参数：`name` 必填；`seed` 为0～4294967295整数，默认0；`durationMs` 为30～30000整数，默认取目录；`intensity` 为0.05～1，默认0.7；`rate` 为1～20，默认7，只影响自动连续打字的平均每秒击键数。`eventsMs` 仅用于连续打字，为1～600个严格递增且落在音效时长内的整数毫秒，显式提供时替代随机间隔。`seed` 影响随机瞬态、噪声、音色和打字间隔；电流嗡鸣及提示音不使用随机变体。声音由瞬态、噪声、共振和包络组合，长按键序列先合成一条音频，避免占用数百个播放事件。

分镜播放示例：

```json
{
  "soundtrack": {
    "effects": [
      {"assetId": "typing", "sceneId": "typing-scene", "offsetFrames": 12, "gainDb": -14},
      {"assetId": "spark", "sceneId": "spark-scene", "offsetFrames": 30, "trimStartMs": 10, "durationMs": 400, "fadeOutMs": 40, "pan": 0.7}
    ]
  }
}
```

播放字段也适用于内置音效和本地 `sourceRef`，全部实际渲染：

| 字段 | 约束与行为 |
|---|---|
| `offsetFrames` | −36000～36000整数，默认相对幕首、按作品实际fps解释；与 `offsetMs`、`segmentId` 互斥。使用 `eventId` 时相对该事件，偏移后起点须在所属幕内 |
| `eventId` | 可选，引用 `sceneId` 所属幕的事件；与 `segmentId`、`offsetMs` 互斥，帧偏移默认0。详见[幕内事件](storyboard-schema.md#幕内事件) |
| `trimStartMs` | 0～600000整数，默认0；必须小于素材时长 |
| `durationMs` | 1～600000整数，默认播放入点后的剩余素材；不循环时不得超过剩余时长 |
| `loop` | 布尔值，默认false；为true时必须显式给出 `durationMs`，重复入点之后的素材 |
| `fadeInMs` / `fadeOutMs` | 0～600000整数，默认0，均不得超过播放时长；在循环铺满之后应用 |
| `pan` | −1～1，左至右；显式设置时先折成单声道再等功率定位，省略时保留素材立体声 |

只有目录标作 `loopable` 的合成嗡鸣保证周期接缝；其他音效或第三方素材的循环接缝须另行检查，`loop: true` 不自动修补断点。准备离线复核**全部登记音效**的许可、参数、完整WAV及摘要，将来源文件和所有音频摘要纳入准备指纹；改素材、配方或事件后重新导入（需要时）并 `prepare`。旁白仍按单声道准备，混音及最终响度处理保留立体声，母版严格裁到全片长度；讲话时压低音床，音效音量由事件控制，不自动压低。

制作接入：必要声音意图引用已有设计与分镜；动作音按声明目标核对同步或偏移，独立氛围不套用动作同步要求；检查实际重复疲劳、必要旁白遮挡及对应波形起点、峰值、声道和尾部，连续循环时再检查接缝。自动信号验证（响度、真峰值、静音、起音、频谱、同步）是声音评审依据；结论限定在可量测范围，不要求播放或试听。可复现配方见[键盘与火花演练](../../../../examples/documentary-edit/american-science-milestones/assets/SOUND_EXERCISE.md)。

### 复用参考音轨（受控例外）

参考素材默认不进入成片。用户明确要求复用单条参考作品音频时，先执行：

```powershell
uv run m2v ref audio <参考目录> --project videos/<类型>/<slug> --user-authorized "<用户授权原文>"
```

命令按 `recipe.json` 复核参考目录，提取 PCM16 / 48 kHz / 源声道 WAV 到作品 `assets/audio/<名称>.wav`，并写同名 `.provenance.json`。`--json` 或人类输出给出作品实际 fps 的总帧数（`(samples × fps + sampleRate - 1) // sampleRate`）和可直接粘贴的 `soundtrack` 片段；留证中的 `framesAt60fps` 仍是60帧分析信息，不可直接当作30帧作品的编排帧数。目标已存在时默认拒绝，来源与摘要一致才复用，`--force` 才替换。

无旁白作品只有音床时，音床就是全片唯一音源：必须显式写 `gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`。全部幕使用 `cut` 时 `sum(durationFrames) = totalFrames`；使用 `fade`/`crossfade` 时另加 `transitionFrames` 之和。母版仍会重采样为 24 kHz、保留混音声道，经限幅/压缩/响度归一后交付 AAC 44.1 kHz，交付说明写「整条音频作为唯一音源，经母版响度规范」，不写「比特级原样」。

`--user-authorized` 必须带用户原文；provenance 记录来源、参考视频与提取音频摘要、许可状态与第三方音乐风险，不把用户授权表述为许可。参考视频画面仍不得进入成片；成片只保留一处片尾署名。

音轨复用与风格借鉴是两件事：`ref audio` 的授权只覆盖这一条音轨，不扩大为参考画面资产的使用授权。用户要求借鉴外观或表达时，按[参考分析与借鉴](reference-video-analysis.md)记录实际采用范围；参考画面仍不得直接进入成片。
