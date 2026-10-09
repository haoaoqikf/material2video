# 金融时间序列视频专题

本文定义金融时间序列视频专题的制作规则。专题入口独立于文章字数、口播和有声评审流程。

专题行为以 [OpenSpec 专题规格](../../../../openspec/specs/financial-timeseries-video/spec.md) 为准。

## 1. 目标与请求

用户给出“公司或指数 + 起止年份”，由 Codex 等 AI 编程工具自行搜索资料。价格与动画计划统一使用 schemaVersion 3 横屏单标的日收盘价折线，不提供 K 线或周期选择。画面按日期推进、重大事件到达时标注，全片无音轨。首期覆盖 A 股、港股、美股及对应指数。

请求示意：“展示某家公司 2010 年到 2024 年的股价变化，带重大事件，先不要声音。”这不是对真实公司的行情查询。

必填标的名称与起止年份；可补充证券代码、市场、视频时长。年份默认展开为完整自然年；标的必须唯一识别，记录名称、代码、市场、币种或点位单位、上市或指数起始日期。公司多地上市、指数名称歧义或年份倒置时先澄清，不自行猜测。AI 搜索用于制作准备；项目代码不联网抓取行情。

## 2. 数据搜索与核验

AI 在制作准备阶段搜索公开免费来源，不依赖账号或付费密钥；本专题不预设固定网站、行情 API 或内置模型服务。每次制作需核验来源实际可用性和数据定义，不能把搜索摘要或来源不明的图表截图当成完整日线序列。

1. 找到交易日日线收盘数据，核对标的代码、市场、单位、时间范围和日期所属市场。
2. 股票默认仅调整拆股、合股，不计分红再投资。以区间末端的股份单位为基准；来源符合该基准时可直接使用，否则需留存可核实的转换依据。指数使用来源明确的官方点位，标注价格指数或其他类型。
3. 区分原始收盘价、前复权、后复权、含分红调整收盘价和仅拆合股调整价。“Adjusted close”名称本身不足以证明口径。若自行推导，保存原始价格、拆合股比例、生效日期、基准日期和计算说明；不能把包含分红的因子混入。
4. 免费数据不能满足口径时，说明问题并请求选择替代口径；不可静默降级。更换数据源也要重查口径，不能拼接定义不同的序列。
5. 校验日期排序、重复冲突、有效数值与交易日覆盖。周末、节假日和已核实停牌不产生虚构报价；应有交易数据异常缺失时阻断数据验收，不补零、插值或用折线跨越掩盖。
6. 上市前、指数起始前、未来日期或来源覆盖不足，披露请求范围与实际范围；需要缩短时先获得用户确认。来源全部不可用时说明无法获取，不替换标的。

保存原始下载或响应文件、标准化价格序列和来源清单。来源至少记录链接、获取时间、覆盖范围、调整定义；原始行情快照记录相对路径、来源链接和 SHA-256，推导数据还需记录依据。预期交易日清单须注明来源，验证器要求它与价格点日期逐项相同。图内显示币种或点位单位、口径与来源摘要，详细链接留在作品材料中。渲染只读已固定的本地文件，不联网。

## 3. 事件自动筛选

AI 搜索并自动筛选，无需逐条请用户确认。优先公司公告、交易所披露、指数发布机构和政府资料，必要时采用可信媒体。每个事件包含实际日期、简短事实标题和来源链接；区分发生日、公告日、报道日，统一采用标的市场当地日历日期。

公司事件优先，指数相关事件与重大市场事件可补充。默认最多八个，按标的关联、重要性、来源可信度及时间覆盖筛选，合并同类重复事件；保留候选、入选和排除理由。没有可靠事件时允许零标注，并说明资料不足。

日期冲突无法解决的候选排除。不得根据曲线涨跌编造事实，不直接写“某事件导致股价上涨/下跌”；事实标记表示时间上的发生，不自动表示因果。事件必须落在确认后的展示范围内。

休市日事件使用真实日期，锚定横轴时间位置，不伪造对应价格，不挪到下一交易日。详细说明按时间依次展示，已经发生的时间轴标记保留。

## 4. 视觉与时间编排

