# 验证与审查

## 验证

- `pnpm build` 与 `pnpm typecheck`：通过。构建有既有依赖注释与包体大小提示，不影响构建。
- `uv run pytest tests/test_article_explainer.py tests/test_general_video.py -q -p no:cacheprovider --basetemp .cache/pytest-subtitle-stacking-final`：36 项通过，包含真实浏览器深浅主题、字幕命中及故意恢复旧层级后拒绝验收的测试。
- OpenSpec 严格变更校验、类型目录文档同步检查、文档链接、JSON 示例与 Git 空白检查：通过。
- 固定的三个示例通过材料校验；无分镜字段变化，无需修改示例内容。

## 审查

- 主要发现：共享场景的 z-index: 1 遮住字幕；旧测试只检查文本与几何位置，不能证明真实可见。修复为字幕显式 z-index: 2，量测增加逐行中心命中检查。
- 逻辑影响：预演与正式导出共用修复后的 composition，general 内嵌同样受益；字幕文字存在但被背景覆盖会阻断完整预演。
- 性能影响：逐行检查复用既有浏览器量测帧和页面执行，无新增浏览器启动或额外求帧；成片每帧仅增加固定样式属性。
- 剩余风险：命中探针不是逐像素遮挡证明；通过真实 MP4 抽帧补充验证，不宣称人工试听或全帧视觉评审。
- 质量评分：98/100；扣分原因是探针按文字行中心采样，未做全帧逐像素比对。

## 实际成片

三个作品均完成重新 prepare → 完整 preview → render，统一入口已验收完整帧数、1080×1920、30 fps 与音轨。成片溯源、准备记录及排版验收指纹一致；分别从正式 MP4 抽取讲话帧并目视确认画面字幕可见。

| 作品 | 帧数 | 秒数 | 字幕条数 |
|---|---:|---:|---:|
| buffer-smoothing | 590 | 19.67 | 8 |
| darts-trial-and-error | 740 | 24.67 | 9 |
| keynote-baseline | 874 | 29.13 | 12 |

沿用原有有效音色选择与旁白；内容及媒体保留在被忽略的 videos/article-narrative 目录，不纳入版本控制。
