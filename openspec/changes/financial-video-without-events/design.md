## 设计

将独立金融作品输入收敛为 `request.json`、`prices.json` 和 `animation-plan.json`。计划 schemaVersion 升为 4，价格点仍为 v3 的 `{date, close}`。

计划固定由四个连续帧段构成：opening 90 帧、advance（60 秒作品为 1530 帧）、overview 60 帧和 ending 120 帧。advance 从展示起始日推进到终日；单日范围允许日期不变。取消 hold 与 eventDisplays。

校验、预演属性和 composition 移除 events 输入。评审绑定三类材料、渲染构建输入及金融 Python 代码，保留标签、滚动、坐标和全貌四项检查。旧 v1/v2 价格及 v3 计划只能经 migrate-line 显式迁移；仅拆取 close，价格来源与快照继续验证。

Nvidia 迁移中从活动材料及历史备份删除事件资料和事件计划副本，保留请求、价格与原始快照；删除所有旧视频、预演、检查图和渲染缓存，完成新预演评审与导出后只保留新版成片及完整预演记录。
