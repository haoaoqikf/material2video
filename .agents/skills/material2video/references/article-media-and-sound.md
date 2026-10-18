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
| `author`、`license` | 可选；未知时如实记为「未知」，不猜测 |

导入过程下载或复制到临时目录，用 ffmpeg 实测真实类型、像素尺寸与视频时长并验证首帧可解码，再按内容摘要落盘为 `assets/media/<sha256><后缀>`，最后把来源页、作者、许可、实测尺寸、时长与文件摘要写进 `assets/media-sources.json`。一批素材全部通过后才发布记录：任何一项失败都不会修改已有记录或留下半成品文件。同一文件可被多个 `id` 引用。

未知署名与未知许可必须明确记录为「未知」；不要为了填满字段而编造来源。

## 素材一致性

分镜不再引用素材路径：作品代码用 `useMediaAsset(id)` 按素材 ID 取用，地址与实测信息由准备阶段
复核后注入。prepare 复核的是**全部**登记素材，不是「本幕用到的那几项」：

- 记录项指向 `assets/media/` 之外、文件缺失、摘要变化或实测尺寸/类型/时长与记录不符 → 准备失败；
- 没有登记过的文件不会出现在映射里，作品拿不到它的地址；
- 每个素材文件的摘要都进入准备输入，因此替换任何一个都会让准备、完整预演与评审过期。

## 素材比例

素材比例**不受画幅限制**：横图、方图、竖视频都可以进同一个作品，裁切、缩放与播放入点由作品
代码决定（`objectFit`、容器尺寸、播放头）。图库检索也不再按画布比例过滤候选，只按作品方向
（横屏或竖屏）约束，比例维度显式声明为不设限。

代码幕的片段不是导入素材，而是准备阶段从作品 `scenes/` 的 TSX 入口逐帧录制：录制页只挂载
**已登记媒体**与仓库字体，作品目录下的其他文件、导入记录与源文都不暴露；入口、依赖与运行
异常都会让准备失败；片段按内容摘要落在 `outputs/code-cache/`，与素材一样进入准备输入，因此
源码、`props`、画幅、字幕安全区、媒体映射或时间窗变化都会让准备、完整预演与评审过期。
详见[分镜结构](storyboard-schema.md)的代码场景一节。

## 可选图库检索

```powershell
uv run m2v general assets search --project <目录> [--provider pexels|pixabay] [--kind video|photo|both] [--query <关键词> ...] [--per-page 15]
```

按幕顺序检索：不传 `--query` 时读取每幕的 `keywords`（`input.kind` 为 `topic` 时必填），传了就按顺序覆盖。检索只输出候选清单（含尺寸、时长、来源页、作者、许可与说明），不下载、不写作品文件；候选为空不是失败，助手可以改用其他公开媒体直链，再由 `import` 统一留证。凭据只从环境变量读取：Pexels 为 `M2V_PEXELS_API_KEY`，Pixabay 为 `M2V_PIXABAY_API_KEY`；缺少凭据时直接失败并指出变量名，不会静默匿名请求。Pixabay 检索响应在作品 `outputs/gallery-cache/` 缓存 24 小时，缓存不含 Key。

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

- `music`：`sourceRef` 为作品目录内本地音频，`gainDb` 为 −60～0 dB，`loop` 为布尔值，`fadeInMs`/`fadeOutMs` 为 0～60000 整数毫秒；音床在旁白区间自动压低。
- `effects`：最多 128 项，`builtin` 与 `sourceRef` 二选一。内置提示音为 `ding`、`ding-dong`、`click`、`transition`，由工具确定性地合成，不依赖外部资产许可；`sourceRef` 指向本地音频。
- 定位：`sceneId` 必填且必须是分镜里的幕；可选 `segmentId` 指向该幕旁白段，给出时从该段开始帧计时，否则从幕开始帧计时；`offsetMs` 为 ±60000 的整数，`gainDb` 为 −60～0 dB。
- 起点必须落在全片时长内，否则准备失败；母版轨严格裁到全片时长，循环音床不会把成片拖长。

没有 `soundtrack` 时母版轨只做响度归一化；有音床或音效时按字幕讲话区间做闪避、混音并限幅。
