# 让编码助手做一条 10 秒竖屏文字动效

先按照[快速开始](../README.md#三分钟做出第一条视频)准备环境和已登记字体。把下面整段交给能读取本仓库、运行终端并使用独立评审代理的编码助手，例如 Codex 或 Claude Code。在本仓库根目录开始，不需要创建 OpenSpec 变更，也不要改共享运行时代码。

```text
请先读 AGENTS.md 和 .agents/skills/material2video/SKILL.md，按 Material2Video 的 Skill 做一条 10 秒竖屏文字动效。

用 text-motion 建独立作品 agent-title-demo，1080×1920、30 帧/秒。开场标题「把想法做成画面」，中段依次排出「文字」「节奏」「画面」，结尾收束到「先做出第一幕」。用深蓝底和暖白文字，不加旁白、字幕、外部素材或片尾制作说明。先确定三个节拍各自的主次，再用可按帧定位的排版和动效把它们连起来，让手机竖屏上能看清停留中的文字。

按 Skill 先做代表样品和适用的独立评审，再完成 RESEARCH.md、DESIGN.md 及各正式场景的设计文档。用正式分镜定义尺寸、帧率和时间，不在场景源码另设一份全片时间表。安装并验证独立工程，导出后按 Skill 提交正式关键帧、适用的片段证据和技术 QA；没能完成独立评审就明确列为未完成。用 ffprobe 报告真实时长、分辨率和文件大小，给出工程、成片和验证证据的实际路径。不要把作品文件或生成媒体加入本仓库 Git。
```

预期产出是包含 `project.json`、`storyboard.json`、场景源文件和设计材料的 `videos/text-motion/agent-title-demo/`，以及其中的 `outputs/video.mp4` 和验证证据；若配置了独立内容根，以助手报告的实际路径为准。目标为 300 帧、10 秒、1080×1920；在真正跑过验证之前，这些不是实测结果。

## 助手会读什么

以下入口都在 `.agents/skills/material2video/references/`。具体选读由 [Skill](../.agents/skills/material2video/SKILL.md) 与[阅读路由](../.agents/skills/material2video/references/guidance-routes.json)决定；无旁白和外部素材，不需要配音或授权工作流。

| 任务 | 参考文件 |
| --- | --- |
| 研究、试制、正式设计和交付 | [production-workflow.md](../.agents/skills/material2video/references/production-workflow.md)、[stage-research.md](../.agents/skills/material2video/references/stage-research.md)、[stage-design.md](../.agents/skills/material2video/references/stage-design.md)、[stage-production.md](../.agents/skills/material2video/references/stage-production.md) |
| 拆解排版与动效并落实各场 | [reference-video-analysis.md](../.agents/skills/material2video/references/reference-video-analysis.md)、[visual-components.md](../.agents/skills/material2video/references/visual-components.md)、[scene-design.md](../.agents/skills/material2video/references/scene-design.md)、[code-scene-runtime.md](../.agents/skills/material2video/references/code-scene-runtime.md) |
| 样品、独立评审和技术核验 | [design-samples.md](../.agents/skills/material2video/references/design-samples.md)、[review-contract.md](../.agents/skills/material2video/references/review-contract.md)、[subagent-review.md](../.agents/skills/material2video/references/subagent-review.md)、[visual-review-rubric.md](../.agents/skills/material2video/references/visual-review-rubric.md)、[render-engine.md](../.agents/skills/material2video/references/render-engine.md) |
