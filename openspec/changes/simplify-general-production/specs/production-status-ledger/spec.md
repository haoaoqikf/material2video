## MODIFIED Requirements

### Requirement: 状态层必须与唯一问题表和任务清单分工

`outputs/visual-notes.md` MUST 继续作为唯一问题表，保存问题现象、处理历史和复查依据。状态层 MUST 只引用问题 ID，MUST NOT 复制问题详情。OpenSpec 任务清单 MUST 继续作为工作计划，MUST NOT 用勾选状态替代门证据。

问题机器状态 MUST 仅为 open/closed。文字未解决与待复查映射 open，已关闭映射 closed；接受保留 MUST 仅用于非必改项，映射 open 且 required=false，并在正文记录取舍和影响，不计为解决。必改性质和独立复查关闭规则保持有效。

#### Scenario: 状态引用问题

- **WHEN** 状态卡显示未关闭问题 `V07`
- **THEN** 问题现象、修改和复查记录只在唯一问题表中，状态层提供链接或 ID

#### Scenario: 任务已完成但门未通过

- **WHEN** 某个任务勾选完成，但对应门的证据或评审缺失
- **THEN** 该门仍显示未完成，任务勾选不构成通过依据

#### Scenario: 修改尚未复查
- **WHEN** 原问题代码已修改但缺当前复查
- **THEN** 正文记待复查，机器保持open，不重复建立状态表
