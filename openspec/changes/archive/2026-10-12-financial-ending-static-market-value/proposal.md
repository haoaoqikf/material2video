## Why

当前金融视频在终幕将“当前市值”切换为本金到最终市值总结并显示收益率，导致与最后推进帧的画面状态不连续。终幕应作为行情画面的静止收束，保留最终时点信息，不增加总结卡片。

## What Changes

- 终幕沿用最后推进帧的年份、当前市值和实际收盘日期，取消总结文字、收益率及淡入。
- 保留曲线和坐标冻结、端点金额、3/51/6 秒分段及既有说明。
- 更新金融画面测试、规格和制作文档，并重导 NVIDIA 成片。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`: 终幕保持最后推进帧的市值信息，不显示本金总结或收益率。

## Impact

影响金融时间序列 React composition 与测试、金融时间序列 OpenSpec 规格、README 和 material2video Skill 参考文档，以及忽略目录中的 NVIDIA 预演、评审和最终视频。
