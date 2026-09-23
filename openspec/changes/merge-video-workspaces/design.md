# 设计

`ArticlePaths.output_dir` 改为源文章目录下的 `outputs` 子目录。`workspace_outputs` 直接返回该目录的父级不再适用，跨文章媒体校验改为基于所有文章的作品输出目录判断。

源目录规则保持不变：正式作品位于 `videos/<slug>/`，示例源文件位于 `examples/<slug>/` 或兼容的 `videos/examples/<slug>/`。本次仓库内已有示例产物迁移到 `videos/examples/<slug>/outputs/`，正式作品迁移到 `videos/<slug>/outputs/`。

显式输出路径仍优先，因此用户可以继续把产物写到任意明确位置；只有省略输出参数时才使用新的默认路径。
