# 验证与审查

- `uv run pytest tests/common/test_guidance_routes.py -q`：21 项通过；pytest 缓存写入权限警告不影响测试执行。
- `uv run python .agents/skills/material2video/scripts/sync_docs.py --check`：通过；入口 1868 字符，plan 2265、iterate 2974、final 2360，均在既有预算内。
- `openspec validate add-scene-detail-design --strict`：通过。
- 9 份受影响入口/设计文档的 220 个本地链接与锚点检查通过；新增参考所含链接已检查。JSON 阅读路由由相关测试解析验证。
- 逐项核对 compound-connect 的 hook/proof/resolution 源码：仅补写已有行为，并明确其无加速表格、无柱体回弹和持续球顶联动；未改示例代码或媒体。

审查结论：无必改缺陷。方法归属运动适配，流程页负责记录与证据，三阶段、审核职责与参数源保持单一。无运行时、材料格式或渲染字段变化，故不增加运行时校验；现有文档导航与预算校验覆盖接线。性能与成片行为无变化；后续作品仍须用实际动态证据验证，文档检查不证明审美效果。未运行全仓回归，未重渲已有示例。本次为文档与流程审查，不作代码质量评分。
