## MODIFIED Requirements

### Requirement: beat 必须描述前后状态

启用新版导演能力的 beat SHALL 描述受控动作与它对观众的解释，并 SHALL 在需要时补充
变化前状态、变化后状态或两者的关系；仅声明入场方式不得满足语义节拍要求。

`before` / `after` / `relation` 是可选字段，声明时 SHALL 校验非空；
必填字段 SHALL 是 `id` / `action` / `targets` / `meaning`。

#### Scenario: 只有淡入动作
- **WHEN** beat 的 `action` 只表达元素出现，没有任何状态或关系变化
- **THEN** 严格动画评审失败并指出该 beat

#### Scenario: 声明了状态字段但内容为空
- **WHEN** beat 声明了 `before` 或 `after` 但取值为空字符串
- **THEN** 校验报错并指出该字段
