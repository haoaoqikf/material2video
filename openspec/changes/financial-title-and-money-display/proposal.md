## Why

当前金融视频标题会带币种并可能换行，收益和端点金额使用英文逗号数字，指标靠左且字号偏大。需要压缩顶部信息层级，并让金额、日期和底部提示更适合手机阅读。

## What Changes

- 标题改为不带本金币种的一行文本，并按可用宽度适配字号。
- 收益日期、收益率和收益金额组成靠右的小字信息组；日期对应最近实际收盘数据。
- 收益和市值采用中文数量级及标的原币名称，例如“56.2 亿美元”。
- 来源与统计口径之后增加一行风险提示。

## Capabilities

### New Capabilities

### Modified Capabilities
- `financial-timeseries-video`: 更新金额、标题、指标位置与底部风险提示的可见行为。

## Impact

- 修改金融 Remotion composition 及其组件测试。
- 更新金融视频 OpenSpec 规格、制作 Skill 参考文档和 README 当前能力说明。
- 不改变金融材料 schema、价格来源或投资收益计算。
