## ADDED Requirements

### Requirement: 五类统一制作入口
系统 MUST 仅以五类公开身份提供 `types/init/validate/prepare/preview/review-template/review/status/render`；作品、分镜、准备记录和成片 MUST 使用同一版本与制作链路。初始化 MUST 使用 `videos/<type>/<slug>/`，类型清单与文档 MUST 从一份目录生成。

#### Scenario: 类型清单
- **WHEN** 查询类型或初始化任一已登记类型
- **THEN** 只出现五类，初始化文件可通过新版结构校验

### Requirement: 新版创作辅助命令
系统 MUST 提供 `m2v author` 的输入审查、候选稿、媒体及声音操作，以及 `m2v data financial-plan` 的金融计划编排；MUST 拒绝 `m2v general`、`m2v financial`、`m2v styles`、`m2v migrate` 和 `m2v relocate`。

#### Scenario: 旧命令
- **WHEN** 运行任一已移除命令
- **THEN** 参数解析失败，且不修改作品

## REMOVED Requirements

### Requirement: 统一作品及制作入口
**Reason**: v1 身份、类别目录和旧迁移命令已被五类 v2 契约替代。
**Migration**: 按 v2/v9 契约重新编排作品，使用五类统一入口。

### Requirement: 显式迁移
**Reason**: 本次版本升级不维护旧材料迁移工具。
**Migration**: 手工重新编排为 v2/v9，不复用旧准备与评审。

### Requirement: 当前类型统一制作入口
**Reason**: 四个旧类型及 `m2v general` 均移除。
**Migration**: 按五类选型并使用 `m2v author`。

### Requirement: 类型类别与父子登记
**Reason**: 五类即全部公开类型，不再需要类别层。
**Migration**: 使用 `videos/<type>/<slug>/`。
