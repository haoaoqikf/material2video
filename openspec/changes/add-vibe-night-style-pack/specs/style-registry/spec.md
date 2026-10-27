## MODIFIED Requirements

### Requirement: 空注册目录与风格查询

系统 SHALL 从仓库 styles 发现风格包，提供 `m2v styles` 文本及 JSON 查询，校验清单、入口和资产来源许可。仓库 SHALL 登记 `vibe-night` 作为首个正式风格包；未注册任何风格时 SHALL 返回空目录，未选风格作品 SHALL 保持可用。

#### Scenario: 已登记风格

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** 返回 `vibe-night` 的 id、version、description、types 与 frames；清单、入口或资产许可非法时命令明确失败，不静默跳过

#### Scenario: 空目录

- **WHEN** 仓库未注册任何风格包
- **THEN** 文本显示暂无已注册风格，JSON 返回空数组，未选风格作品保持可用
