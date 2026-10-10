# 金融时间序列视频专题

本文定义金融视频的离线制作规范。专题入口独立于文章字数、口播和有声评审流程，行为以 [OpenSpec 专题规格](../../../../openspec/specs/financial-timeseries-video/spec.md) 为准。

## 制作与数据

请求由标的、日期范围及可选投资年份/本金构成。投资年份默认为展示区间首年，本金默认为 1,000,000 标的计价单位。制作准备阶段核验公开免费行情来源，项目代码不联网抓取行情。股票默认采用仅拆股、合股调整的日收盘价，不计分红再投资；指数采用来源明确的官方点位。保存原始响应快照、来源清单及 SHA-256，预期交易日清单必须与实际价格日期逐项相同。休市日不补报价，交易日数据异常缺失时停止验收。

作品画面不展示股价；投资年份首个真实交易日收盘价作为买入价，以本金/买入价计算持仓比例，之后每个真实日收盘价转换为组合市值。折线及纵轴显示组合价值，顶部只显示假设投资标题和实时收益金额/收益率；投资起点前只显示标题，不展示曲线或收益数据。收益率为收益金额/本金。股票不计分红再投资，所有模拟不计手续费及税费。指数按点位比例模拟且需注明指数不可直接持有。作品不搜索、保存或展示事件，也不包含 K 线或周期选择。价格和计划材料必须使用 `{date, close}` 日线。渲染仅读取本地材料，不联网。

## 材料与编排

作品使用三份材料：`request.json` schema v1、`prices.json` schema v3、`animation-plan.json` schema v7。请求标的可选 `instrument.displayName` 作为画面短名称；缺省时显示正式名称，正式名称和代码仍用于标的识别。材料目录不使用 `storyboard.json`，也不进入文章校验入口。

计划明确 `chartType: "line"`、`axis.dateScale: "staged-expanding"` 和 `axis.valueScale: "revealed-linear"`，不接受滚动窗口或固定纵轴范围。默认 60 秒、1080×1920、30 fps、无音轨：开场 3 秒，投资价值推进 53 秒，完整曲线停留 4 秒。横轴按覆盖自然年份数取 ceil(N / 6) 年步长生成不超过六个阶段，开场显示第一阶段；播放日期将在 15 帧内越过阶段边界时，以 smoothstep 扩展到下一边界。起始日期固定在左侧，曲线、网格和刻度使用同一映射，历史点持续保留。扩展期间保留旧刻度间隔，新刻度在进入视野时淡入，扩展后交叉淡化到新稀疏刻度；竖屏至多显示四个按实际标签宽度避让的横轴标签。单年范围直接显示完整日期范围，终幕 4 秒保持完整横轴和曲线。休市日市值沿用最近真实收盘价推导的组合值，不插值也不提前显示未来价格。

纵轴根据投资起点至当前日期已展示的全部组合价值极值线性自适应，上下各留白 8%。采用六帧因果加权范围并以当前范围包络，保证新极值不裁切；终幕冻结最后推进帧的坐标。历史曲线始终完整，随机寻帧与顺序播放一致。

画面采用安全区 x=64～1016、y=180～1500。顶部仅显示一条假设投资标题及实时收益金额/收益率；股票标题说明投资年份、标的和本金，指数标题说明按比例投入并跟踪指数。投资起点前只显示标题。正收益时收益金额、收益率和投资价值折线为红色；收益为负或零时三者为绿色。投资价值端点金额继续跟随最新真实收盘点。折线宽 4 px、端点半径 8 px，纵轴刻度不大于 22 px，底部来源和统计口径不大于 24 px。绘图区横向尽量铺满安全区，所有实际文字和端点均须处于该安全区。底部唯一说明区只呈现去重后的来源主机名和统计口径（仅拆合股调整、不计分红再投资、手续费或税费）；完整来源仍保存在作品材料中。

正式导出前必须针对完整静音预演完成材料绑定评审。评审记录包括预演哈希、材料和构建资产摘要、抽检时间码，以及 `labelsReadable`（标签可读）、`advanceTrackable`（推进可跟随）、`stagedAxisStable`（分阶段扩展稳定）、`axisStable`（坐标稳定）、`overviewComplete`（全貌完整）五项结论及证据。`labelsReadable` 必须实际检查 360×640 缩放画面和安全区，并分别记录证据；只看原尺寸不能通过。评审 metrics 绑定画布、手机检查尺寸和安全区，旧版本记录、短预演及输入变化均不能用于正式导出。

