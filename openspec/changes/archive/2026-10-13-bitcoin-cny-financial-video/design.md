## Context

金融材料当前通过 `financial.py` 校验 request v1 / prices v3，并由 Python 计划器与 Remotion 组件各自派生投资序列。既有股票、指数不含换汇。详见 `proposal.md` 与本变更规格。

## Goals / Non-Goals

**Goals:** 精确支持 BTC/USD 日线按指定日期买入，并将每帧展示价值转换为 CNY；可追溯行情和汇率输入；在安全区内显示起点说明。

**Non-Goals:** 不联网渲染、不为 BTC 添加实时交易入口、不改股票和指数的计算口径、不将真实视频内容纳入 Git。

## Decisions

- 保持 request schema v1 的既有股票/指数形状；BTC 使用 `instrument.kind: "crypto"`、`investment.date`、`investment.principal`、`investment.currency: "CNY"` 和可选 `investment.startRationale`。股票和指数继续使用 `investment.year`。
- 保持 prices v3 给股票/指数读取；BTC 使用 prices v4，含逐 UTC 日 `{date, close}` BTC/USD 点、`priceBasis: "crypto-spot-close"`、汇率 `{date, close}` 点（单位 CNY/USD）及各自独立的来源、快照、SHA-256 和日期核验记录。汇率按“当日或此前最近可用点”对齐 BTC 日期，禁止前向填充。
- 保持 plan v8，Python 与 TypeScript 共享同一公式：本金 × BTC 当日 close/买入日 close × 对齐后 CNY/USD 汇率/买入日对齐汇率。新增纯函数供计划节奏和前端使用相同派生值；渲染输入摘要包含其依赖文件。
- 使用用户已确认的 2011-05-01 BTC/USD 收盘 $3.60。FRED DEXCHUS 是纽约中午买入汇率且为工作日序列；周末和假日使用此前观测。起点文案说明采用全月回顾成交量，明确该数不是起点当日盘口深度且可能有滑点。
- 将 `investment.startRationale` 放在图表后、既有统计口径前，以 18px 小字、最多两行显示；现有统计口径与最多两行风险提示保留。内容组自动垂直居中与现有逐帧布局探针适用于新增说明；不够容纳时阻断。
- 先创建空白金融作品，再离线写入已核验材料；所有来源快照存作品目录。金融渲染、预演和正式导出仅读取已保存材料。

## Risks / Trade-offs

- [BTC 历史报价可能因供应商/UTC 日界口径而异] → 固定单一历史日线来源和快照，并交叉核对 2011-05-01 收盘与近端日期；旁车与材料记录口径。
- [历史汇率不是周末实时可成交报价] → 使用 FRED 发布的最新此前工作日纽约中午汇率，并在统计口径与作品旁车明确回填规则。
- [起点说明可能挤压画面高度] → 使用 18px、限制两行并纳入布局探针；失败时调整现有区域排布，不隐藏风险说明。
- [资产价格覆盖区间很长] → Python 与前端保持 O(n) 序列派生并缓存；计划生成只扫描历史点一次，逐帧仅二分查找当前点。

## Migration Plan

不修改或迁移既有材料。prices v3 与投资年份行为持续兼容；prices v4 只供 crypto 使用。BTC 作品通过统一金融入口 validate → prepare → 完整 preview 自动验收 → render。验证与提交成功后同步主规格并归档 OpenSpec 变更，再提交归档结果。
