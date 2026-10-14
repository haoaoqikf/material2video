# darts-trial-and-error 讲解制作流程

本目录只保存可复用的示例源码，运行产物写入被忽略 Git 的 `videos/examples/darts-trial-and-error/outputs/`。

统一入口：

```powershell
uv run m2v article input-review --storyboard examples/darts-trial-and-error/storyboard.json
uv run m2v prepare --project videos/examples/darts-trial-and-error
uv run m2v preview --project videos/examples/darts-trial-and-error
uv run m2v review-template --project videos/examples/darts-trial-and-error
uv run m2v render --project videos/examples/darts-trial-and-error
```

输入语义审查和所有视觉评审必须来自实际文章与实际材料，不复制历史示例的通过结论；`legacy-test-storyboard.json` 只供旧共享动画回归，不能作为 article-narrative 输入。
