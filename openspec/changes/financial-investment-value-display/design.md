## Context

金融专题目前 request 只含标的和日期范围；React composition 的所有价格坐标直接映射 close。制作入口 Python 校验 request、价格与 v7 动画计划，渲染 props 将材料传给 composition。

## Goals / Non-Goals

- 在现有本地、确定性日线渲染链路上计算假设投资价值。
- 保持价格材料与来源不变，只改变画面指标及纵轴所表达的值。
- 暂不实现分红再投资、手续费、税费、外币兑换或指数投资份额语义。

## Decisions

- request v1 增加 `investment: { year, principal }`，缺省 year 为 displayRange 首年，principal 为 1,000,000；计价单位复用 instrument.unit。
- 股票买入点取 investment.year 内第一个真实价格点；若该年没有可用点则拒绝材料。指数按相同份额算术作为假设点位单位投资。
- 所有可见点从买入日开始转换为 `principal * close / buyClose`；端点派生市值、盈亏及收益率。用转换后的可见点计算因果平滑纵轴。
- 数值轴刻度保留，但格式化为标的计价币种的组合金额；不展示任何股价 close。端点与市值同步定位。
- 底部注释由去重来源主机和投资计算口径组成；完整来源仍留在材料。
- 投资年份不在展示范围时校验失败；起投日前无收益线和指标。

## Risks / Trade-offs

- 拆股调整收盘价跨拆股保持可比，但结果明确不包含股息收益；说明区标注该限制。
- 1,000,000 USD 等金额占据更多竖屏空间，需要压缩顶部层级并用安全区预演验收。

## Migration

- 旧 request 在读取时按缺省投资参数解释，不改写原始真实作品材料；下一次 init 生成完整投资字段。
- 金融 composition props 增加投资参数，项目内 financial render builder 是唯一赋值入口。
