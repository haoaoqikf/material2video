# 制作流程

本流程适用于仓库内的示例和 `videos/<slug>/` 中的作品。制作记录及渲染产物写入忽略目录，不复制示例的评审通过结论。

```powershell
uv run python .agents/skills/article2video/scripts/production.py status --storyboard videos/<slug>/storyboard.json
uv run python .agents/skills/article2video/scripts/production.py keyframes --storyboard videos/<slug>/storyboard.json
uv run python .agents/skills/article2video/scripts/production.py rehearsal --storyboard videos/<slug>/storyboard.json
uv run python .agents/skills/article2video/scripts/production.py status --storyboard videos/<slug>/storyboard.json
```

先查看关键阶段联系表和全片有声预演，再按[视觉评审量表](visual-review-rubric.md)记录观察证据与返工项。材料或源文件变化后重新生成受影响的评审材料，不能复用旧结论。

正式成片仍须通过输入审查、字数及时长、严格分镜校验、视觉/动态/连续性评审与制作记录门禁；命令细节见各脚本的 `--help`。
