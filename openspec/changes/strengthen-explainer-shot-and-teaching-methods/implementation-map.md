# 实施映射与现状

核对时间：2026-10-29。`add-vibe-night-style-pack` 仍有独立作品和审核未完成项，本变更不代其关闭；`unify-example-outputs` 正在修改固定示例输出路径，避免覆盖其工作。两套风格、Painter 相机、全局时间、幕内事件和 fold 原布局生成器均已存在。

| 方法 | 实施位置 | 核心窗口或证据 |
|---|---|---|
| 镜头连接 | explainer-design、两个示例设计 | fold 的珠链／细胞／回场，pigeon 的计时器／角色／计时器完整窗口 |
| 时间预算 | explainer-design、两个示例设计 | 建立、阅读、观察、消化的实际区间与独立观察 |
| 共同尺度 | pigeon 场景与分镜、fable GUIDE | 15 秒时钟，取消无依据量值；不得声称多案例验证 |
| 几何生成 | fold 生成器与布局测试 | 146 颗、索引 5、邻接和接合，失败不覆盖 |
| 修改教学 | 两个 HOWTO 与 README | 临时副本四项练习及相关命令 |
| 分层验收 | visual-review-rubric、两个 GUIDE、验证摘要 | 同候选技术 QA、独立完整窗口与粗片终审分别报告 |

旧成片与分镜副本保存在各示例 `outputs/pre-change-baseline/`，但两段旧成片已被候选渲染的交付清理移除，现存只有 `pigeon.tsx`、`pigeon/storyboard.json`、`fold.tsx`、`fold/storyboard.json` 源码基线。本轮改用这些源码在临时副本中重新渲染对照粗样；基线只用于比较，不代表候选已通过。这次清理也说明旧成片不能依赖 `outputs/` 长期保存，比较前须先移出。

## 四项练习的执行结果（2026-10-29，临时副本）

| 练习 | 实际修改 | 验证结果 |
|---|---|---|
| pigeon 事件调时 | `wander.turn-1.frame` 135→132 | 事件与 `swish` 同移到全片 402 帧（13.4s）；`feeder-open-1` 仍为 450 帧（15.0s），`feeder-open-2` 仍为 900 帧（30.0s），`feed-2-arrival` 仍为 906 帧（30.2s）；字幕窗口未自动联动 |
| pigeon 取景 | `SHOTS.wander.to.focus` `[1200,555]`→`[1180,555]` | `validate`/`prepare` 通过，`lookdev --motion 8.0 10.5` 中房间、鸽子、食槽与计时器仍可认回；字幕未遮挡主体 |
| fold 相机 | `CAM` 关键帧 `at: 9.15`→`9.3` | `validate`/`prepare` 通过，8.0–10.5s 转场样片中拉远稍晚，突变珠子与细胞全貌仍连续可认 |
| fold 布局 | `gen_layout.py --seed 2` | 146 颗、索引 5 仍为 knob `(6,0)`、`pitch < 2R`；`validate`/`prepare` 通过，折叠与接合画面正常；`--seed 0` 明确失败且 `layout.json` 摘要不变 |

练习均在系统临时目录执行，未修改仓库内作品，未提交变体或媒体。
