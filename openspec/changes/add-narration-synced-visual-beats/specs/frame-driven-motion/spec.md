## ADDED Requirements

### Requirement: 语义动作是帧驱动的受控状态转换
系统 SHALL 支持 `establish`、`connect`、`transfer`、`accumulate`、`deplete`、`transform`、`compare`、`highlight`、`loop`、`break`、`restore`。每个动作 SHALL 由目标节点、解析区间和当前帧确定，SHALL NOT 使用 CSS 动画、挂钟或运行时随机状态。

#### Scenario: 同帧重复求值
- **WHEN** 同一个语义动作在相同输入和帧号下重复求值
- **THEN** 目标节点状态、关系与像素结果保持一致

### Requirement: 语义动作结束后留下可读状态
每个 beat SHALL 在区间结束后形成确定的完成状态；最后一个解释性 beat 完成后 SHALL 留出可配置且可机检的稳定阅读时间，默认至少 12 帧。

#### Scenario: 结论来不及阅读
- **WHEN** 最后一个 beat 在距场景结束不足 12 帧时才完成
- **THEN** 严格评审失败并报告完成帧、场景长度和剩余帧数
