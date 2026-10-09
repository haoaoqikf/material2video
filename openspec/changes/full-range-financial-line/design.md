## Context
见 proposal.md。现有金融计划 v4 使用滚动窗口与全貌展开，价格材料已是 v3。

## Goals / Non-Goals
目标：横轴固定全日期范围、历史点累积、已揭示价格动态线性纵轴。此次不改变行情获取与价格口径，不加入事件或 K 线。

## Decisions
- v5 axis 使用 dateScale=full-range 和 valueScale=revealed-linear，移除 visibleWindowMonths 和 overview，防止旧计划静默改变语义。
- 固定 90 帧开场与 120 帧终幕，其余帧均用于 advance；最低时长保持 10 秒。
- 每帧用已到达数据计算极值及 8% 留白，单点使用绝对价格 1%（至少 0.01）半跨度；沿用六帧因果加权范围并用当前范围包络保证新极值不裁切。
- 横轴及年份刻度只取完整 dateRange；报价仍取最近真实交易点。
- 显式迁移备份全部旧材料与评审记录，写入失败回滚；plan 入口拒绝已有旧计划，避免绕过备份。
- 全片评审使用 labelsReadable、advanceTrackable、axisStable、overviewComplete 和 dateAxisFixed；指标记录固定横轴及已揭示线性纵轴。

## Risks / Trade-offs
- 多年跨度早期曲线宽度较小 → 固定稀疏年份标签，完整预演抽检可读性。
- 累积历史极值导致回落后纵轴不收缩 → 保证历史曲线完整，明确自适应提示。

## Migration Plan
用户显式 migrate-line，备份旧材料，生成 v5，作废旧评审及预演记录，重新完整预演；不覆盖成片。失败恢复活动材料。
