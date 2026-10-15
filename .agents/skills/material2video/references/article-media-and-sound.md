# 文章媒体与音效

文章 v6 把「文章讲解」和「在线素材剪辑」合并到一个入口：同一份分镜既能写受控图文幕，也能放图片与视频镜头，声音则用内置提示音与本地音床混成一条母版轨。本文说明媒体来源边界、实测校验与混音规则；分镜字段见[分镜结构](storyboard-schema.md)，制作顺序见[制作流程](production-workflow.md)。

## 媒体进入作品的唯一路径

准备与渲染只读本地文件，不联网取素材。无论素材来自助手检索、公开媒体直链还是图库，进入作品的方式只有一条：

```powershell
uv run m2v article assets import --project videos/article-narrative/<slug> --manifest <清单.json> [--base <清单里 localPath 的基准目录>]
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

分镜的 `content.src` 必须指向 `assets/media/` 下的内容寻址文件，且必须能在来源记录里找到对应条目：

- 文件被替换（摘要变化）或实测尺寸与记录不符 → 校验失败，要求重新导入；
- 没有导入记录 → 校验失败，提示先执行 `m2v article assets import`；
- 导入记录本身被改动 → 记录摘要进入准备输入，重新 `prepare` 前会阻断。

准备阶段把素材文件摘要写进准备输入，因此替换素材会让准备、完整预演与评审全部过期。

## 画布比例

默认要求素材与 1080×1920 画布一致，容差 2%。比例不符时校验失败并提示可显式放宽；确实需要完整显示非 9:16 素材（例如示意图）时在该幕声明 `"aspectRatio": "any"`，并按 `fit: "contain"` 完整显示或 `fit: "cover"` 居中裁切。

图片幕可用 `photoZoom`（1～1.3）声明推拉幅度。视频幕用 `trimStartSeconds` 声明入点，剩余时长不足以覆盖镜头帧数时准备失败，不会静默裁短。

## 可选图库检索

```powershell
uv run m2v article assets search --project <目录> [--provider pexels|pixabay] [--kind video|photo|both] [--query <关键词> ...] [--per-page 15]
```

按幕顺序检索：不传 `--query` 时读取每幕的 `keywords`（`input.kind` 为 `topic` 时必填），传了就按顺序覆盖。检索只输出候选清单（含尺寸、时长、来源页、作者、许可与说明），不下载、不写作品文件；候选为空不是失败，助手可以改用其他公开媒体直链，再由 `import` 统一留证。凭据只从环境变量读取：Pexels 为 `M2V_PEXELS_API_KEY`，Pixabay 为 `M2V_PIXABAY_API_KEY`；缺少凭据时直接失败并指出变量名，不会静默匿名请求。Pixabay 检索响应在作品 `outputs/gallery-cache/` 缓存 24 小时，缓存不含 Key。

文章画布固定 9:16，因此检索默认按竖屏方向与画布比例约束候选（视频按比例挑选变体，Pexels 图片取保持原始比例的缩略图），不用于系统性批量下载。

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