- 1920×1080、30 fps、单标的持续场景，无配音、音乐、音效或静音音轨。标题、日期、最新真实收盘价及所属交易日、口径、来源摘要和事件区域共同构成画面。
- 价格与动画计划使用 `schemaVersion: 3`；需求和事件保持 version 1。价格点只包含 `{date, close}`，不得携带 OHLC。动画明确 `chartType: "line"`。
- 默认最近 12 个日历月，新行情从右侧进入，已有曲线向左滚出。横轴按帧连续推进，月末回退截短到目标月有效末日，数据起始处钳制到起始日。窗口边缘可连接并裁剪前一个真实点，不产生虚构报价。
- 报价仅取不晚于当前日期的真实交易日收盘。休市期间保留原交易日期，不插值、不提前展示未来曲线或事件。完整日期范围用于时间推进；窗口外历史仅在结尾重新展开。
- 纵轴按窗口内有效收盘值线性自适应，两端留极差 8%；单点/相同价使用价格 1%（至少 0.01）的半范围。最近六帧的因果范围加权减缓收缩，同时包含当前窗口极值及左边缘真实连线的裁剪几何。边缘几何只用于坐标范围，不显示为历史报价。全貌展开时纵轴至少容纳当前可见曲线，避免横轴先展开而裁掉早期行情。随机寻帧与顺序播放相同，不使用 CSS 动画、墙钟或随机数。
- 默认 60 秒。开场 3 秒，每个入选事件停留 3 秒，结尾 6 秒；其余推进帧按事件之间的日历跨度确定性分配。正跨度至少两帧，同日事件依次暂停；预算不足阻断并提示增加时长，不删事件或缩短日期范围。
- 最后 6 秒已到达终日：前 2 秒 `overview` 平滑展开窗口至完整历史，横纵轴和曲线/事件同步变化；后 4 秒 `ending` 保持全貌。全貌为线性纵轴、稀疏年份刻度、事件编号及图例；近期阶段明确显示窗口长度和纵轴自适应提示。
- 事件保留真实日期，休市事件不挪动日期、不伪造价格；独立说明区域依次展示，不遮盖曲线。标记随窗口滚出，全貌中编号恢复。标记表明时间，不能宣称价格变化由事件导致。

### 完整静音预演与评审

先用 `preview --limit-frames 120` 检查开场，再用不限制帧数的 `preview` 生成完整评审版。预演只能写入 `outputs/previews/`；正式导出不能写入该目录。渲染器验收帧数、分辨率及无音轨，写入 `preview-record.json`，绑定产物路径、文件 SHA-256、实际帧数及材料/资产摘要。

`review-template` 只接受当前完整预演，生成 pending 记录。AI 助手必须实际查看完整预演，结合事件前/到达/后、推进中段、54–56 秒展开及最终帧抽检，填写 `sampleTimecodes`、`fullVideo`、五项 `checks` 和逐项 `evidence`，确认标签可读、滚动可跟随、坐标稳定、事件无重叠、全貌完整后才能设 `result: "pass"`。短预演不能充当全片评审。摘要绑定四类材料、web 可达构建输入和金融 Python 代码，任何变化都要求重新预演/评审；渲染期间材料变化也会阻断发布。

### 旧材料显式迁移

旧 version 1 折线和 version 2 OHLC 材料均不能直接计划或渲染。运行 `migrate-line`：先核验需求、来源、快照摘要、真实 close 与交易日覆盖，备份四类材料和原评审至 `outputs/material-backups/`，仅提取 date/close、保留口径与来源，并生成新动画计划。失败恢复原材料。旧评审保留但摘要失效，须重新完整预演。旧成片不改动；新版默认成片名称为 `financial-line.mp4`，英伟达使用独立名称。

## 5. 作品材料与命令

每个作品目录固定包含以下四份材料。字段契约由 `.agents/skills/article2video/scripts/a2v/financial.py` 校验；这些材料不使用 `storyboard.json`，也不交给文章校验入口。

| 材料 | 建议文件 | 最小信息 |
| --- | --- | --- |
| 需求记录 | `request.json` | 原始请求、唯一标的、请求/实际日期范围及缩短确认 |
| 价格序列 | `prices.json` | 预期交易日、逐日真实收盘值、口径、来源和原始文件 SHA-256 |
| 事件清单 | `events.json` | 候选、入选、排除理由及日期依据 |
| 动画编排 | `animation-plan.json` | version 3、chartType=line、时长、完整范围、窗口月数、线性自适应轴、连续半开帧段、overview/ending 和事件停留 |

原始数据快照保存在作品目录中；静音预演与验收记录放在 `outputs/`。实际作品使用已有忽略目录 `videos/<slug>/`，或外部内容根中的作品目录；材料、行情、事件资料及媒体均不入库。方法与规范入库，不使用 `git add -f` 绕过忽略，不增删替换现有三个示例。

```powershell
uv run python .agents/skills/article2video/scripts/financial_video.py init `
  --out-dir videos/<slug> --kind stock --name <公司名> --code <证券代码> `
  --market <市场> --unit USD --listing-date YYYY-MM-DD `
  --start-date YYYY-01-01 --end-date YYYY-12-31

