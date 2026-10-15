## Why

Pexels 暂停发放新 Key，单一图库阻碍新用户制作。用户已确认取得 Pixabay Key，需要增加可选择的图片与视频来源。

## What Changes

- 增加 Pixabay 检索与下载，按来源选择官方地址和凭据变量，保留 Pexels 默认行为。
- Pixabay 检索响应缓存 24 小时；凭据不进入日志、缓存及检索记录。
- 更新制作说明并验证两家图库兼容性。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `stock-montage-video`：增加 Pixabay 来源、缓存及凭据保护要求。

## Impact

影响 stock 图库适配器、材料默认值、检索缓存、测试及 README 和类型参考文档。不增加依赖，不修改渲染契约。
