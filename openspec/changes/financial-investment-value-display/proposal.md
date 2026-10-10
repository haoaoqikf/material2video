## Why

金融折线直接显示股价，不容易让观众理解长期涨跌对实际投入的意义。改为展示假设投资的市值、收益和收益率，并让数值随行情时间推进。

## What Changes

- **BREAKING** 金融视频改为假设投资表现；投资年份首个交易日收盘投入 1,000,000 标的计价币种，显示当前市值、收益及收益率。
- 折线表示投资组合价值，起投前隐藏投资指标；底部注释只保留行情来源和统计口径。
- 更新材料校验、共享渲染组件、金融制作说明及验收测试。

## Capabilities

### New Capabilities

### Modified Capabilities
- `financial-timeseries-video`: 从股价展示改为假设投资价值展示，并调整材料、动态指标和说明区域行为。

## Impact

- React 金融 composition 及其测试；Python 金融材料初始化、校验和渲染 props。
- OpenSpec 金融专题规格、金融制作 Skill 参考及 README 当前能力说明。
- 作品 `request.json` 增加投资设置。真实作品与媒体位于忽略目录，不纳入版本控制。
