# 金融时间序列视频专题

本文定义金融视频的离线制作规范。专题入口独立于文章字数、口播和有声评审流程，行为以 [OpenSpec 专题规格](../../../../openspec/specs/financial-timeseries-video/spec.md) 为准。

## 制作与数据

请求由标的、日期范围及可选投资年份/本金构成。投资年份默认为展示区间首年，本金默认为 100,000 标的计价单位。制作准备阶段核验公开免费行情来源，项目代码不联网抓取行情。股票默认采用仅拆股、合股调整的日收盘价，不计分红再投资；指数采用来源明确的官方点位。保存原始响应快照、来源清单及 SHA-256，预期交易日清单必须与实际价格日期逐项相同。休市日不补报价，交易日数据异常缺失时停止验收。

作品画面不展示股价；投资年份首个真实交易日收盘价作为买入价，以本金/买入价计算持仓比例，之后每个真实日收盘价转换为组合市值。折线及纵轴显示组合价值，顶部显示假设投资标题、大号年份与当前市值；投资起点前显示标题及初始年份，不展示曲线或报价。收益率为收益金额/本金。股票不计分红再投资，所有模拟不计手续费及税费。指数按点位比例模拟且需注明指数不可直接持有。作品不搜索、保存或展示事件，也不包含 K 线或周期选择。价格和计划材料必须使用 `{date, close}` 日线。渲染仅读取本地材料，不联网。

## 材料与编排

作品使用三份材料：`request.json` schema v1、`prices.json` schema v3、`animation-plan.json` schema v8（兼容 v7）。请求标的可选 `instrument.displayName` 作为画面短名称；缺省时显示正式名称，正式名称和代码仍用于标的识别。材料目录不使用 `storyboard.json`，也不进入文章校验入口。

计划明确 `chartType: "line"`、`axis.dateScale: "staged-expanding"` 和 `axis.valueScale: "revealed-linear"`，不接受滚动窗口或固定纵轴范围。默认 60 秒、1080×1920、30 fps、无音轨：开场 3 秒，投资价值推进 51 秒，结果总结停留 6 秒；v7 保留原有 3/53/4 秒和匀速映射。横轴按覆盖自然年份数取 ceil(N / 6) 年步长生成不超过六个阶段，开场显示第一阶段；播放日期将在 15 帧内越过阶段边界时，以 smoothstep 扩展到下一边界。起始日期固定在左侧，曲线、网格和刻度使用同一映射，历史点持续保留。横轴标签按完整日期范围确定不超过四个、不重叠的固定锚点，随着可视范围扩展逐个显现并保持至片尾；后半段保留较晚年份，终幕显示结束年份，避免逐帧重算造成标签闪烁。单年范围直接显示完整日期范围，终幕保持完整横轴和曲线。休市日市值沿用最近真实收盘价推导的组合值，不插值也不提前显示未来价格。

纵轴根据投资起点至当前日期已展示的全部组合价值极值线性自适应，上下各留白 8%。采用六帧因果加权范围并以当前范围包络，保证新极值不裁切；终幕冻结最后推进帧的坐标。历史曲线始终完整，随机寻帧与顺序播放一致。

