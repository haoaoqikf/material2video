# 任务：把动效量测搬进验收流程

## 1. 抽出可复用模块

- [x] 1.1 新增 `scripts/a2v/motion.py`：扫描脚本、入场判定、四条判据、汇总与 JSON 落盘。
- [x] 1.2 `AnimatedPage.evaluate` 支持可选参数（逐幕传起始帧与帧数），未传时行为不变。
- [x] 1.3 `tests/test_motion_trajectory.py` 改为调用模块，删掉自带的第二份扫描实现。
- [x] 1.4 给「被采样上限截断的入场」单独留字段并报进 M0，不允许静默丢掉。

## 2. 接进验收流程

- [x] 2.1 `inspect.run_inspect` 在抽帧之后跑一次动效量测，结果进 `report.json` 的 `motion` 段。
- [x] 2.2 `cli._review_summary` 增加「动效量测 M0–M4」一栏（通过项也列实测值，未通过项列原因）。
- [x] 2.3 跳过时如实给出理由（没有场景 / 场景没声明帧数），终端照实打印「不适用——…」。
- [x] 2.4 动效闸门不改错误数与退出码，并在代码注释里写明为什么（与 K 系列同性质）。

## 3. 测试

- [x] 3.1 新增 `tests/test_motion_review.py`：入场判定（全不透明/刻意压暗/幕中创建都不算）、
  四条判据在构造的轨迹上确实会失败、跳过要有理由、JSON 载荷带全部入场。
- [x] 3.2 截断判据的正反例：单调上升被截断要报；停在部分不透明度、脉动、已落地都不报。
- [x] 3.3 参考实现的严格判定与反例保持通过（改调用模块后 12 项全绿）。

## 4. 端到端验证与文档

- [x] 4.1 实跑 `review.py`：基准示例、`examples/why-effort-fails`、`videos/never-fear-interviews`
  三份 `report.json` 都带 `motion` 段，终端都打印 M0–M4。
- [x] 4.2 README 的动效条目补上「验收时会跑、闸门只提示不拦人」。
- [x] 4.3 `docs/PROJECT_PLAN.md` 把这一步从开放项移入已实现，并更新仍开放的边界。
- [x] 4.4 参考文档（`references/visual-spec.md`）指明验收命令会给出动效结论。
- [x] 4.5 全量 `uv run pytest` 通过；基准示例 C 系列与 K 系列结论与改动前一致。
