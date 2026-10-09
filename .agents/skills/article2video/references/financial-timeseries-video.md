# 金融时间序列视频专题

本文定义金融视频的离线制作规范。专题入口独立于文章字数、口播和有声评审流程，行为以 [OpenSpec 专题规格](../../../../openspec/specs/financial-timeseries-video/spec.md) 为准。

## 制作与数据

请求由标的和日期范围构成。制作准备阶段核验公开免费行情来源，项目代码不联网抓取行情。股票默认采用仅拆股、合股调整的日收盘价，不计分红再投资；指数采用来源明确的官方点位。明确价格口径、覆盖范围、市场日期、币种或点位单位。保存原始响应快照、来源清单及 SHA-256，预期交易日清单必须与实际价格日期逐项相同。休市日不补报价，交易日数据异常缺失时停止验收。

作品只展示真实日收盘价折线，不搜索、保存或展示事件，也不包含 K 线或周期选择。价格和计划材料必须使用 `{date, close}` 日线。渲染仅读取本地材料，不联网。

## 材料与编排

作品使用三份材料：`request.json` schema v1、`prices.json` schema v3、`animation-plan.json` schema v4。材料目录不使用 `storyboard.json`，也不进入文章校验入口。

计划明确 `chartType: "line"`、可见窗口月数、线性自适应纵轴、画布、帧率和连续半开帧段。默认 60 秒、1920×1080、30 fps、无音轨：开场 3 秒，行情推进 51 秒，终日展开全历史 2 秒，全貌停留 4 秒。滚动阶段显示最近 12 个日历月，横轴连续向左移动，新数据从右侧进入；月末回退截短至目标月有效末日。日期和报价按真实日线推进，休市日保持上一有效收盘价所属日期，绝不生成插值报价或提前显示未来价格。

滚动阶段纵轴对窗口内真实收盘值线性自适应。最后 2 秒同步过渡横轴、纵轴和曲线至完整历史；全貌使用线性纵轴与稀疏年份刻度。画面始终标明当前日期窗口和纵轴自适应提示。动画按帧确定，随机寻帧和顺序播放结果一致。

正式导出前必须针对完整静音预演完成材料绑定评审。评审记录包括预演哈希、材料和构建资产摘要、抽检时间码，以及标签可读、滚动可跟随、坐标稳定、全貌完整四项结论及证据。短预演不构成正式评审；输入变化会令评审失效。

## 显式迁移

旧 OHLC 价格材料及旧动画计划不得直接渲染。使用 `migrate-line` 显式迁移：验证旧材料后只提取原有 `close`，保留日期、价格口径、来源、原始快照和交易日清单，将计划更新为 v4；旧评审作废。迁移完成后，三份当前材料才能用于校验和渲染。迁移不会自动刷新行情截止日。

## 命令

```powershell
uv run python .agents/skills/article2video/scripts/financial_video.py init `
  --out-dir videos/<slug> --kind stock --name <公司名> --code <证券代码> `
  --market <市场> --unit USD --listing-date YYYY-MM-DD `
  --start-date YYYY-MM-DD --end-date YYYY-MM-DD

# 将旧材料显式迁移到收盘价折线契约
uv run python .agents/skills/article2video/scripts/financial_video.py migrate-line --project-dir videos/<slug> --duration-seconds 60 --window-months 12
uv run python .agents/skills/article2video/scripts/financial_video.py plan --project-dir videos/<slug> --duration-seconds 60 --window-months 12
uv run python .agents/skills/article2video/scripts/financial_video.py validate --project-dir videos/<slug>
uv run python .agents/skills/article2video/scripts/financial_video.py preview --project-dir videos/<slug> --limit-frames 120
uv run python .agents/skills/article2video/scripts/financial_video.py preview --project-dir videos/<slug>
uv run python .agents/skills/article2video/scripts/financial_video.py review-template --project-dir videos/<slug>
# 实际查看完整预演，填写 outputs/legibility-review.json 的结论与证据，再正式导出
uv run python .agents/skills/article2video/scripts/financial_video.py render --project-dir videos/<slug> --out videos/<slug>/outputs/financial-line.mp4
```

`init` 仅创建待填模板。价格来源、真实行情、来源快照和日期清单核验完成后，先运行 `validate`。`--period` 已移除，若旧材料包含 OHLC，必须先运行 `migrate-line`。金融视频材料和生成媒体均位于忽略的作品目录或外部内容根中；共享制作方法和规范纳入版本控制。

## 材料形状示例

以下是结构示意，不是可用于制作的完整材料：

```json
{
  "schemaVersion": 1,
  "originalRequest": "示例公司股价变化",
  "instrument": {
    "kind": "stock",
    "name": "示例公司",
    "code": "SAMPLE",
    "market": "NASDAQ",
    "unit": "USD",
    "listingDate": "1999-01-01"
  },
  "requestedRange": ["2020-01-01", "2020-12-31"],
  "displayRange": ["2020-01-01", "2020-12-31"],
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
  "schemaVersion": 4,
  "chartType": "line",
  "durationSeconds": 60,
  "fps": 30,
  "canvas": {"width": 1920, "height": 1080},
  "axis": {"dateRange": ["2020-01-01", "2020-12-31"], "visibleWindowMonths": 12, "valueScale": "rolling-linear"},
  "segments": [
    {"frames": [0, 90], "dates": ["2020-01-01", "2020-01-01"], "kind": "opening"},
    {"frames": [90, 1620], "dates": ["2020-01-01", "2020-12-31"], "kind": "advance"},
    {"frames": [1620, 1680], "dates": ["2020-12-31", "2020-12-31"], "kind": "overview"},
    {"frames": [1680, 1800], "dates": ["2020-12-31", "2020-12-31"], "kind": "ending"}
  ],
  "rationale": "60 秒连续折线编排，结束时展开完整历史"
}
```
