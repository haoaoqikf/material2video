## Why

金融时间序列画面目前是一张通用的暗色折线图：市值浮在右上、曲线在中部，数字与曲线没有视觉关系；标题、条件句、市值和日期共用同一套无衬线字阶；`ledger`、`signal`、`archive` 三个设计档案只改背景光晕色，没有形成视觉身份。观众看到的是「任何股票都能套」的模板，而不是「苹果的 18 年」或「茅台的 25 年」。

本变更按已选定的「深色对账单」方向升级该类型的视觉语言：把画面组织成一张持仓对账单，让曲线成为余额走势、图表下方的收束区成为期末余额，用细规则线、表格化数字和一次编排的开场建立金融题材专属的观看秩序。

## What Changes

- 当前市值从画面右上移到图表下方的收束区：左侧为本金与投资起点，右侧为「当前市值」标签、hero 金额和最近实际收盘日期；金额仍与曲线同色，仍不插值、不滚动。
- 新增两条 1px 分隔线（标题上方、收束区上方）和收束区账目布局；分隔线颜色由 `profile` 决定，不进入市值、曲线、端点、坐标、轴标签、标题和底部说明。
- 背景改为暖近黑 `#0B0A09` 径向渐变与极细噪点；正文文字改为暖白。红 `#FF5A4E`／绿 `#4BD39A`／中性暖白 `#D8D4CC` 的涨跌语义不变。
- 数字统一使用等宽数字（`tabular-nums lining-nums`）；收束区本金 28px、起点 20px、市值标签 20px、市值 72/64/56px、日期 24px；正文数字不再因字符串变化而抖动。
- 开场 1 秒改为一次明确编排：分隔线先画，主体名、条件句、图表框/网格、收束区账目依次入场；入场使用透明度 + 8–12px 位移，收束区金额另带 0.985→1 缩放，不再只改透明度。
- 推进段仍以曲线为 primary、收束区市值为 secondary；结尾 2 秒继续完全冻结，不新增整屏淡入、扫光、粒子、面积填充或电影化运镜。
- 只重新生成 `videos/financial-timeseries/apple-since-2007`；作品材料 schema、v8 计划、投资计算、日期映射和其他作品的既有产物不变。苹果作品的 `design.profile` 改为 `ledger`，以使用暖金分隔线。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`：当前市值从顶部移到图表下方收束区；新增本金/起点账目、分隔线、暖近黑背景与等宽数字；重写开场编排；`profile` 增加分隔线色语义。

## Impact

- 前端：`web/src/types/financial/design.ts`、`overlay.tsx`、`FinancialTimeSeries.tsx`、`chart.tsx` 常量与对应测试。
- 文档：`.agents/skills/material2video/references/financial-timeseries-video.md`、`README.md` 当前能力描述、`openspec/specs/financial-timeseries-video/spec.md`。
- 作品：只重新 prepare、render 并验收 `videos/financial-timeseries/apple-since-2007`；其他金融作品的材料和既有成片不重新生成。
- 不新增材料字段、不改变 schema 版本、不改变 CLI 命令；既有 v8 计划与价格材料继续有效。
