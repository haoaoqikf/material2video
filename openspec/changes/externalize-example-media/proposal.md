## Why
示例媒体直接进入 Git 增加克隆与历史存储成本。保留公共字体，改为恢复固定素材，并在恢复验证后清理本地与远端历史。

## What Changes
- 示例媒体通过配方下载或生成，按摘要校验，缓存命中跳过。
- 恢复不改写来源清单，失败不覆盖已有素材。
- 示例媒体不入库；备份后清理历史并以租约保护更新远端。

## Capabilities
### New Capabilities
- `example-media-recovery`: 示例固定媒体恢复与版本控制边界。
### Modified Capabilities
无。

## Impact
示例获取脚本、共享恢复工具、测试、制作说明、Git 忽略规则与历史。公共字体继续入库。
