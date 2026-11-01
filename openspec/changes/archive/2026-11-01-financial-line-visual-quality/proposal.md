## Why

金融折线类型的功能门禁全部通过，但成片视觉仍停留在「会动的图表」：开场纵轴刻度因固定三位有效数字而重复、纵轴 14 px 在 360×640 手机缩放下不可辨、日频折线在窄绘图区内挤成毛刺、曲线只有单色实线且没有本金参照、绘图区偏小、持平显示绿色与红涨绿跌语义冲突。同类型五条成片共用同一渲染实现，问题属于类型级而非单条作品。

用户要求按已确认的 11 条质感方案改造，只重制苹果一条作品，并把金融类型默认帧率从 60 fps 调整为 30 fps。

## What Changes

- 金融类型固定帧率从 60 fps 改为 30 fps：`web/src/video-config.json`、计划校验文案、规格、文档与测试同步。
- 绘图区从 x=220～928、y=520～1190 扩大为 x=224～936、y=490～1260；底部说明区下移，整体居中与安全区探针按新几何重算。
- 纵轴刻度字号从 14 px 提高到 22 px；刻度按数值间距决定小数位，单位（万/亿/万亿）只在轴顶标注一次，不再每行重复。
- 曲线改为双层：按月采样并经单调三次插值平滑的主曲线承担趋势，全量日线以低透明度细线保留真实波动；主曲线下方增加渐变面积层与低透明度光晕，端点增加外环，并绘制最近收盘位置的淡竖线。
- 新增本金基准线：本金落在当前纵轴范围内时，以虚线和小字「本金」标示，不显示收益金额或收益率。
- 持平（收益为零）的市值与曲线改用中性浅灰，不再使用绿色；正收益红、负收益绿保持不变。
- 顶部市值字号按固定档位适配，不再按当前字符串逐帧反推；金额去掉数字与单位之间的空格，纵轴刻度不再使用千分位逗号。
- 背景由纯色改为低对比径向渐变，主曲线与网格使用分层明度。
- 金融验收规范补充手机可读的最低判据：360×640 缩放下纵轴刻度不得低于约 7 px 实际高度，并实际查看代表帧。
- 重制 `videos/financial-timeseries/apple-since-2007`；其余四条作品不重制，内容目录不入库。

不涉及：事件标注、收益率数字、图内金额牌、材料字段、准备与交付门禁、其他视频类型。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`：固定帧率、绘图区与纵向布局、纵轴刻度字号与单位、曲线绘制与材质、本金基准线、持平颜色、金额格式与手机可读验收判据。
- `video-frame-rate`：金融固定帧率由 60 fps 改为 30 fps。

## Impact

- 代码：`web/src/video-config.json`、`web/src/types/financial/chart.tsx`、`overlay.tsx`、`FinancialTimeSeries.tsx`、`src/m2v/types/financial/materials.py`。
- 测试：`web/src/types/financial/FinancialTimeSeries.test.tsx`、`tests/types/financial/*`、受 60 fps 影响的通用测试。
- 文档：`references/financial-timeseries-video.md`、`README.md`、`openspec/specs/financial-timeseries-video/spec.md`、`openspec/specs/video-frame-rate/spec.md`。
- 内容：仅重制苹果作品；`videos/` 保持忽略，不提交成片或材料。
