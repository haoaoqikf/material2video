## 名称选择

新名称使用 `compound-interest`：与示例主题《复利》一致，保持仓库现有示例的短横线主题命名（`american-science-milestones`、`solar-system-journey`），不与 OpenSpec 能力名 `compound-interest-explainer-video` 混用。

## 迁移方式

- 目录用 `git mv` 改名，保留文件历史。
- `project.json` 的 `id` 同步改名；`m2v` 的准备指纹包含项目 ID，因此必须重新准备与渲染，不能只改目录。
- 示例目录内 `outputs/` 与 `videos/examples/<slug>/` 均为生成内容，随目录/项目 ID 迁移，保持评审证据与基线可追溯；它们仍不入库。
- 视觉、声音与分镜内容不变，重新渲染用于绑定新项目 ID 与准备指纹；若成片画面与旧版一致，记录新旧摘要并说明差异仅来自绑定信息。

## 文档与校验

- 固定示例名单在 `tests/example_catalog.py` 与 `AGENTS.md` 中只有一份口径，改名时同步。
- `README.md`、示例文档、Skill 参考、测试与主规格中的路径和名称全部更新。
- 历史归档变更不改写，避免伪造历史；当前主规格与当前示例保持一致。
