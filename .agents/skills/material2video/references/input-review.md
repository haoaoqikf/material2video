# 输入文章审查

输入审查必须早于口播重写、分镜和配音。目标正文为130～170字，标题、标点与空白不计；数字、英文字母及其余 Unicode 码点逐个计数。脚本只负责计数、来源摘要和流程门禁，不能判断观点或场景语义。

## 开始审查

没有分镜时，以文章文件启动：

```bash
uv run m2v article input-review --article videos/article-narrative/<slug>/article.md
```

使用 `uv run m2v article input-review --article <原文>`；已有分镜时使用 `--storyboard <分镜>`。工具会创建或更新 `production.json` 中的 `inputReview`，记录正文计数、来源路径和 SHA-256。随后 AI 必须阅读完整原文并填写 `singleScene` 与 `assessment`：核心观点 `claim`、持续视觉隐喻 `metaphor`、可核查的判断依据 `rationale`、问题段落 `problemSpans`，以及模型和会话来源。只有字数合格、语义判断通过且来源摘要匹配，审查状态才可为 `pass`。

单场景要求贯穿整条视频的视觉世界持续存在。镜头推进、拉远、焦点变化、对象数量与状态变化都可用；必须切换到独立视觉世界才能说明必要推理时应判 `fail`。证据不足时保持 `pending`，不得靠猜测放行。

## 不合格文章

保留 `article.md` 原文。向用户说明具体问题、涉及段落和依据，并给出不虚构论据、忠于原意且正文130～170字的候选稿。空白或不可读原文没有足够依据时不得编造候选。候选稿保存前先写入临时文件，再用脚本登记：

```bash
uv run m2v article candidate --article videos/article-narrative/<slug>/article.md --text-file <候选稿临时文件>
```

登记只接受130～170字候选稿，并绑定当前原文摘要。候选稿不会被自动采用，也不能进入分镜或配音。用户明确采用后才执行：

```bash
uv run m2v article adopt-candidate --article videos/article-narrative/<slug>/article.md
```

脚本把候选复制为忽略 Git 的 `article.accepted.md`，原文保持不变，并重置语义审查。AI 必须重新阅读采用稿、重新给出核心观点与单场景依据；审查通过前不得生成分镜或媒体。原文或候选稿在授权后变化会使授权和审查失效。

`m2v prepare` 在请求语音服务或写媒体前再次验证有效审查与文章摘要。缺失、待审、失败、来源变化或采用授权失效时立即停止。完整制作顺序为：输入审查 → 核心观点与隐喻设计 → 分镜及动画编排 → 配音准备 → 实际时长检查 → 评审与渲染。
