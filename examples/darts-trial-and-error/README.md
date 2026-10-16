# darts-trial-and-error 讲解示例

当前 storyboard.json 为文章 v7 混合媒体讲解分镜，保持原文主题。先完成源文语义审查，再通过统一 m2v prepare、preview、render（画面 review 为可选工具）制作。

图片幕使用已导入的本地素材 `assets/media/`（原创 CC0，见 `assets/LICENSE.md`），来源记录见 `assets/media-sources.json`。该示意图不是 9:16，因此该幕显式声明 `aspectRatio: "any"`，并按 `contain` 完整显示、加轻微推拉。

末幕是代码场景：`scenes/timeline.tsx` 用 `gsap` 时间轴逐条推入步骤并旋转靶心，该幕没有旁白，用声明的固定帧数录制。片段由 `prepare` 实时录制到 `outputs/code-cache/`。

三个固定示例共同覆盖观点、对比、步骤、因果图、图片配文、视频镜头与代码场景。

字段见 [分镜结构](../../.agents/skills/material2video/references/storyboard-schema.md)、[媒体素材与音效](../../.agents/skills/material2video/references/article-media-and-sound.md)。生成媒体与 outputs 不入库。
