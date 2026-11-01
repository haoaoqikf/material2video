## Why

金融时间序列类型的曲线、市值、红绿语义和自动验收已经成立，但用新引入的 `frontend-design` 与 `motion-design` 看仍有三处不足：

- 题材身份弱：主体名埋在“假如你20XX年买入10万元XX”的句尾，五条作品视觉几乎相同；
- 开场弱：开场 1 秒基本是静态保持，缺少有意的入场编排；
- 运动无语法：坐标扩展使用自写 smoothstep，端点与背景使用裸 `sin/cos`，没有共享命名曲线和 primary/secondary/ambient 分层。

用户要求按推荐方案升级该类型，只重做 Apple 作为试点，新做一条 Google 自 2004 年 IPO 以来的视频；moutai、nvidia、tencent、tesla 保持现有成片不动。

## What Changes

- `request.json` 增加可选 `design` 块（保持 schemaVersion 1，additive）：`profile`、`accent`、`titleMode`、`personality`；缺省为 signal/subject/corporate。
- 标题支持两行主体优先 masthead：主体名 56/48px，条件句 32/28px；`titleMode: premise` 保留现有单行 40px 公式。市值仍为 72/64/56 的右侧 hero，日期 24px。
- 新增三套中性设计 profile 与可选低透明度背景 accent；accent 不进入市值、曲线、端点、坐标，红绿语义不变。
- 开场 1 秒加入主体名→条件句→图表框→市值的编排；推进段坐标扩展/年份标签/端点使用共享命名曲线；结尾 2 秒继续冻结。
- 统一纵轴字号为 24px，消除规格中 22/24 的冲突。
- 重做 Apple 一条；新增 `videos/financial-timeseries/google-since-ipo`（GOOGL，2004-08-19～2026-10-30）；其余四条作品不重做。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`：可选 design 块、主体优先 masthead、profile/accent 边界、运动分层与开场编排、纵轴 24px。

## Impact

- 前端：`web/src/types/financial/design.ts`（新增）、`chart.tsx`、`overlay.tsx`、`FinancialTimeSeries.tsx`、`FinancialTimeSeries.test.tsx`。
- Python：`src/m2v/types/financial/materials.py`、`tests/types/financial/test_financial_materials.py`。
- 文档：`.agents/skills/material2video/references/financial-timeseries-video.md`、`README.md`、`openspec/specs/financial-timeseries-video/spec.md`。
- 作品：Apple 重做；Google 新建并渲染；moutai、nvidia、tencent、tesla 不改、不重做。
- 不涉及：数据映射、投资计算、红绿语义、布局边界、裁剪探针、自动 QA、CLI 门禁、其他视频类型。
