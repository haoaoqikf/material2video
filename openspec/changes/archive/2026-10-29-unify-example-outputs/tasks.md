## 1. 产物路径

- [x] 1.1 `delivery.outputs` 直接返回作品根下的 `outputs/`。
- [x] 1.2 `qa.delivered_video` 与 QA 报告目录使用作品根。
- [x] 1.3 general 的 preview/render 输出根使用作品根。
- [x] 1.4 render 成功后的清理目录使用作品根。

## 2. 测试

- [x] 2.1 更新示例 QA 报告位置测试，断言写入 `examples/<slug>/outputs/` 且不落到 `videos/examples/`。
- [x] 2.2 更新示例产物在作品根之外的预演测试，覆盖新的默认位置语义。

## 3. 文档与规格

- [x] 3.1 更新 `paths.md`、`production-workflow.md`、`visual-review-rubric.md` 中的示例产物路径。
- [x] 3.2 更新三个示例的 README/VERIFICATION/DESIGN 中的产物路径。
- [x] 3.3 同步 `openspec/specs` 中 article-workspace、modular-video-production、article-explainer 的描述。

## 4. 迁移与验证

- [x] 4.1 合并 `videos/examples/*/outputs/` 到 `examples/*/outputs/`，冲突按修改时间保留较新版本。两个不可读的临时目录未能迁移，已在 design.md 披露。
- [x] 4.2 运行相关 Python 测试与文档检查。
- [x] 4.3 检查暂存内容并提交。
