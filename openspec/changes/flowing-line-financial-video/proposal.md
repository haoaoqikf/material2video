## Why

英伟达长期行情被自动周期预算压缩成年 K，无法表达用户要求的快速流动日收盘价变化。金融视频统一为滚动折线，并在结尾展开完整历史。

## What Changes

- **BREAKING** 移除 K 线、OHLC 聚合和周期选择接口；价格和动画计划升级为 schemaVersion 3。
- 显式迁移旧材料，仅提取真实 close，备份原材料并使旧评审失效。
- 默认最近 12 个月平滑滚动，结尾 2 秒展开全历史并停留 4 秒。
- 所有正式金融导出均要求绑定材料与资产的完整静音预演评审。
- 用新流程重制 60 秒英伟达视频，保留旧成片。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`：统一折线材料、动画、显式迁移与评审门禁；移除周期聚合能力。

## Impact

金融 Python 校验、CLI、渲染门禁、React composition、相关测试及专题文档。实际作品和生成媒体仍不入库，三个文章示例不变。
