# 文章类型制作流程

文章制作流程适用于 `article-narrative`，保留文章原有输入审查、v4 分镜、口播与连续性评审门禁。文章材料与输出由 `project.json` 所属作品目录统一管理。

```powershell
uv run m2v article input-review --article videos/<slug>/article.md
uv run m2v validate --project videos/<slug>
uv run m2v prepare --project videos/<slug>
uv run m2v article template --storyboard videos/<slug>/storyboard.json
uv run m2v article keyframes --storyboard videos/<slug>/storyboard.json
uv run m2v article samples --storyboard videos/<slug>/storyboard.json
uv run m2v article rehearsal --storyboard videos/<slug>/storyboard.json
uv run m2v article status --storyboard videos/<slug>/storyboard.json
uv run m2v preview --project videos/<slug>
uv run m2v review-template --project videos/<slug>
uv run m2v review --project videos/<slug>
uv run m2v render --project videos/<slug>
```

全片铺开前，先生成并静音查看开场、核心论证和高潮的关键幕样片，确认对象状态/关系推进、焦点或镜头变化及动作后的稳定结果。随后查看联系表和全片有声预演，按[视觉评审量表](visual-review-rubric.md)填写静态、动态和连续性评审证据。材料或源文件变化后重新准备并评审，不能复用旧结论。

统一视频命令和退出码见仓库 README；文章字段及专用语义规则见[分镜结构](storyboard-schema.md)和[文章生成分镜](article-to-storyboard.md)。
