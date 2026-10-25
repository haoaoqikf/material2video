## Why

`examples/five-life-choices` 的内容已在上一变更中整体替换为30秒《复利》，但目录名与项目 ID 仍沿用旧主题名称。当前状态会让示例清单、命令、文档与输出路径继续指向一个已经不存在的作品主题，也容易让读者误以为仓库仍保留五选择示例。

## What Changes

- 将示例目录 `examples/five-life-choices` 更名为 `examples/compound-interest`。
- 将 `project.json` 的项目 ID 从 `five-life-choices` 改为 `compound-interest`，使命令、准备记录与输出路径一致。
- 将渲染输出目录从 `videos/examples/five-life-choices` 迁移为 `videos/examples/compound-interest`，保留基线、评审包与验证证据。
- 同步更新仓库固定示例名单、根 README、示例文档、Skill 参考、测试清单、测试内路径与 OpenSpec 主规格中的名称。
- 不改变分镜、场景代码、数学、声音、画幅、帧率、帧数或画面内容；不恢复五选择主题或兼容入口。

## Capabilities

### Modified Capabilities

- `article-explainer`: 固定示例集合中的《复利》目录与项目 ID 更正为 `compound-interest`，其余示例契约不变。

## Impact

- 受影响路径：`examples/compound-interest/`、`videos/examples/compound-interest/`、`README.md`、`AGENTS.md`、`.agents/skills/material2video/references/`、`tests/`、`web/src/`、`openspec/specs/article-explainer/spec.md`。
- 项目 ID 参与准备指纹，改名后需重新 `prepare`、`render` 与 `qa`，使最终视频绑定新指纹。
- 归档变更中的旧名称保留为历史记录，不回写。
