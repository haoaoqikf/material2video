# 金融时间序列视频专题

本文定义金融视频的离线制作规范。专题入口独立于文章字数、口播和有声评审流程，行为以 [OpenSpec 专题规格](../../../../openspec/specs/financial-timeseries-video/spec.md) 为准。

## 制作与数据

请求由标的和日期范围构成。制作准备阶段核验公开免费行情来源，项目代码不联网抓取行情。股票默认采用仅拆股、合股调整的日收盘价，不计分红再投资；指数采用来源明确的官方点位。明确价格口径、覆盖范围、市场日期、币种或点位单位。保存原始响应快照、来源清单及 SHA-256，预期交易日清单必须与实际价格日期逐项相同。休市日不补报价，交易日数据异常缺失时停止验收。

作品只展示真实日收盘价折线，不搜索、保存或展示事件，也不包含 K 线或周期选择。价格和计划材料必须使用 `{date, close}` 日线。渲染仅读取本地材料，不联网。

## 材料与编排

作品使用三份材料：`request.json` schema v1、`prices.json` schema v3、`animation-plan.json` schema v5。材料目录不使用 `storyboard.json`，也不进入文章校验入口。

计划明确 `chartType: "line"`、`axis.dateScale: "full-range"` 和 `axis.valueScale: "revealed-linear"`，不接受滚动窗口或固定纵轴范围。默认 60 秒、1920×1080、30 fps、无音轨：开场 3 秒，行情推进 53 秒，完整曲线停留 4 秒。完整日期横轴和稀疏年份刻度从开头固定展示，折线从左向右揭示已到达的真实日收盘点，历史点持续保留。休市日保持最近真实收盘价及其交易日期，不生成插值报价或提前显示未来价格。

纵轴根据从起始日至当前日期全部已展示价格的极值线性自适应，上下各留白 8%。单点或恒定价格以绝对价格的 1%（至少 0.01 单位）作为半跨度。采用六帧因果加权范围并以当前范围包络，保证新极值不裁切；终幕冻结最后推进帧的坐标。回落不会缩小到只容纳近期股价，历史曲线始终完整。画面显示“纵轴随已展示价格自适应”；随机寻帧与顺序播放一致。

正式导出前必须针对完整静音预演完成材料绑定评审。评审记录包括预演哈希、材料和构建资产摘要、抽检时间码，以及 `labelsReadable`（标签可读）、`advanceTrackable`（推进可跟随）、`dateAxisFixed`（横轴固定）、`axisStable`（坐标稳定）、`overviewComplete`（全貌完整）五项结论及证据。短预演不能作为正式评审；输入变化会令评审失效。

## 显式迁移

旧 OHLC 价格材料及旧 v3/v4 动画计划不得直接渲染或用 `plan` 覆盖。运行 `migrate-line`：验证旧材料后只提取原有 `close`，保留日期、价格口径、来源、原始快照和交易日清单，将计划更新为 v5。迁移前完整备份请求、价格、计划、旧事件及评审/预演记录（如有），成功后清除活动旧事件和过期评审记录；失败恢复活动材料。迁移不刷新行情截止日、不覆盖已有成片，完成后必须重新完整预演与评审。

## 命令

```powershell
uv run python .agents/skills/article2video/scripts/financial_video.py init `
  --out-dir videos/<slug> --kind stock --name <公司名> --code <证券代码> `
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

`init` 仅创建待填模板。价格来源、真实行情、来源快照和日期清单核验完成后，先运行 `validate`。`--period` 和 `--window-months` 已移除，若旧材料包含 OHLC，必须先运行 `migrate-line`。`preview` 不加 `--out` 时写出作品的标准完整预演并登记 `outputs/previews/preview-record.json`，评审模板绑定的是它；带 `--out` 的 `preview` 只是复核/对比用的旁路输出，不会改写已登记的预演记录或已有评审，但也不能作为提交评审的预演。金融视频材料和生成媒体均位于忽略的作品目录或外部内容根中；共享制作方法和规范纳入版本控制。成片与预演经临时目录中转，Windows 上会带上临时目录那份「关闭继承」的 ACL，因此落盘后统一用 `icacls /reset` 重新继承所在目录的权限（必须搬运之后执行，在临时目录里修复只会再套一遍那份收紧的 ACL）；否则以标准权限运行的打包播放器打开交付视频时报 `0x80070005`。预演同样是给人打开的文件，也一并修复。

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
  "schemaVersion": 5,
  "chartType": "line",
  "durationSeconds": 60,
  "fps": 30,
  "canvas": {"width": 1920, "height": 1080},
  "axis": {"dateRange": ["2020-01-01", "2020-12-31"], "dateScale": "full-range", "valueScale": "revealed-linear"},
  "segments": [
    {"frames": [0, 90], "dates": ["2020-01-01", "2020-01-01"], "kind": "opening"},
    {"frames": [90, 1680], "dates": ["2020-01-01", "2020-12-31"], "kind": "advance"},
    {"frames": [1680, 1800], "dates": ["2020-12-31", "2020-12-31"], "kind": "ending"}
  ],
  "rationale": "60 秒固定全日期横轴编排，纵轴随已展示价格自适应"
}
```
