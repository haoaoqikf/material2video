## Context

准备阶段已把实际 TTS 字幕转换为 subtitleCues。预演与正式导出共用 ArticleExplainer，general 直接传递子作品 props。

## Goals / Non-Goals

固定默认字幕的可验证契约；不新增开关、不修改分镜结构、不重渲染历史作品。

## Decisions

- 保留现有自动字幕实现，避免重复字幕层或引入另一套时间轴。
- 扩展现有 Python 与浏览器测试，验证默认生成、起止帧、静音尾段、主题对比度和嵌入传递；不以外置 SRT 代替画面验证。
- README 说明当前能力，Skill 和分镜参考说明操作及安全区；无需修改未来路线。

## Risks / Trade-offs

合成语音测试替身不能证明服务实际发音自然度；本变更仅验证字幕传递与绘制，不改变 TTS 服务。
