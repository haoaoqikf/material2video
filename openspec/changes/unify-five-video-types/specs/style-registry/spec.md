## REMOVED Requirements

### Requirement: 空注册目录与风格查询
**Reason**: 风格层取消。
**Migration**: 选择五类视频类型；通用组件使用场景 SDK。

### Requirement: 风格要求声明
**Reason**: 作品不再选择风格。
**Migration**: 由分镜与场景声明旁白和画面。

### Requirement: 包内字体缺失提示恢复
**Reason**: 不再有风格包字体。
**Migration**: 使用公共字体登记与恢复机制。

### Requirement: 可选作品绑定
**Reason**: `project.style` 被移除。
**Migration**: 删除风格字段并重新编排 v2 作品。

### Requirement: 显式表现接入
**Reason**: `m2v/style` 导入被移除。
**Migration**: 使用 `m2v/code-scene` 或作品本地组件。

### Requirement: 准备与缓存绑定
**Reason**: 不再存在风格包指纹。
**Migration**: 准备指纹继续绑定实际场景源码、资源与字体。
