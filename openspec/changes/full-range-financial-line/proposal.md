## Why
滚动窗口会隐藏早期历史，用户希望从开头看见完整年份布局，并随已揭示股价调整纵轴。

## What Changes
- 固定完整日期横轴，逐日揭示并保留历史曲线。
- **BREAKING**：计划升级 v5，移除滚动窗口及 overview 阶段；旧计划显式备份迁移。
- 默认 3 秒开场、53 秒推进、4 秒终幕，更新完整预演评审。

## Capabilities
### New Capabilities
无。
### Modified Capabilities
- `financial-timeseries-video`：固定全范围横轴、已揭示数据动态纵轴、v5 编排和迁移。

## Impact
金融 Python 计划与 CLI、React composition、测试、制作手册和 README；无新依赖，作品不入库。
