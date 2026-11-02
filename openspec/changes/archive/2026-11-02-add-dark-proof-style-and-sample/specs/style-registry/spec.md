## MODIFIED Requirements

### Requirement: 空注册目录与风格查询

系统 SHALL 从仓库 styles 的直接子目录发现风格包，提供 `m2v styles` 文本及 JSON 查询，校验清单、入口和资产来源许可。仓库 SHALL 登记 `vibe-fable`、`vibe-night`、`doc-archive`、`count-ledger`、`deep-journey` 与 `dark-proof` 六个正式风格包；未注册任何风格时 SHALL 返回空目录，未选风格作品 SHALL 保持可用。规范示例 SHALL 位于 `styles/<style-id>/examples/<slug>/`，不参与风格发现；不再维护 `styles/examples/` 或旧路径别名，其余直接子目录 SHALL 为有效风格包。

#### Scenario: 已登记风格

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** 返回六个正式风格包的 id、version、description、types 与 frames，清单、入口或资产许可非法时明确失败

#### Scenario: 保留目录不被发现

- **WHEN** 各风格的 examples 子目录包含作品及其输出
- **THEN** 风格查询仅返回直接子目录的风格，不把示例当作独立风格，直接加载 examples 明确失败

#### Scenario: 空目录

- **WHEN** 仓库未注册任何风格包
- **THEN** 文本显示暂无已注册风格，JSON 返回空数组，未选风格作品保持可用
