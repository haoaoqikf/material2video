## ADDED Requirements

### Requirement: v9 五类代码分镜
系统 MUST 只接受 version/schemaVersion 均为 9 的统一分镜，保留 30/60 fps、横竖屏、唯一场景与旁白 ID、主题或原文输入、时间窗、镜头、声音及转场校验。五类分镜 MUST 允许无旁白代码幕，MUST 拒绝未知字段与旧准备记录。

#### Scenario: 五类共享分镜
- **WHEN** 五类作品分别提供合法 v9 分镜
- **THEN** 相同的时间轴、字幕、录制与声音逻辑适用

#### Scenario: 旧分镜
- **WHEN** 输入 v8 或更早分镜
- **THEN** 要求按 v9 重新编排，不自动迁移

## REMOVED Requirements

### Requirement: v8 横竖屏代码分镜
**Reason**: v8 只属于旧 `general` 类型，已被五类 v9 分镜替代。
**Migration**: 按 v9 契约重新编排。

### Requirement: 随附风格示例集合
**Reason**: 风格层取消，示例归入独立五类目录。
**Migration**: 使用 `examples/<type>/<slug>/` 中的新版示例。