# 旧材料先显式迁移；全新 version 3 材料使用 plan
uv run python .agents/skills/article2video/scripts/financial_video.py migrate-line --project-dir videos/<slug> --duration-seconds 60 --window-months 12
uv run python .agents/skills/article2video/scripts/financial_video.py plan --project-dir videos/<slug> --duration-seconds 60 --window-months 12
uv run python .agents/skills/article2video/scripts/financial_video.py validate --project-dir videos/<slug>
uv run python .agents/skills/article2video/scripts/financial_video.py preview --project-dir videos/<slug> --limit-frames 120
uv run python .agents/skills/article2video/scripts/financial_video.py preview --project-dir videos/<slug>
uv run python .agents/skills/article2video/scripts/financial_video.py review-template --project-dir videos/<slug>
# 实际查看完整预演及关键帧，填写 outputs/legibility-review.json 的结论与证据后正式导出
uv run python .agents/skills/article2video/scripts/financial_video.py render --project-dir videos/<slug> --out videos/<slug>/outputs/financial-line.mp4
```

`init` 只写空模板，不替用户或 AI 搜索资料；空数组、未定时长及坐标占位不能渲染。指数用 `--kind index` 并提供点位单位；AI 还须填写 `prices.json.indexType`。用户自然语言提出标的后，AI 必须搜索、核实来源并填材料；校验失败前不得渲染。短预演不代表终稿验收通过。

### 合成结构示例

以下数值、标的和事件全部为合成资料，`example.invalid` 是示例地址，不能作为行情或事件证据。字段片段帮助理解材料，原始快照须另存文件，四份完整材料才能通过离线校验。

需求记录：

```json
{
  "schemaVersion": 1,
  "originalRequest": "合成公司2020年到2020年的无声演变视频",
  "instrument": {
    "name": "合成公司",
    "code": "SYNTHETIC",
    "market": "synthetic",
    "schemaVersion": 3,
  "unit": "USD",
    "listingDate": "2010-01-01"
  },
  "requestedRange": ["2020-01-01", "2020-12-31"],
  "displayRange": ["2020-01-01", "2020-01-03"],
  "confirmations": ["合成示例中确认缩短展示范围"]
}
```

价格材料（version 3；以下为需补齐来源和原始快照的合成片段）：

```json
{
  "unit": "USD",
  "priceBasis": "split-adjusted",
  "adjustmentBaseDate": "2020-01-03",
  "adjustmentDefinition": "仅拆合股调整，不计分红再投资",
  "splitAdjustments": [],
  "expectedTradingDates": ["2020-01-02", "2020-01-03"],
  "expectedTradingDatesSource": ["https://example.invalid/calendar"],
  "points": [
    {"date": "2020-01-02", "close": 100},
    {"date": "2020-01-03", "close": 101}
  ],
  "sources": [{
    "url": "https://example.invalid/prices",
    "fetchedAt": "2026-10-05T00:00:00Z",
    "coverage": ["2020-01-01", "2020-12-31"],
    "adjustmentDefinition": "仅拆合股调整；示意期间无拆合股"
  }],
  "rawSnapshots": [{"path": "raw-prices.csv", "sha256": "由原始快照计算的 64 位 SHA-256", "sourceUrl": "https://example.invalid/prices"}]
}
```

事件材料：

```json
{
  "schemaVersion": 1,
  "candidates": [{
    "id": "event-1",
    "date": "2020-01-02",
    "dateBasis": "announced",
    "title": "合成公司发布产品公告",
    "sources": ["https://example.invalid/announcement"],
    "reason": "与标的直接相关；合成事实标注示意"
  }],
  "selected": [{
    "id": "event-1", "date": "2020-01-02", "dateBasis": "announced",
    "title": "合成公司发布产品公告", "sources": ["https://example.invalid/announcement"],
    "reason": "与标的直接相关；合成事实标注示意"
  }],
  "excluded": []
}
```

动画编排由 `plan` 生成；不要手写第二套时长规则。version 3 根级示意：

```json
{"schemaVersion": 3, "chartType": "line", "durationSeconds": 60, "fps": 30, "canvas": {"width": 1920, "height": 1080}, "axis": {"dateRange": ["2020-01-01", "2020-01-03"], "visibleWindowMonths": 12, "valueScale": "rolling-linear"}}
```

上述仅为片段，完整材料还需 `segments`、`eventDisplays` 和 `rationale`。开场及事件 hold 为 90 帧，尾部 overview 为 60 帧、ending 为 120 帧；所有帧段连续覆盖总时长。
