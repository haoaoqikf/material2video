# 讲解输入审查

先在作品内保存非空 article.md。采用稿存在时使用 article.accepted.md；也可由 project.materials.article 显式指定源文。

```powershell
uv run m2v article input-review --storyboard videos/article-narrative/<slug>/storyboard.json
```

命令生成 outputs/input-review.json，记录源文相对路径、SHA-256 和正文计数（排除一级标题、标点和空白）。计数只用于记录，不要求 130～170 字。阅读原文后填写 status、claim、rationale、reviewer、problemSpans；通过时 status 为 pass、依据非空且 problemSpans 为空。工具不会自动判定语义通过。

不合格材料可运行 `m2v article candidate --article <article.md> --text-file <候选文本>`；原文保持不变，候选必须非空并绑定原文摘要。用户明确采用后执行 `m2v article adopt-candidate --article <article.md>`，再重新审查。源文或候选变化须重新生成；采用不等于审查通过。

当前审查是 v5 讲解语义审查，不要求单世界隐喻或连续性。旧 production.json 与 singleScene 评审不能用于当前制作。
