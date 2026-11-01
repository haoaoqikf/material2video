## 1. 合并流程文档

- [x] 1.1 把 `creative-production.md` 的项目独有内容并入 `production-workflow.md`：信息单元预算、标题与文案、返工升级、分层精修、减法复核、阶段回归、反馈影响。
- [x] 1.2 把 `creative-production.md` 的声音设计与排查并入 `voice-and-rhythm.md`。
- [x] 1.3 删除 `creative-production.md`，更新所有活动链接。

## 2. 合并评审文档

- [x] 2.1 把 `director-review-and-edit.md` 的 G5/G6、全片逐页检查、剪辑重组、第二次审查与传播评估并入 `visual-review-rubric.md`。
- [x] 2.2 删除 `director-review-and-edit.md`，更新所有活动链接。

## 3. 压缩重复指导

- [x] 3.1 `production-workflow.md` 删除与 `visual-creative-direction.md` 重复的视觉创意方案、导演设计、核心事件观察、减法、静态目标验证与核心事件短循环，改为链接。
- [x] 3.2 `visual-creative-direction.md` 删除七段式模板、十项自检与判断演练，精简通用视觉力量说明，新增五块式 `DESIGN.md` 模板。
- [x] 3.3 `production-examples.md` 删除七段式模板与十项自检，只保留项目特有演练和排错案例。
- [x] 3.4 `explainer-design.md` 把通用构图/色彩/字体/留白判断委托 `frontend-design`，保留讲解特有诊断。

## 4. 阶段指南改为决策表

- [x] 4.1 `stage-plan.md`：要决定什么、写到 DESIGN.md 哪一块、何时读哪个 skill。
- [x] 4.2 `stage-iterate.md`：要验证什么、用什么证据、何时调用两个 skill。
- [x] 4.3 `stage-final.md`：要接受什么、G5/G6 与问题关闭、何时使用两个 skill 观察。

## 5. 路由与入口

- [x] 5.1 `guidance-routes.json` 删除已删除文档的路由，迁移到新权威锚点。
- [x] 5.2 `SKILL.md`、README、ARCHITECTURE、AGENTS 更新文档导航与权威说明。
- [x] 5.3 示例 `DESIGN.md` 链接指向新的五块式模板或视觉创意方法。

## 6. 测试与验证

- [x] 6.1 更新 `test_doc_examples.py` 的可达文档、链接来源与示例链接断言。
- [x] 6.2 更新 `test_guidance_routes.py` 的锚点与预算断言（如涉及）。
- [x] 6.3 运行 `sync_docs.py --check`、`uv run pytest`、`openspec validate --all`。
- [x] 6.4 检查暂存内容，只提交本变更相关文件。
- [x] 6.5 归档并同步 OpenSpec 主规格。
