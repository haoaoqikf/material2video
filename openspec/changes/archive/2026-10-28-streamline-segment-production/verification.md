# 验证与审查

## 实施范围

general 制作在既有三阶段内改为「先做一个最小完整段落试制，再逐段扩展」。试制在方案确定时选定，同一份可编辑材料依次完成连续构图 → 动态实现 → 检查与修改 → 适用独立复查，通过后保留为正式作品的一部分；每段先定内容边界，再在原时间线上安排阅读、动作、结果观察与下一句。全片粗片与最终验收职责保持不变。

规则只在 `production-workflow.md` 的「完整段落试制与逐段扩展」定义一次；`stage-plan.md`、`stage-iterate.md`、`explainer-design.md`、`scene-design-and-acceptance.md` 与 `README.md` 只作摘要并回链，未新增阶段、表单、JSON 字段、CLI 门禁或逐段审核轮。

## 验证

- 定向回归 107 项通过：`test_guidance_routes.py`、`test_doc_examples.py`、`test_production_gates.py`、`test_production_sources.py`、`test_media_evidence.py`（`PYTHONUTF8=1`）。
- 全量非慢速回归 926 项通过、5 项跳过、50 项按 `slow` 排除（`PYTHONUTF8=1 uv run pytest -m "not slow"`）。不加 `PYTHONUTF8=1` 时示例与语音用例会在夹具收尾抛出 `UnicodeDecodeError`，原因是 Windows 控制台以 GBK 输出被 pytest 捕获层按 UTF-8 读取，单独运行这些文件均通过，与本次改动无关。
- `sync_docs.py --check` 通过：入口 1419、方案 1434、制作与迭代 1791、最终 1267 字符；入口加当前阶段 3210，低于 5000 上限。
- 新增与改动的 Markdown 相对链接及锚点全部可解析，含 `production-workflow.md#完整段落试制与逐段扩展`、`#每段完成一个关系`、`checkpoint-gates.md#门三阶段与审核轮`。
- OpenSpec 变更 strict 校验通过。
- 独立只读审查对照权威契约逐项核对覆盖不足、目标关键帧、复用隔离、G5/G6 职责与文档唯一权威，未发现阻塞缺陷；其提出的 4 项一般问题已在提交前修正。

## 审查结论与限制

独立审查确认三阶段、G4–G6、审核人数与隔离要求、`static-expression` 独立目标关键帧及盲审、复用材料不继承通过均未被削弱。修正的 4 项：

- G5 覆盖曾在本节另列一套口径 —— 改为回链检查点契约，不在本节缩小或扩大覆盖；
- 新增试制与既有「核心事件短循环」未衔接 —— 明确 `core-event` 风险时沿用小节的完整窗口、预声明条件与时间容差，低成本粗样是同一材料的前一版；
- 「不要求固定张数」可能被读成取消四张叙事基准 —— 明确基准仍按原规则单独制作；
- 阅读／动作／结果顺序曾被读作统一顺序 —— 明确为默认节奏，字幕晚半拍与结论后置按表达需要。

同时清理了与三阶段冲突的旧阶段语汇：`README.md` 的「全片粗片在精制前」、`creative-production.md` 的「粗片活动」、`visual-review-rubric.md` 的「粗片阶段」。

无渲染路径、分镜结构、材料格式或音视频输出改变，因此未重新生成媒体、未跑前端构建，也未重跑无关整仓用例。

## 主规格与归档

已同步 `openspec/specs/video-production-workflow/spec.md`：修改「制作与迭代必须按问题闭环并复用有效证据」，新增「完整段落试制必须覆盖表达并支持逐段扩展」；其余需求未改。归档保留提案、设计、任务、规格与本记录。