## 显式迁移

旧 OHLC 价格材料及旧 v3/v4/v5/v6 动画计划不得直接渲染或用 `plan` 覆盖。运行 `migrate-line`：验证旧材料后只提取原有 `close`，保留日期、价格口径、来源、原始快照和交易日清单，将 v1/v2 价格规范为 v3，并将旧计划更新为 v7；v7 重复迁移会被拒绝。迁移前完整备份请求、价格、计划、旧事件及评审/预演记录（如有），成功后清除活动旧事件和过期评审记录；失败恢复活动材料。迁移不刷新行情截止日、不覆盖已有成片，完成后必须重新完整预演与评审。

## 命令

```powershell
uv run python .agents/skills/article2video/scripts/financial_video.py init `
  --out-dir videos/<slug> --kind stock --name <公司名> --code <证券代码> `
  --display-name <画面短名称> `
  --market <市场> --unit USD --listing-date YYYY-MM-DD `
  --start-date YYYY-MM-DD --end-date YYYY-MM-DD

# 将旧材料显式迁移到收盘价折线契约
uv run python .agents/skills/article2video/scripts/financial_video.py migrate-line --project-dir videos/<slug> --duration-seconds 60
uv run python .agents/skills/article2video/scripts/financial_video.py plan --project-dir videos/<slug> --duration-seconds 60
uv run python .agents/skills/article2video/scripts/financial_video.py validate --project-dir videos/<slug>
uv run python .agents/skills/article2video/scripts/financial_video.py preview --project-dir videos/<slug> --limit-frames 120
uv run python .agents/skills/article2video/scripts/financial_video.py preview --project-dir videos/<slug>
uv run python .agents/skills/article2video/scripts/financial_video.py review-template --project-dir videos/<slug>
# 实际查看完整预演，填写 outputs/legibility-review.json 的结论与证据，再正式导出
uv run python .agents/skills/article2video/scripts/financial_video.py render --project-dir videos/<slug> --out videos/<slug>/outputs/financial-line.mp4
```

`init` 仅创建待填模板。价格来源、真实行情、来源快照和日期清单核验完成后，先运行 `validate`。`--period` 和 `--window-months` 已移除，旧 v3–v6 计划或旧材料必须先运行 `migrate-line` 显式备份迁移。`preview` 不加 `--out` 时写出作品的标准完整预演并登记 `outputs/previews/preview-record.json`，评审模板绑定的是它；带 `--out` 的 `preview` 只是复核/对比用的旁路输出，不会改写已登记的预演记录或已有评审，但也不能作为提交评审的预演。金融视频材料和生成媒体均位于忽略的作品目录或外部内容根中；共享制作方法和规范纳入版本控制。成片与预演经临时目录中转，Windows 上会带上临时目录那份「关闭继承」的 ACL，因此落盘后统一用 `icacls /reset` 重新继承所在目录的权限（必须搬运之后执行，在临时目录里修复只会再套一遍那份收紧的 ACL）；否则以标准权限运行的打包播放器打开交付视频时报 `0x80070005`。预演同样是给人打开的文件，也一并修复。

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
  "schemaVersion": 7,
  "chartType": "line",
  "durationSeconds": 60,
  "fps": 30,
  "canvas": {"width": 1080, "height": 1920},
  "axis": {"dateRange": ["2020-01-01", "2020-12-31"], "dateScale": "staged-expanding", "valueScale": "revealed-linear"},
  "segments": [
    {"frames": [0, 90], "dates": ["2020-01-01", "2020-01-01"], "kind": "opening"},
    {"frames": [90, 1680], "dates": ["2020-01-01", "2020-12-31"], "kind": "advance"},
    {"frames": [1680, 1800], "dates": ["2020-12-31", "2020-12-31"], "kind": "ending"}
  ],
  "rationale": "60 秒分阶段扩展横轴编排，纵轴随已展示组合价值自适应"
}
```
