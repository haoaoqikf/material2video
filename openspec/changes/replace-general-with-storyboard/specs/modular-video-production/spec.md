## ADDED Requirements

### Requirement: 三类型统一制作入口
系统 MUST 仅注册 financial-timeseries、housing-timeseries 和 general，通用类型中文名为“通用”，以 storyboard 材料制作 v6 讲解；辅助操作 MUST 使用 m2v general。旧 article-narrative 类型与 m2v article 命令 MUST 被拒绝，作品标准位置 MUST 为 videos/general/<slug>。

#### Scenario: 查询与初始化类型
- **WHEN** 用户查询类型或初始化通用作品
- **THEN** 类型列表仅返回三类，通用模板与目录采用 general 身份

#### Scenario: 旧入口被拒绝
- **WHEN** 用户指定 article-narrative 类型或执行 m2v article
- **THEN** 系统报告无效类型或命令，不提供兼容分发
