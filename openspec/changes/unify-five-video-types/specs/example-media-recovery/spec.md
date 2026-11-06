## ADDED Requirements

### Requirement: 五类示例素材恢复
七个示例 MUST 位于 `examples/<type>/<slug>/`；每个示例的恢复入口 MUST 按配方校验 SHA-256、尺寸与时长，不改写来源登记、许可或预期摘要。媒体及生成声音 MUST 被 Git 忽略，配方、分镜与场景源码 MUST 入库。

#### Scenario: 恢复与运行
- **WHEN** 示例输入缺失后按配方恢复
- **THEN** 全部素材校验后示例可准备和短预演；失败不覆盖正确素材

## REMOVED Requirements

### Requirement: 固定素材恢复
**Reason**: 风格示例路径不再存在。
**Migration**: 使用 `examples/<type>/<slug>/assets/` 下的恢复入口。

### Requirement: 版本控制边界
**Reason**: 风格示例的 Git 路径规则已过时。
**Migration**: 对独立示例目录应用同等源码入库和媒体忽略规则。
