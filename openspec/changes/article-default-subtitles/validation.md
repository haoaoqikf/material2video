# 验证与审查

- `uv run pytest tests/test_article_explainer.py tests/test_general_video.py -q -p no:cacheprovider --basetemp .cache/pytest-article-subtitles`：35 项通过，包含深浅主题真实浏览器检查，无跳过。
- `pnpm typecheck`：通过；文章及 general composition 测试：6 项通过。
- OpenSpec 严格变更校验、类型目录文档同步检查、git diff --check：通过。
- README、Skill 与分镜参考的 25 个相对链接及 JSON 示例：通过；三个固定示例通过现有严格材料校验。

## 审查结论

- 主要发现：当前准备始终生成字幕，预演与正式导出共用 ArticleExplainer 及其 subtitleCues；general 原样保留子作品 props 并使用文章 composition，未发现字幕遗漏。
- 逻辑影响：仅明确既有默认交付要求，补充字幕文本、帧边界、阅读尾段、主题对比度及嵌入传递断言；公共接口、材料结构和既有示例无需改动。
- 性能影响：生产逻辑未修改，无新增运行时计算或 I/O。
- 剩余风险：TTS 使用测试替身；本次未生成新 MP4，预演和导出共用字幕实现通过代码核对与浏览器求帧验证，未进行编码后视频像素比对。初次测试出现缓存权限警告，使用独立临时目录复核已通过。
- 质量评分：96/100；扣分源于未执行真实 TTS 与编码后 MP4 检查。
