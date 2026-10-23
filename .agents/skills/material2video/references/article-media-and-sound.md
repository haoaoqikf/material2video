# 文章媒体与音效

本页配合[节奏、美术、声音与制作阶段](creative-production.md)执行：先整片粗预演、风险优先，再按阶段完成条件精制与复查；不增加用户确认或 CLI 人工门禁。

通用 v8 把「文章讲解」和「在线素材剪辑」合并到一个入口：画面是作品自己的全画布 React 场景，图片与视频经 `useMediaAsset` 按素材 ID 取用，声音用内置提示音与本地音床混成一条母版轨。本文说明媒体来源边界、实测校验与混音规则；分镜字段见[分镜结构](storyboard-schema.md)，制作顺序见[制作流程](production-workflow.md)。

## 媒体进入作品的唯一路径

准备与渲染只读本地文件，不联网取素材。无论素材来自助手检索、公开媒体直链还是图库，进入作品的方式只有一条：

```powershell
uv run m2v general assets import --project videos/general/<slug> --manifest <清单.json> [--base <清单里 localPath 的基准目录>]
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

导入过程下载或复制到临时目录，用 ffmpeg 实测真实类型、像素尺寸与视频时长并验证首帧可解码，再按内容摘要落盘为 `assets/media/<sha256><后缀>`，最后把来源页、作者、许可、实测尺寸、时长与文件摘要写进 `assets/media-sources.json`。一批素材全部通过后才发布记录：任何一项失败都不会修改已有记录或留下半成品文件。同一文件可被多个 `id` 引用。

未知署名与未知许可必须明确记录为「未知」；不要为了填满字段而编造来源。

## 素材一致性

分镜不再引用素材路径：作品代码用 `useMediaAsset(id)` 按素材 ID 取用，地址与实测信息由准备阶段
复核后注入。prepare 复核的是**全部**登记素材，不是「本幕用到的那几项」：

- 记录项指向 `assets/media/` 之外、文件缺失、摘要变化或实测尺寸/类型/时长与记录不符 → 准备失败；
- 没有登记过的文件不会出现在映射里，作品拿不到它的地址；
- 每个素材文件的摘要都进入准备输入，因此替换任何一个都会让准备、候选与评审过期。

## 素材比例

素材比例**不受画幅限制**：横图、方图、竖视频都可以进同一个作品，裁切、缩放与播放入点由作品
代码决定（`objectFit`、容器尺寸、播放头）。图库检索也不再按画布比例过滤候选，只按作品方向
（横屏或竖屏）约束，比例维度显式声明为不设限。

代码幕的片段不是导入素材，而是在检查或正式生成时从作品 `scenes/` 的 TSX 入口逐帧录制：录制页只挂载
**已登记媒体**与仓库字体，作品目录下的其他文件、导入记录与源文都不暴露；入口、依赖与运行
异常都会让准备失败；片段按内容摘要落在 `outputs/code-cache/`，与素材一样进入准备输入，因此
源码、`props`、画幅、字幕安全区、媒体映射或时间窗变化都会让准备、候选与评审过期。
详见[分镜结构](storyboard-schema.md)的代码场景一节。

## 可选图库检索

```powershell
uv run m2v general assets search --project <目录> [--provider pixabay] [--kind video|photo|both] [--query <关键词> ...] [--per-page 15]
```

按幕顺序检索：不传 `--query` 时读取每幕的 `keywords`（`input.kind` 为 `topic` 时必填），传了就按顺序覆盖。检索只输出候选清单（含尺寸、时长、来源页、作者、许可与说明），不下载、不写作品文件；候选为空不是失败，助手可以改用其他公开媒体直链，再由 `import` 统一留证。默认且唯一启用的图库为 Pixabay，凭据只从环境变量 `M2V_PIXABAY_API_KEY` 读取；Pexels 固定停用，显式指定会提示改用 Pixabay，即使配置其密钥也不会自动启用。缺少凭据时直接失败并指出变量名，不会静默匿名请求。Pixabay 检索响应在作品 `outputs/gallery-cache/` 缓存 24 小时，缓存不含 Key。

检索方向跟随作品画幅（`height >= width` 取竖屏，否则横屏），比例不设限；检索只用于挑候选，
不用于系统性批量下载。

## 声音

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

- `music`：`sourceRef` 为作品目录内本地音频，`gainDb` 为 −60～0 dB，`loop` 为布尔值（默认 false），`fadeInMs`/`fadeOutMs` 为 0～60000 整数毫秒（默认各 500ms）；音床在旁白区间自动压低。
- `effects`：最多 128 项，`builtin` 与 `sourceRef` 二选一。内置提示音为 `ding`、`ding-dong`、`click`、`transition`，由工具确定性地合成，不依赖外部资产许可；`sourceRef` 指向本地音频。
- 定位：`sceneId` 必填且必须是分镜里的幕；可选 `segmentId` 指向该幕旁白段，给出时从该段开始帧计时，否则从幕开始帧计时；`offsetMs` 为 ±60000 的整数，`gainDb` 为 −60～0 dB；音效按幕或旁白段窗口与 `offsetMs` 定位，起点必须落在全片时长内，否则准备失败。
- `sourceRef` 相对**声明它的材料文件所在目录**解析，不支持 URL、绝对路径、`..` 或反斜线，解析后不可越界；素材缺失或损坏让 prepare 失败，旧准备记录保持有效。

上面的 `assets/bed.wav` 是作品自备本地音床的路径示例；仓库音效测试使用独立合成夹具，不依赖固定视频示例。作品音床与生成产物不入库。

- **音床素材必须能无缝循环**。混音用 `-stream_loop -1` 铺满全片，接缝不连续就会在每个循环点响一下。
  判据不是「首尾采样值接近」，而是「末采样到首采样的步进不超过素材内部的最大相邻步进」：
  频率取循环长度的整数分之一、漂移用相位调制，才能让循环点与信号内部同样平滑。
- 声明音床或音效后，音轨不再是逐幕轨，而是**整片一条母版轨**：先按全片帧边界拼出旁白，
  再按字幕讲话区间生成闪避包络与音床混合，并把音效按幕/段起点叠上去，口播保持清晰。
  拼接按**全片帧边界**推进——每幕占它到下一幕起点为止的帧数，没有口播的幕补静音，
  闪避包络和字幕一样用全片时间。不能按口播时长首尾相接：那样人声会整体前移，
  音床在旁白结束处就断了。母版轨严格裁到全片时长，循环音床不会把成片拖长。
- **音效混音验收口径**：每条音效按定位起点延迟叠入母版轨，与旁白、音床一起经
  `amix`、限幅和 `atrim` 严格裁到全片时长；起点越界、引用未知 `sceneId`/`segmentId`
  或 `builtin`/`sourceRef` 同缺同给都在 prepare 阶段失败。音效增益默认 −18 dB。
  叠入音效后母版轨仍须通过同一响度与真峰值复核（旁白 −16 LUFS、成片 ≤ −1 dBTP），
  修正只改增益、不改变时间轴；音效素材摘要进入准备指纹，换素材或改参数都要重新 prepare。

没有 `soundtrack` 时母版轨只做响度归一化；有音床或音效时按字幕讲话区间做闪避、混音并限幅。

### 复用参考音轨（受控例外）

参考素材默认不进入成片。用户明确要求复用单条参考作品音频时，先执行：

```powershell
uv run m2v ref audio <参考目录> --project videos/general/<slug> --user-authorized "<用户授权原文>"
```

命令按 `recipe.json` 复核参考目录，提取 PCM16 / 48 kHz / 源声道 WAV 到作品 `assets/audio/<名称>.wav`，并写同名 `.provenance.json`。`--json` 或人类输出给出作品实际 fps 的总帧数（`(samples × fps + sampleRate - 1) // sampleRate`）和可直接粘贴的 `soundtrack` 片段；留证中的 `framesAt60fps` 仍是60帧分析信息，不可直接当作30帧作品的编排帧数。目标已存在时默认拒绝，来源与摘要一致才复用，`--force` 才替换。

无旁白作品只有音床时，音床就是全片唯一音源：必须显式写 `gainDb: 0`、`loop: false`、`fadeInMs: 0`、`fadeOutMs: 0`。全部幕使用 `cut` 时 `sum(durationFrames) = totalFrames`；使用 `fade`/`crossfade` 时另加 `transitionFrames` 之和。母版仍会重采样为 24 kHz 单声道、经限幅/压缩/响度归一后交付 AAC 44.1 kHz，交付说明写「整条音频作为唯一音源，经母版响度规范」，不写「比特级原样」。

`--user-authorized` 必须带用户原文；provenance 记录来源、参考视频与提取音频摘要、许可状态与第三方音乐风险，不把用户授权表述为许可。参考视频画面仍不得进入成片；成片只保留一处片尾署名。

音轨复用与风格借鉴是两件事：`ref audio` 的授权只覆盖这一条音轨，不等于可以复制参考画面或沿用其视觉风格。用户要求借鉴画面风格时，另按[参考风格契约](reference-style.md)执行；参考画面仍不得进入成片。
