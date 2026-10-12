## Why

固定的垂直位移无法适配来源说明行数等内容变化，也不能保证画面整体真正居中。金融折线应根据实际渲染内容包围盒，在项目安全区内自动上下居中并继续执行硬边界检查。

## What Changes

- 以 x=140～940、y=180～1500 的项目安全区为定位范围，将金融视频前景内容组按实际包围盒居中。
- 内容高度超过安全区时阻断渲染；不缩字或裁切来绕过安全边界。
- 更新评审模板与制作工作流，重新预演、评审并生成英伟达视频。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`：将固定下移行为改为按完整可视内容包围盒在统一安全区内上下居中。

## Impact

- 影响共享金融 React composition、边界检测、Python 评审元数据、前端/Python 测试、README、制作参考和金融视频 OpenSpec 规格。
- 不改变金融材料格式、投资计算、画布、背景和安全区范围。
