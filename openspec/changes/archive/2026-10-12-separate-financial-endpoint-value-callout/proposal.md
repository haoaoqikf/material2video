## Why

金融视频的端点金额固定贴在折线端点附近，行情波动密集时会与曲线混在一起，手机画面难以辨认。为所有金融成片提供稳定、清晰且能避让折线的端点金额标记。

## What Changes

- 为端点金额增加独立底板和留白，并按附近折线几何选择不遮挡曲线的位置。
- 将标签底板、文字、端点间距和项目边界纳入运行时探针与测试。
- 同步金融制作参考规范，并重新预演、评审和生成特斯拉视频。

## Capabilities

### New Capabilities

### Modified Capabilities
- `financial-timeseries-video`: 端点金额标签必须清晰可辨、与折线分离并留在项目布局范围内。

## Impact

- 影响 `web/src/compositions/FinancialTimeSeries.tsx` 及其前端测试。
- 更新金融时间序列 OpenSpec 与制作参考文档。
- 特斯拉视频的共享渲染产物需重新准备、预演、评审和渲染；作品内容仍在忽略目录中。
