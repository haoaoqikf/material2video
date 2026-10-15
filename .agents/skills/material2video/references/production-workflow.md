# 文章讲解制作流程

文章作品使用 project.json 和 v5 storyboard.json，先保存源文并完成 [输入审查](input-review.md)，编排完整旁白，再由制作助手按[自动选音流程](../SKILL.md)选择并保存音色。用户明确指定音色时沿用其选择。统一制作入口：

```powershell
uv run m2v validate --project videos/article-narrative/<slug>
uv run m2v prepare --project videos/article-narrative/<slug>
uv run m2v preview --project videos/article-narrative/<slug>
uv run m2v render --project videos/article-narrative/<slug>
uv run m2v status --project videos/article-narrative/<slug>
```

prepare 根据每段实际 TTS 编译时间轴并缓存音频，支持现有音色、语速与停顿配置。preview 自动进行真实浏览器排版量测，并生成有声完整视频；限帧预览不能用于正式导出。`m2v article keyframes --storyboard <路径>` 输出各幕结果帧用于静态检查；samples/rehearsal 均调用完整预演，v5 不再使用旧动画关键幕抽样流程。

可选的 review.json 绑定当前准备指纹和完整预演摘要，主动评审时填写五项通过依据：信息清晰、模板布局、图文关系、旁白同步、阅读节奏。无另一个 production.json 专用门禁。源文、图片、分镜、输入审查、音轨、渲染代码或字体变化均要求重新准备与完整预演；人工画面评审不阻断导出。

正式渲染先生成临时文件、核验画布帧数与声音，再替换 outputs/video.mp4 并保存溯源。失败不覆盖旧成片。旧准备及评审不兼容；v1～v4 分镜须重新编排。通用视频内嵌文章保留完整画面、字幕和声音，仍需文章原文语义审查与当前完整预演自动验收。

默认流程为材料审查 → 编排旁白 → 选择音色并保存 → 校验与准备 → 完整预演 → 正式导出；无需人工查看画面、填写依据或再次确认。可选人工评审记录缺失、待填、失败或过期均不阻断导出；主动执行 `review` 时仍检查当前绑定、结论与非空依据，不自动生成人工通过结论。
