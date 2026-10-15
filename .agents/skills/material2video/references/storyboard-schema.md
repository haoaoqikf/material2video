# 文章分镜 v5

`article-narrative` 只接受 `version: 5`、`schemaVersion: 5`。v1～v4 必须重新编排，不自动迁移；历史测试分镜不属于制作入口。

## 全片与场景

全片声明 `fps: 30`、`width: 1080`、`height: 1920`、`title`、可选 `visual: {"theme":"dark"}`（支持 dark/light）和非空 `scenes`。每幕声明 `id`、`template`、`content`、`narrationSegments`，可选 `transition: "cut" | "fade"`。首幕只能 cut。场景及旁白 ID 全片唯一。

`narrationSegments` 每项为 `{id,text}`，文字非空。屏幕摘要和完整旁白独立，展示元素为 `{text,segmentId,keywords?}`；`segmentId` 必须引用本幕旁白，`keywords` 必须出现在该元素文字中。源文为作品 `article.md` 或明确采用的 `article.accepted.md`；也可在 project.materials.article 指定作品内文件。

## 五种模板

| template | content 字段 | 限制 |
|---|---|---|
| point | title、summary 展示元素 | 一个核心观点 |
| compare | title、columns 两列，每列 title、items 展示元素 | 恰好两列，每列 1～4 项 |
| steps | title、items 展示元素 | 1～6 步，按不同旁白段顺序绑定 |
| cause | title、nodes（id 加展示元素）、links（from/to 加展示元素） | 1～6 节点、1～8 连线，分层有向无环图 |
| image | title、src、caption 展示元素、可选 fit | PNG/JPEG/WebP 作品内图片，contain 默认完整显示，cover 居中裁切 |

图片在准备时嵌入离线渲染材料并绑定原文件摘要。不自动搜图或生成图片。未知字段拒绝；旧 world、stages、camera、stateTracks 不属于 v5。

## 时间轴与实际量测

每段使用共享 TTS 独立合成，以实际音频推导帧数、字幕与展示时间。元素在绑定段开始后 8 帧淡入并轻微上移，随后保持稳定；步骤高亮跟随最新开始的旁白段。因果连线必须等待两端节点出现。

每幕声音结束后保留 12 帧稳定阅读，默认硬切。fade 在完整阅读尾段之后添加 8 帧画面交叉淡化，下一幕配音在淡化结束后开始。音轨不截断、不重叠。完整成片含停留及淡化最多 1800 帧（60 秒），没有原 130～170 字或 35～45 秒限制。

默认根据旁白原文自动生成画面字幕，预演和正式导出共用同一字幕层，无需配置开关；仅生成外置 SRT 不算完成字幕交付。字幕使用真实配音派生的帧边界，开始帧显示、结束帧隐藏，无讲话的停顿及阅读尾段不显示字幕。深浅主题均预留独立字幕区；general 嵌入保留文章本地字幕时间轴。

准备输出 `compiledScenes`、`segmentWindows`、`subtitleCues` 和 `durationInFrames`；这些为派生字段，不写回分镜。字幕层位于场景背景及正文之上；浏览器命中检查确认字幕实际可见，文字存在但被遮挡也会阻断预演。浏览器检查旁白边界、元素入场结束、字幕边界和每幕结尾的真实文字包围盒，溢出或侵入字幕区即失败。人工还需检查阅读节奏。

最小示例：

```json
{"version":5,"schemaVersion":5,"fps":30,"width":1080,"height":1920,"title":"反馈帮助改进","scenes":[{"id":"opening","template":"point","content":{"title":"先看反馈，再修正","summary":{"text":"修正方法才有进步","segmentId":"line","keywords":["修正"]}},"narrationSegments":[{"id":"line","text":"观察结果，根据反馈修正下一次的做法。"}]}]}
```

完整示例：[缓冲](../../../../examples/buffer-smoothing/storyboard.json)、[试错](../../../../examples/darts-trial-and-error/storyboard.json)、[选择](../../../../examples/keynote-baseline/storyboard.json)。当前规格见 [article-explainer](../../../../openspec/specs/article-explainer/spec.md)。
