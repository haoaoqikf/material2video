# 制作流程

本流程适用于仓库内的示例和 `videos/<slug>/` 中的作品。制作记录及渲染产物写入忽略目录，不复制示例的评审通过结论。

```powershell
uv run python .agents/skills/article2video/scripts/production.py status --storyboard videos/<slug>/storyboard.json
uv run python .agents/skills/article2video/scripts/production.py keyframes --storyboard videos/<slug>/storyboard.json
uv run python .agents/skills/article2video/scripts/production.py samples --storyboard videos/<slug>/storyboard.json --media videos/<slug>/outputs/media/media.json
uv run python .agents/skills/article2video/scripts/production.py rehearsal --storyboard videos/<slug>/storyboard.json --media videos/<slug>/outputs/media/media.json
uv run python .agents/skills/article2video/scripts/production.py status --storyboard videos/<slug>/storyboard.json
```

全片铺开前，先基于完整 v4 草稿生成开场、核心论证和高潮的关键幕样片。**先静音播放关键幕样片**，逐段确认对象状态/关系推进、焦点或镜头变化、动作后的稳定结果；同一视觉世界或相同构图可以持续，但只有字幕/标签变化、看不到论证性状态推进时，必须记录必改项并退回视觉转译或动画设计。通过后再铺开其余阶段。

随后查看关键幕联系表和全片有声预演，按[视觉评审量表](visual-review-rubric.md)逐阶段、全片记录基于实际画面的证据与返工项。全片“节奏”必须单独评分至少 4/5，并以有声预演中的时间码或明确阶段为依据；总分不得抵消节奏低分。关键幕静态、动态或连续性评审仍有 pending/fail、材料或源文件变化导致结论过期、或有未解决必改项时，正式渲染继续阻断。评审版和关键幕样片仍可用于返工。

材料或源文件变化后重新生成受影响的评审材料，不能复用旧结论。

正式成片仍须通过输入审查、字数及时长、严格分镜校验、视觉/动态/连续性评审与制作记录门禁；命令细节见各脚本的 `--help`。
