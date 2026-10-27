## MODIFIED Requirements

### Requirement: 空注册目录与风格查询

系统 SHALL 从仓库 styles 发现风格包，提供 `m2v styles` 文本及 JSON 查询，校验清单、入口和资产来源许可。仓库 SHALL 登记 `vibe-night` 作为首个正式风格包；未注册任何风格时 SHALL 返回空目录，未选风格作品 SHALL 保持可用。

#### Scenario: 已登记风格

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** 返回 `vibe-night` 的 id、version、description、types 与 frames；清单、入口或资产许可非法时命令明确失败，不静默跳过

#### Scenario: 空目录

- **WHEN** 仓库未注册任何风格包
- **THEN** 文本显示暂无已注册风格，JSON 返回空数组，未选风格作品保持可用

## ADDED Requirements

### Requirement: 风格要求声明

风格清单 SHALL 可声明可选 `requires` 对象，当前仅允许 `narration` 取 `none` 或 `any`；未知键或非法值 SHALL 明确失败。作品选择风格时 SHALL 按 `requires.narration` 与分镜是否含旁白校验，不满足时 SHALL 明确失败且不回退到无风格。

#### Scenario: 无旁白风格被有旁白作品选择

- **WHEN** 任一幕含旁白的作品选择 `requires.narration = none` 的风格包
- **THEN** `validate` 与 `prepare` 失败并指出风格与原因

#### Scenario: 无约束风格

- **WHEN** 风格清单未声明 `requires`
- **THEN** 行为与现有版本一致，不增加旁白限制