画面通用文字安全区为 x=64～1016、y=180～1500；纵轴刻度单独允许进入 x=24～1016，纵向范围相同。顶部先显示一条完整单行假设投资标题，按通用安全区宽度适配字号；股票标题说明投资年份、标的和本金但不带币种，指数标题说明按比例投入并跟踪指数。标题下方左侧显示 64 px 大号年份，右侧显示“当前市值”及最大 56 px 的金额，下方用 24 px 显示最近实际收盘日期；年份采用同一收盘日，尚无报价时显示初始年份。数字采用等宽数字样式。推进阶段不显示收益金额和收益率，投资起点前隐藏市值和完整日期。结尾冻结完整曲线和坐标，沿用最后推进帧的年份、当前市值及实际收盘日期并静止停留；不显示本金到最终市值总结或收益率，也不进行淡入。市值使用中文数量级（万、亿、万亿）并以“元”结尾，不显示美元等具体币种名称；底层仍使用原始计价单位，不换汇。正收益时市值和折线为红色，负收益或零收益为绿色。投资价值端点金额继续跟随最新真实收盘点。折线宽 3 px、端点半径 8 px，纵轴刻度 14 px，底部来源和统计口径不大于 24 px。绘图区左边界为 x=92，尽量铺满横向空间；纵轴刻度右对齐于 x=78，标签超出 x=24 左侧安全边界内的可用宽度时水平压缩标签宽度，保持字号。标题、横轴标签、端点金额和底部说明继续遵守 x=64 左安全边界。底部说明区显示去重后的来源主机名、统计口径（仅拆合股调整、不计分红再投资、手续费或税费）以及一行风险提示“过往业绩不代表未来表现。本视频仅作信息展示，不构成投资建议。”；完整来源仍保存在作品材料中。

正式导出前必须针对完整静音预演完成材料绑定评审。评审记录包括预演哈希、材料和构建资产摘要、抽检时间码，以及 `labelsReadable`（标签可读）、`advanceTrackable`（推进可跟随）、`stagedAxisStable`（分阶段扩展稳定）、`axisStable`（坐标稳定）、`overviewComplete`（全貌完整）五项结论及证据。`labelsReadable` 必须实际检查 360×640 缩放画面和安全区，并分别记录证据；只看原尺寸不能通过。评审 metrics 绑定画布、手机检查尺寸和安全区，旧版本记录、短预演及输入变化均不能用于正式导出。

## 波动节奏与计划锚点

v8 的 `pacing` 必须声明 `mode: "volatility" | "uniform"` 和 `anchors: [{frame, date}, ...]`，frame 是全片绝对帧。锚点至少两个，帧严格递增、日期单调，首末必须精确绑定推进首帧和末帧及展示起止日；相邻锚点线性插值，日历日期向下取整，报价只取已到达真实收盘数据。uniform 仅接受首末两个锚点。

新计划默认 volatility：按自然月统计绝对对数收益累计量及组合市值绝对变化累计量，分别除以全区间月最大值，以 40%/60% 组合；权重为 1+2×组合分数，限制为 1～3，按覆盖日数加权分配推进帧。涨跌均可放慢，投资起点前权重为 1，平盘退化为匀速。月边界分配为整数帧，重复帧合并，准确保留首末锚点。节奏可使用全区间行情作为剪辑依据，画面报价及纵轴仍不提前显示未来值。渲染只读取已保存锚点；Python、前端和横轴扩展使用同一映射。不保证每个交易日均有单独画面。

## 显式迁移

v7 仍可读取及渲染，保持旧日期映射和 120 帧结尾；不能用 plan 静默覆盖。已有统一作品使用 `uv run m2v financial migrate-line --project <目录> --duration-seconds 60` 备份后升级 v8；尚无 project.json 的历史作品先使用 `m2v migrate --from financial` 进入统一作品契约，旧 v1～v6 会同时升级 v8，v7/v8 保留原计划。v8 重复升级被拒绝。

迁移前备份请求、价格、计划、旧事件及评审/预演记录；保留 date/close、来源、快照、交易日与截止日，清理过期金融评审。失败恢复活动材料，已有成片不变。升级后必须重新 prepare、完整 preview 和评审。

## 命令

```powershell
uv run m2v init --type financial-timeseries --project videos/<slug>
uv run m2v validate --project videos/<slug>
uv run m2v financial plan --project videos/<slug> --duration-seconds 60
uv run m2v prepare --project videos/<slug>
uv run m2v preview --project videos/<slug>
uv run m2v review-template --project videos/<slug>
# 查看完整预演并填写 outputs/review.json，再通过 review 后正式导出
uv run m2v review --project videos/<slug>
uv run m2v render --project videos/<slug>
# 旧金融材料的迁移使用显式、备份优先的操作；先按当前材料契约核对迁移来源版本
uv run m2v migrate --project videos/<slug> --from financial
```

