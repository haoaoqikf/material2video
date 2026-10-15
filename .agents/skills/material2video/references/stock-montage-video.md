# 在线素材剪辑视频

`stock-montage` 用于「只给主题和逐幕关键词，素材由工具自动检索并剪成竖屏短片」的作品。素材来自在线图库，因此检索与许可留证是这条流程的一部分：作品不保存图库响应，只保存下载到本地的素材与一份可核验的来源、作者、许可记录。

与 `general` 的分工：`general` 的材料是人手逐幕编排；本类型的材料是一份 `brief.json`，逐幕的素材由检索得到，时间轴由工具按目标时长自动分配。

## 工作流

```powershell
uv run m2v init --type stock-montage --project <slug>
# 编辑 brief.json：主题、逐幕关键词、目标时长、图库配置与可选口播/音床
# 设置图库凭据（只从环境变量读取，不写入作品）：
#   $env:M2V_PEXELS_API_KEY = "<在 https://www.pexels.com/api/ 申请的免费 key>"
uv run m2v stock search --project videos/stock-montage/<slug>
uv run m2v validate --project videos/stock-montage/<slug>
uv run m2v prepare --project videos/stock-montage/<slug>
uv run m2v preview --project videos/stock-montage/<slug>
# 查看完整预演，按 outputs/review.json 的全部准则填写评审结论
uv run m2v review-template --project videos/stock-montage/<slug>
uv run m2v review --project videos/stock-montage/<slug>
uv run m2v render --project videos/stock-montage/<slug>
```

下载的素材属于作品内容：它们留在被忽略的 `videos/<type>/<slug>/assets/stock/`，不入库；检索记录写在 `outputs/footage-search.json`。只把 `brief.json` 当作可编辑材料，检索记录与素材都是它的派生物。

## `brief.json` 契约

- 顶层 `schemaVersion` 为 1；`topic` 非空；`targetSeconds` 为 1 至 600 秒；`fps`、`width`、`height` 固定为 30、1080、1920；`durationToleranceSeconds` 默认 2 秒。
- `provider`：`name`（`pexels` 或 `pixabay`，默认 `pexels`）、`apiBase`（按来源默认官方地址，可覆盖以便离线测试）、`apiKeyEnv`（按来源默认环境变量名）、`orientation`、`perPage`（1 至 80；Pixabay 请求至少取 3 条，返回后按声明数量截取）、`media`（`video`/`photo` 的子集）、`minClipSeconds`/`maxClipSeconds`、`allowReuse`。凭据只从环境变量读取，缺失时检索在任何请求之前失败。
- `visual`：`theme`（`dark`/`light`）与**必填**的 `attribution` 署名文案；`motion.photoZoom` 为静图推拉的最大缩放（默认 1.12）。
- `scenes`：至少一幕，每幕有唯一 `id` 与非空 `keywords`；可选 `media`（限定该幕只要视频或只要图片）、`assetId`（钉住某个来源 ID）、`trimStartSeconds`（视频裁剪入点）、`durationFrames`（固定帧数）、`narration`（口播文本）、`speech`（该幕语速与停顿）、`transition`（`cut` 或 `crossfade` + 重叠帧数，首幕不允许转场）。
- `soundtrack.music`：作品目录内的本地音床，字段与共享声音契约一致（`sourceRef`、`gainDb`、`loop`、`fadeInMs`、`fadeOutMs`）。本类型没有 beat 轴，因此不接受 `soundtrack.effects`。

## 检索与许可

### 切换到 Pixabay

