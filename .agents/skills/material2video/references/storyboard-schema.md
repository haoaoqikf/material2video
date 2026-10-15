# 文章分镜 v6

`article-narrative` 只接受 `version: 6`、`schemaVersion: 6`。v5 及更早分镜必须重新编排，不自动迁移；历史测试分镜不属于制作入口。

## 全片与场景

全片声明 `fps: 30`、`width: 1080`、`height: 1920`、`title`、`input`、可选 `targetSeconds`、可选 `visual: {"theme":"dark"}`（支持 dark/light）、可选顶层 `soundtrack` 和非空 `scenes`（最多 300 幕）。

`input` 为 `{"kind":"article"}` 时绑定作品 `article.md` 或明确采用的 `article.accepted.md`（也可在 `project.materials.article` 指定作品内文件），必须先通过源文语义审查；为 `{"kind":"topic","topic":"<非空主题>"}` 时只声明主题，跳过源文与源文语义审查，此时每幕必须声明 `keywords`。`targetSeconds` 为 1～600 的整数，默认 60，只用于分配无旁白镜头的剩余时长。

每幕声明 `id`、`template`、`content`、`narrationSegments`，可选 `keywords`、`durationFrames`、`transition`、`transitionFrames`、`aspectRatio`、`speech`。转场支持 `cut`、`fade`、`crossfade`，首幕只能 cut；`transitionFrames` 为 1～1800 的整数，默认 8。`durationFrames` 为 1～18000 的整数，声明后必须容得下旁白、12 帧阅读停留与转场，不得截断口播。场景及旁白 ID 全片唯一。

`narrationSegments` 每项为 `{id,text}`，文字非空。屏幕摘要和完整旁白独立，展示元素为 `{text,segmentId,keywords?}`；`segmentId` 必须引用本幕旁白，`keywords` 必须出现在该元素文字中。

## 六种模板

| template | content 字段 | 限制 |
|---|---|---|
| point | title、summary 展示元素 | 一个核心观点 |
| compare | title、columns 两列，每列 title、items 展示元素 | 恰好两列，每列 1～4 项 |
| steps | title、items 展示元素 | 1～6 步，按不同旁白段顺序绑定 |
| cause | title、nodes（id 加展示元素）、links（from/to 加展示元素） | 1～6 节点、1～8 连线，分层有向无环图 |
| image | title、src、caption 展示元素、可选 fit、可选 photoZoom | PNG/JPEG/WebP，photoZoom 为 1～1.3 |
| video | title、src、caption 展示元素、可选 fit、可选 trimStartSeconds | MP4/MOV/M4V/WebM，按入点裁切 |

图片与视频幕允许没有旁白，也允许只写画面标题；此时没有展示元素，不需要 `segmentId`。媒体只接受 `assets/media/` 下已导入并留证的内容寻址文件，默认要求与画布 9:16 一致（容差 2%），个别幕可显式 `aspectRatio: "any"` 放宽；导入、留证与音效规则见[文章媒体与音效](article-media-and-sound.md)。未知字段拒绝；旧 world、stages、camera、stateTracks 不属于 v6。

## 时间轴与实际量测

每段使用共享 TTS 独立合成，以实际音频推导帧数、字幕与展示时间。元素在绑定段开始后 8 帧淡入并轻微上移，随后保持稳定；步骤高亮跟随最新开始的旁白段。因果连线必须等待两端节点出现。

每幕声音结束后保留 12 帧稳定阅读，默认硬切。`fade`/`crossfade` 在前一幕完整阅读尾段之后按 `transitionFrames` 交叉淡化，下一幕配音在淡化结束后开始，前后口播不重叠。无旁白镜头的时长取声明的 `durationFrames`，未声明时与其余无旁白镜头平分 `targetSeconds` 的剩余帧数。音轨不截断、不重叠，母版轨严格裁到全片时长。完整成片含停留及淡化最多 18000 帧（600 秒），没有原 130～170 字或 35～45 秒限制。

默认根据旁白原文自动生成画面字幕，预演和正式导出共用同一字幕层，无需配置开关；字幕烧录进画面，不导出外置字幕文件，因此「有字幕」只能以成片里的可见文字为准。字幕使用真实配音派生的帧边界，开始帧显示、结束帧隐藏，无讲话的停顿及阅读尾段不显示字幕。深浅主题均预留独立字幕区。

准备输出 `compiledScenes`、`segmentWindows`、`subtitleCues` 和 `durationInFrames`，媒体幕另派生 `mediaPath` 与 `trimStartFrames`；这些为派生字段，不写回分镜。字幕层位于场景背景及正文之上；浏览器命中检查确认字幕实际可见，文字存在但被遮挡也会阻断预演。浏览器检查旁白边界、元素入场结束、字幕边界和每幕结尾的真实文字包围盒，溢出或侵入字幕区即失败。人工还需检查阅读节奏。

最小示例：

```json
{"version":6,"schemaVersion":6,"fps":30,"width":1080,"height":1920,"title":"反馈帮助改进","input":{"kind":"article"},"targetSeconds":60,"scenes":[{"id":"opening","template":"point","keywords":["修正"],"content":{"title":"先看反馈，再修正","summary":{"text":"修正方法才有进步","segmentId":"line","keywords":["修正"]}},"narrationSegments":[{"id":"line","text":"观察结果，根据反馈修正下一次的做法。"}]}]}
```

完整示例：[缓冲](../../../../examples/buffer-smoothing/storyboard.json)、[试错](../../../../examples/darts-trial-and-error/storyboard.json)、[选择](../../../../examples/keynote-baseline/storyboard.json)。当前规格见 [article-explainer](../../../../openspec/specs/article-explainer/spec.md)。
