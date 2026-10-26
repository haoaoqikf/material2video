# 实施边界与验证记录

记录时间：2026-10-27。

## 与在制无声视频任务的交接

工作树同时存在 `produce-us-top10-market-cap-silent-video` 的改动。本变更只修改审核策略、v2 合同、检查/评审/台账与对应文档；无声视频任务的素材优先级、无声输出、初始化画幅与 audio policy 改动不并入本次提交。

共享文件按 hunk 分离暂存：

| 文件 | 本变更范围 | 另一任务范围 |
|---|---|---|
| `README.md` | 审核轮次、G0–G6 与 v2 合同描述 | 素材优先级、静音无音轨、初始化画幅 |
| `.agents/skills/material2video/SKILL.md` | 四阶段审核、许可证与提交边界 | 素材优先级段落 |
| `references/production-workflow.md` | 三轮审核、风险触发、设计对照、两问降级为诊断 | 「运动载体优先级」段落 |
| `references/visual-review-rubric.md` | 审核轮次、门禁位置 | 载体选择默认顺序 |

其余本变更文件（`AGENTS.md`、`checkpoint-gates.md`、`subagent-review.md`、`director-review-and-edit.md`、`scene-design-and-acceptance.md`、`creative-production.md`、`visual-creative-direction.md`、`visual-impact-design.md`、`video-revision.md`、`article-to-storyboard.md`、`reach-potential.md`、`reference-video-analysis.md`、`src/m2v/production/`、`tests/test_production_gates.py`、三个示例合同与演练）整体暂存。

## 旧合同与用户硬要求

- 旧合同 v1 使用 `structureRisk` 与可选 `acceptanceChecks`；本次明确拒绝，不自动迁移。
- 旧流程固定 G2 逐核心检查点关键帧、G3 animatic、G4 A 级独立评审、G5 批量回绑、G6 两名固定终审与五维三方凭据；本次改为审核计划派生。
- 用户既有硬要求（无声成片、画幅、时长、事实与许可边界）不在本变更内调整；示例合同只记录当前 v2 结构，不重制视频、不伪造历史评审。

## 验证

- `pytest tests/test_production_gates.py`：通过（含策略表驱动、v2 拒绝旧字段、覆盖表、多门绑定、终审新代理、blind→consistency 顺序）。
- `pytest tests/test_production_gates.py tests/test_optional_visual_review.py tests/test_input_review_cli.py tests/test_project_cli.py tests/test_general_type.py -m "not slow"`：81 项通过。
- `pytest tests/test_examples_strict.py tests/test_type_catalog.py tests/test_styles.py`：通过。
- 三个示例 `contract.load` 与 `contract.mapping`：通过。
- `sync_docs.py --check`：通过。
- 相关 Markdown 相对链接：仓库文档无断链；示例 `outputs/` 产物中的 3 个历史链接断链，不属于版本控制文档。
- 全量测试在单进程一次运行时出现与本次改动无关的终端解码错误；按文件分组运行通过，已在上方分别记录。

## 未完成项

- 4.3 太阳系真实核心窗→粗片→最终独立审查闭环：未执行。示例是已交付的历史作品，其设计文档明确「非重制记录」；当前合同刚升级 v2，重跑会覆盖历史评审并需要重新渲染/浏览器取证，超出不伪造、不覆盖历史的要求。环境具备子代理，但缺少可合法写入的当前制作周期与用户重制授权，故保持未完成并披露。
