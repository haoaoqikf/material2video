# 验证与复核

## 定向验证

- `uv run pytest tests/types/general/test_subtitle_size.py tests/types/general/test_article_explainer.py::test_prepare_binds_frame_subtitle_and_media tests/common/test_design_tokens.py`：36 passed，1 个浏览器节点按默认策略未收集；首次运行出现既有 `.pytest_cache` 写权限警告，测试全部通过。后续测试使用已忽略的 `outputs/test-cache-subtitle-size`。
- `uv run pytest tests/types/general/test_subtitle_size.py::test_browser_uses_prepared_subtitle_size_and_rejects_drift tests/types/general/test_article_explainer.py::test_browser_subtitle_layout_and_random_seek tests/types/general/test_article_explainer.py::test_browser_blocks_subtitle_overflow tests/types/general/test_article_explainer.py::test_browser_detects_covered_subtitle -o cache_dir=outputs/test-cache-subtitle-size`：5 passed，包含真实浏览器 52px 计算字号通过、强制40px漂移拒绝、横竖屏、溢出与遮挡。
- `uv run pytest tests/common/test_single_pass_delivery.py::test_general_materializes_only_intersecting_scenes_and_offsets -o cache_dir=outputs/test-cache-subtitle-size`：1 passed；补齐该合成夹具的必需准备字幕样式，继续保护窗口裁切与原准备不变。
- `uv run pytest tests/common/test_doc_facts.py::test_tracked_markdown_links_and_anchors_resolve -o cache_dir=outputs/test-cache-subtitle-size`：1 passed。
- `pnpm exec vitest run src/types/general/ArticleExplainer.test.tsx`：6 passed；`pnpm typecheck`：通过。
- `openspec validate add-project-subtitle-size --strict`、`git diff --check`：通过。变更文档中的 JSON 示例均经解析检查。

未运行全仓回归或完整成片生成；浏览器验证仅使用测试临时夹具，作品制作由主代理继续。

## 独立代码复核

独立子代理复核配置边界、直接适配器调用、准备样式传播、指纹失效、量测与前端消费链，未发现必须修复项。作者补充检查所有 `materialize` 测试调用者，并更新缺少字幕对象的合成夹具。

逻辑影响：仅 general 可声明该字段；未配置的样式与画幅清单完全一致。一个解析后的完整字幕样式进入 props、inputs 和各消费者。完整 project 已绑定准备指纹，添加、更改、移除配置都会使旧准备失效。

性能影响：固定规模配置校验；每个现有字幕量测帧多一次计算字号读取。无新依赖、媒体 I/O、缓存维度膨胀或随片长增长的额外常驻数据。已有 frames、SubtitleStyle 与合成组件满足需求，直接复用。

剩余边界：增大字号可能让具体长字幕换行或溢出；现有浏览器量测继续阻断溢出，作品手机尺寸可读性仍须独立复核。未改变安全区或自动缩字。

代码质量评分：98/100。扣分保留给具体长字幕及极限字号在作品中的布局风险，当前定向技术检查均通过。
