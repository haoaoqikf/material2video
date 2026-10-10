## Why

英伟达成片把金额标成美元，画面空间也还能继续利用。此项调整让金额显示更简洁，并让折线图从更靠左的位置展开。

## What Changes

- 收益和端点金额统一使用中文数量级及“元”后缀，不显示特定币种名称。
- 横轴起点向左扩展，并缩小纵轴刻度以保留标签安全区。
- 更新金融视频规格、制作参考、README 和组件测试，重新预演并导出英伟达视频。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`: 金额标签改用“元”，图表横向扩展并保持纵轴刻度在安全区内。

## Impact

- 画面组件：`web/src/compositions/FinancialTimeSeries.tsx`
- 组件测试：`web/src/compositions/FinancialTimeSeries.test.tsx`
- 金融视频 OpenSpec、制作参考与 README
- `videos/nvidia-since-ipo/` 忽略目录中的预演与正式视频
