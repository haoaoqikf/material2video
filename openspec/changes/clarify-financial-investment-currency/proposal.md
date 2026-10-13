## Why

金融作品把本金描述成“标的计价单位”，但画面统一以“元”展示金额，容易被理解成已经按汇率模拟了人民币账户回报。需要明确本金是用于缩放价值变化的数值基数，真正表达的是标的价格倍数，而非实际投资金额的币种或汇兑后账户价值。

## What Changes

- 在金融时间序列规范与制作说明中明确价格倍数及组合价值公式。
- 明确不计算汇率变化或实际换汇后的人民币余额；画面“元”仅为金额展示约定。
- README 增加简短口径说明，材料 schema、行情、画面和渲染均不变。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`：增加本金基数、价格倍数和币种展示边界的说明要求。

## Impact

影响金融时间序列 OpenSpec、Material2Video Skill 金融参考文档及 README；不改代码、材料格式或现有视频。