登录 [Pixabay API 文档](https://pixabay.com/api/docs/)领取 Key，设置当前 PowerShell 环境变量：

```powershell
$env:M2V_PIXABAY_API_KEY = "<你的 Key>"
# 可选：持久保存到 Windows 当前用户环境变量，新启动的程序生效
[Environment]::SetEnvironmentVariable("M2V_PIXABAY_API_KEY", $env:M2V_PIXABAY_API_KEY, "User")
```

在现有 `brief.json` 中将 `provider` 配置为下面的对象，并将 `visual.attribution` 改为 `素材来源：Pixabay`；随后执行原有 `m2v stock search` 流程：

```json
{
  "name": "pixabay",
  "apiBase": "https://pixabay.com/api",
  "apiKeyEnv": "M2V_PIXABAY_API_KEY",
  "orientation": "portrait",
  "media": ["video", "photo"]
}
```

只指定 `name` 时会按来源补全地址与凭据变量。由 Pexels 模板切换时应删除或替换原有 `apiBase`、`apiKeyEnv`，否则显式配置会继续优先。Pexels 的默认值仍为 `https://api.pexels.com` / `M2V_PEXELS_API_KEY`。一份作品选择一个来源，不自动回退或混搜。

Pixabay 按 [API 规则](https://pixabay.com/api/docs/)将检索响应缓存 24 小时，位置为作品 `outputs/stock-cache/`；缓存不包含 Key 或完整请求 URL，不入库。默认 API 额度为每 60 秒 100 次请求；仅用于人工指定作品的逐幕检索，不用于系统性批量下载。关键词拼接后不得超过 100 字符。普通图片使用 `largeImageURL`（最大边 1280），留证记录该版本尺寸；不会把原图尺寸当作下载尺寸。方向按实际候选尺寸过滤，严格竖屏或正方形条件可能没有候选；可将 `orientation` 改为 `any` 放宽。许可记录为 Pixabay Content License，仍需人工核验实际用途。

检索按幕独立查询，逐幕选定一个素材：先按声明关键词在返回文本中的命中数排序，再看方向、时长是否落在声明区间与分辨率适配，最后按来源 ID 稳定排序。整个过程不使用随机数，重复检索得到同一结果；已使用的来源 ID 不会重复使用（除非 `allowReuse` 为真）。任一幕没有可用候选即整体失败，报出该幕与关键词，并且不写出部分结果。

每个入选素材必须带来源页、作者与许可，缺一即不采用。检索记录保存来源页、作者、许可名称、媒体类型、像素尺寸、视频时长、文件内容摘要，以及当前 `brief.json` 的检索指纹与图库参数。素材文件、检索记录或 `brief.json` 任一变化都会让准备与评审过期，校验会要求重新检索——被外部替换过的素材不会进入渲染。

成片底部的署名行显示 `visual.attribution` 与当前幕素材的作者和图库名，因此画面本身保留了可核验的来源信息；完整来源 URL 与许可文本留在检索记录中。

## 自动剪辑规则

- 声明口播的幕由真实语音时长决定（末尾保留 12 帧阅读停留）；声明固定帧数的幕用固定帧数；其余幕均分「目标总时长 + 幕间重叠 − 已确定幕」的余量，并夹在 `minClipSeconds`/`maxClipSeconds` 与素材自身可用时长之间。
- 余数按幕顺序逐帧补齐或扣减，使编译后的总时长尽量等于 `targetSeconds`；最终偏差超过 `durationToleranceSeconds` 即失败，不会靠截断口播或压缩画面凑数。
- 短视频按 `trimStartSeconds` 起裁切本幕所需帧数；素材可用时长不足时明确失败。静图按幕交替做推拉与平移（缩放方向逐幕交替，平移方向 4 幕一轮），参数由准备阶段编译进 props。
- 幕间只支持硬切与交叉淡化；淡化帧数不小于相邻幕时长、或导致三幕同时重叠时失败。
- 画面为 1080×1920、30 fps。渲染期素材经回环 HTTP 提供给浏览器（只绑 127.0.0.1），渲染前素材已本地可用，画面不访问任何外部网络。
- 有口播或音床时，准备阶段产出覆盖全片的**单条母版音轨**并做响度归一；成片音轨为 44.1kHz 立体声 AAC-LC，与文章、通用类型同一交付规格。都没有时成片无声。

## 评审要点

正式渲染要求绑定当前准备指纹且结论为通过的评审，评审项覆盖画面质量（清晰度、构图、竖屏可读性、无重复素材）、剪辑节奏（逐幕时长、推拉平移与转场）、素材来源合规（每幕来源、作者与许可与实际画面一致且可核验），有音轨时另含口播、响度与字幕同步。