`init` 仅创建待填模板。价格来源、真实行情、来源快照和日期清单核验完成后再生成计划并运行 `validate`。`--period` 和 `--window-months` 已移除，旧 v1–v6 计划或旧材料必须先运行 `migrate-line` 显式备份迁移。`preview` 不加 `--out` 时写出作品的标准完整预演并登记 `outputs/previews/preview-record.json`，评审模板绑定的是它；带 `--out` 的 `preview` 只是复核/对比用的旁路输出，不会改写已登记的预演记录或已有评审，但也不能作为提交评审的预演。金融视频材料和生成媒体均位于忽略的作品目录或外部内容根中；共享制作方法和规范纳入版本控制。成片与预演经临时目录中转，Windows 上会带上临时目录那份「关闭继承」的 ACL，因此落盘后统一用 `icacls /reset` 重新继承所在目录的权限（必须搬运之后执行，在临时目录里修复只会再套一遍那份收紧的 ACL）；否则以标准权限运行的打包播放器打开交付视频时报 `0x80070005`。预演同样是给人打开的文件，也一并修复。

## 材料形状示例

以下是结构示意，不是可用于制作的完整材料：

```json
{
  "schemaVersion": 1,
  "originalRequest": "假如在 2020 年投入 100 万买入示例公司，投资价值如何变化",
  "instrument": {
    "kind": "stock",
    "name": "示例公司",
    "code": "SAMPLE",
    "market": "NASDAQ",
    "unit": "USD",
    "displayName": "示例公司",
    "listingDate": "1999-01-01"
  },
  "requestedRange": ["2020-01-01", "2020-12-31"],
  "displayRange": ["2020-01-01", "2020-12-31"],
  "investment": {"year": 2020, "principal": 1000000},
  "confirmations": []
}
```

```json
{
  "schemaVersion": 3,
  "unit": "USD",
  "priceBasis": "split-adjusted",
  "adjustmentBaseDate": "2020-12-31",
  "adjustmentDefinition": "仅拆合股调整，不计分红再投资",
  "splitAdjustments": [],
  "expectedTradingDates": ["2020-12-30", "2020-12-31"],
  "expectedTradingDatesSource": ["https://example.invalid/calendar"],
  "points": [
    {"date": "2020-12-30", "close": 100},
    {"date": "2020-12-31", "close": 101}
  ],
  "sources": [{"url": "https://example.invalid/prices", "fetchedAt": "2026-10-05T00:00:00Z", "coverage": ["2020-01-01", "2020-12-31"], "adjustmentDefinition": "拆股调整收盘价"}],
  "rawSnapshots": [{"path": "raw-prices.csv", "sha256": "由原始快照计算的 SHA-256", "sourceUrl": "https://example.invalid/prices"}]
}
```

```json
{
  "schemaVersion": 8,
  "chartType": "line",
  "durationSeconds": 60,
  "fps": 30,
  "canvas": {"width": 1080, "height": 1920},
  "axis": {"dateRange": ["2020-01-01", "2020-12-31"], "dateScale": "staged-expanding", "valueScale": "revealed-linear"},
  "segments": [
    {"frames": [0, 90], "dates": ["2020-01-01", "2020-01-01"], "kind": "opening"},
    {"frames": [90, 1620], "dates": ["2020-01-01", "2020-12-31"], "kind": "advance"},
    {"frames": [1620, 1800], "dates": ["2020-12-31", "2020-12-31"], "kind": "ending"}
  ],
  "pacing": {"mode": "uniform", "anchors": [{"frame": 90, "date": "2020-01-01"}, {"frame": 1619, "date": "2020-12-31"}]},
  "rationale": "60 秒匀速示意；生产默认使用月波动节奏，纵轴随已展示组合价值自适应"
}
```
