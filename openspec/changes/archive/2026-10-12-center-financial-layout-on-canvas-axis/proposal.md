## Why

金融折线画面目前将前景包围盒居中到纵向安全区中线 y=840，而非 1920 高画布的中线 y=960，导致整组内容相对画布仍显得偏上。统一以画布中线为中心，可使用户要求的上下居中有明确、可验证的几何定义。

## What Changes

- 金融股票与指数画面的统一前景层按实际包围盒居中到 y=960。
- 纵向项目布局检查范围调整为 y=180～1740，保持画布上下各 180px 的对称边距；横向范围维持 x=140～940。
- 更新边界探针、评审模板、制作参考文档和安全区报告，并重新预演、评审及渲染特斯拉视频。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`：整体内容改为对齐画布中线，纵向布局检查范围改为对称边界。

## Impact

- 影响 `web/src/compositions/FinancialTimeSeries.tsx` 与对应测试，以及 Python 金融评审指标和模板。
- 同步更新金融视频 README、制作参考文档和 OpenSpec 主规格。
- 重新生成 `videos/tesla-ipo-to-present` 派生产物；作品内容与媒体仍由 Git 忽略。
