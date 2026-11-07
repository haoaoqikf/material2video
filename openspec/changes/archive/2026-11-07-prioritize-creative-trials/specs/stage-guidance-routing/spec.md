## REMOVED Requirements

### Requirement: 任务与阶段决定主要阅读入口
**Reason**: 经用户确认以三阶段媒体评审体系替换旧流程与检查点约束。
**Migration**: 不迁移旧通过；保留历史，显式开启新周期。

### Requirement: 阅读预算与路由可校验
**Reason**: 经用户确认以三阶段媒体评审体系替换旧流程与检查点约束。
**Migration**: 不迁移旧通过；保留历史，显式开启新周期。

### Requirement: 精简必须保全规则
**Reason**: 经用户确认以三阶段媒体评审体系替换旧流程与检查点约束。
**Migration**: 不迁移旧通过；保留历史，显式开启新周期。

### Requirement: 阶段指南必须以决策表组织
**Reason**: 经用户确认以三阶段媒体评审体系替换旧流程与检查点约束。
**Migration**: 不迁移旧通过；保留历史，显式开启新周期。

### Requirement: 删除文档必须迁移活动路由
**Reason**: 经用户确认以三阶段媒体评审体系替换旧流程与检查点约束。
**Migration**: 不迁移旧通过；保留历史，显式开启新周期。

### Requirement: 制作指导必须按权威分层组织
**Reason**: 经用户确认以三阶段媒体评审体系替换旧流程与检查点约束。
**Migration**: 不迁移旧通过；保留历史，显式开启新周期。

## ADDED Requirements

### Requirement: 三阶段唯一阅读入口
阅读路由 MUST 使用 research/design/production 三个唯一主指南；创作总纲保持必读，详细研究与隔离评审按需展开；重复阶段指南及跳转页 MUST 删除，活动链接和 JSON 示例 MUST 有效。

#### Scenario: 读取当前阶段
- **WHEN** 执行本场景
- **THEN** 入口 MUST 指向对应阶段，不要求递归阅读所有参考。
