# keynote-baseline 讲解示例

当前 storyboard.json 为文章 v7 混合媒体讲解分镜，保持原文主题。先完成源文语义审查，再通过统一 m2v prepare、preview、render（画面 review 为可选工具）制作。

视频幕：素材由 `assets/generate.py` 合成并导入到 `assets/media/`（原创 CC0，见 `assets/LICENSE.md`），来源记录见 `assets/media-sources.json`。该幕没有旁白，用声明的固定帧数播放，并按 `trimStartSeconds` 裁切入点。

末幕是代码场景：`scenes/three-world.tsx` 用 `@react-three/fiber` 与 `@react-three/drei` 画一个缓慢自转的二十面体与星空，同样没有旁白、按声明帧数录制。片段由 `prepare` 实时录制到 `outputs/code-cache/`。

三个固定示例共同覆盖观点、对比、步骤、因果图、图片配文、视频镜头与代码场景。

字段见 [分镜结构](../../.agents/skills/material2video/references/storyboard-schema.md)、[媒体素材与音效](../../.agents/skills/material2video/references/article-media-and-sound.md)。生成媒体与 outputs 不入库。
