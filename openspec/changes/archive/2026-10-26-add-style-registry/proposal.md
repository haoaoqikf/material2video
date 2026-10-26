## Why

项目需要在不改变视频类型职责的前提下接入不同表现风格。目前缺少统一的风格注册、作品绑定与依赖校验机制。

## What Changes

- 建立空 styles 目录和版本化风格包契约，不内置风格。
- 增加作品可选风格声明、查询、加载校验及依赖指纹。
- 为 general 场景提供参数读取及受限组件、资产导入。
- 同步制作指导、架构及验证，保留未选择风格作品的行为。

## Capabilities

### New Capabilities
- `style-registry`：独立于视频类型的风格发现、选择、运行时接入与准备依赖。

### Modified Capabilities

无。

## Impact

涉及 core/project、独立风格模块、CLI、general 代码场景打包、SDK、准备及缓存状态；不新增依赖，不改变评审和导出条件。
