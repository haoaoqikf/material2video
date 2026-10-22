## 1. 规范与设计

- [x] 1.1 记录提案与设计，明确只改流程文档与规格。
- [x] 1.2 新增 `independent-subagent-review` 规格：A/B 清单、评审包、匿名化、身份证据、输出模板、降级、记录与不适用。
- [x] 1.3 修改 `video-production-workflow`：逐场观察复述、导演审查、传播反面依据。
- [x] 1.4 修改 `reference-style-transfer`：同族判定。

## 2. 文档

- [x] 2.1 新增 `references/subagent-review.md`。
- [x] 2.2 修改 `SKILL.md` 编排原则与渲染评审。
- [x] 2.3 修改 `creative-production.md` 候选淘汰、美术方向、复述关、导演审查。
- [x] 2.4 修改 `scene-design-and-acceptance.md` 逐场观察复述。
- [x] 2.5 修改 `director-review-and-edit.md` 两次审查与记录。
- [x] 2.6 修改 `reach-potential.md` 反面依据。
- [x] 2.7 修改 `reference-style.md` 同族判定。
- [x] 2.8 修改 `article-to-storyboard.md`、`production-workflow.md`、`visual-review-rubric.md`、`AGENTS.md`、`README.md`。

## 3. 测试

- [x] 3.1 更新 `tests/test_doc_examples.py`，断言新文档的关键条款，保留「角色分离自审」。
- [x] 3.2 运行文档相关 pytest 子集。
- [x] 3.3 运行 `sync_docs.py --check`。

## 4. 验证与提交

- [x] 4.1 检查相对链接、锚点与表格列数。
- [x] 4.2 检索术语，确认不再出现「不要求新增代理」作为默认口径。
- [x] 4.3 检查暂存范围，不夹带 `web/scripts/build-code-scene.mjs`。
- [x] 4.4 提交并同步主规格、归档本变更。
