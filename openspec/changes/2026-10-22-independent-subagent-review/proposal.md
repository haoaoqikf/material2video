## Why

制作流程里的关键判断长期由制作助手自己完成。作者知道设计意图和后续内容，无法可靠冒充第一次观看者；`director-review-and-edit.md` 明确承认只能做到「角色分离自审」，`video-production-workflow` 主规格也写「同一助手执行……不要求新增代理」。实际结果是：冷审、候选淘汰、美术方向比较、逐场观察复述等环节容易退化为填表，直到用户看到成片才发现问题。

需要把 A 级与 B 级评审的组织方式集中成可查证的规则：默认由独立子代理执行，只投喂评审包；环境不具备时降级为角色分离自审并显著披露，但不关闭评审项。

## What Changes

- 新增 `.agents/skills/material2video/references/subagent-review.md`：定义 A 级与 B 级清单、评审包、匿名化、评审者身份与证据、先描述后判定、降级披露、`visual-notes.md` 记录、不适用环节与成本控制。
- 修改 `SKILL.md`、`creative-production.md`、`scene-design-and-acceptance.md`、`director-review-and-edit.md`、`reach-potential.md`、`reference-style.md`、`production-workflow.md`、`article-to-storyboard.md`、`visual-review-rubric.md` 与 `README.md`，改为显式要求并引用新文档。
- 修改 `AGENTS.md`：把「自审不能替代独立冷审」扩展为 A/B 级评审必须由独立子代理执行、降级须披露。
- 修改 `video-production-workflow` 主规格：逐场观察复述、全片导演审查、传播反面依据改为默认独立子代理。
- 修改 `reference-style-transfer` 主规格：同族判定改为默认独立子代理。
- 不新增 CLI 命令、运行时字段、自动审美分数或导出门禁；不改 `src/`、`web/`、`examples/`。

## Capabilities

### Added Capabilities

- `independent-subagent-review`：A/B 级评审的隔离执行、评审包、身份证据、降级披露与记录规则。

### Modified Capabilities

- `video-production-workflow`：逐场验收、全片导演审查、传播潜力反面依据的评审执行者改为默认独立子代理，并允许降级披露。
- `reference-style-transfer`：风格同族判定改为默认独立子代理。

## Impact

- 只改创作流程文档、README 与 OpenSpec 规格。
- 不触碰 `videos/`、`work/`、`refs/`；不重新准备、渲染或验收任何作品。
- 参考素材与音轨的默认禁令不变。
- 本次一并提交工作区已有的 `visual-review-rubric.md` 冷审章节与 `AGENTS.md` 画面注释规则；`web/scripts/build-code-scene.mjs` 不属于本次变更。
