## 1. 诊断表与形象判据

- [x] 1.1 新建 `references/visual-diagnosis.md`：症状→成因→改法三列表（覆盖规格列出的十一类症状），标注改法层级；验证 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` 通过且相对链接可解析。
- [x] 1.2 在同一文件写入「画得像它本身」四条判据与主体尺度设计期起点（占宽比例、最小可辨单元），并说明与 `reference-style.md` 事后量测的分工；验证判据能对「圆圈加标签」「一串光点」「题材本身是文字」三种情形给出明确结论。
- [x] 1.3 在 `references/guidance-routes.json` 登记 `visual-diagnosis` 条件路由（触发条件：看图发现画面问题、判断形象是否成立、确定主体尺度时）；验证 `uv run pytest tests/test_guidance_routes.py -q` 通过。

## 2. 阶段指南接入

- [x] 2.1 `references/explainer-design.md` 的看图改图检查表改为转介 `visual-diagnosis.md` 并保留可自查摘要；补「先找形象、再写文案」顺序说明；验证检查表条目没有丢失、链接锚点存在。
- [x] 2.2 `references/stage-plan.md` 增加顺序约束：形象清单与分镜表未完成不建工程、不写场景代码；验证该阶段指南字符数 ≤3000 且入口加阶段 ≤5000。
- [x] 2.3 `references/stage-rough.md` 增加开场段落闸（先渲开头、过判据与诊断、留存证据再铺全片），写明不新增用户审批；验证字符预算并确认未与 `checkpoint-gates.md` 的审核轮次冲突。
- [x] 2.4 `references/stage-final.md` 并入八类终检门槛表，并声明冲突时以检查点契约为准；验证字符预算与既有「独立评审」表述一致。

## 3. 收敛可见变化定义

- [x] 3.1 确认 `references/visual-creative-direction.md` 为唯一权威定义，逐一改写其余五处（`creative-production.md`、`production-workflow.md`、`article-to-storyboard.md`、`explainer-design.md`、`scene-design-and-acceptance.md`）为转介加一句可自查结论；保留 `explainer-design.md` 与 `visual-review-rubric.md` 的使用点勾选项。
- [x] 3.2 验证规则未丢失：逐条核对被改摘要的结论都能在权威定义中找到对应原文；`uv run pytest tests/test_doc_examples.py tests/test_guidance_routes.py -q` 与 `uv run python .agents/skills/material2video/scripts/sync_docs.py --check` 全部通过。

## 4. 验证与交付

- [x] 4.1 运行完整文档回归（`sync_docs.py --check`、`test_doc_examples.py`、`test_guidance_routes.py`），确认预算 entry≤2000、stage≤3000、合计≤5000；修复后复查。
- [x] 4.2 检查暂存范围并提交实施；随后同步 `openspec/specs/` 主规格、移入 `openspec/changes/archive/2026-10-28-strengthen-explainer-visual-diagnosis/` 并提交归档。
