## MODIFIED Requirements

### Requirement: 独立示例目录

五类仅决定制作指导和默认目录；每个工程 MUST 独立拥有执行能力，不以主项目统一运行时作为运行前提。旧project v2和旧准备记录 MUST 明确拒绝，不提供转换入口。

仓库 MUST 在 `examples/<type>/<slug>/` 保存五个可运行示例；示例素材恢复与输出仍遵守来源摘要校验及 Git 忽略规则。

#### Scenario: 示例运行
- **WHEN** 逐一对五个示例执行校验、准备和短预演
- **THEN** 不依赖风格包，所有作品材料和输出均留在自身目录
