## MODIFIED Requirements

### Requirement: 评审者身份与证据必须可核验

评审记录 MUST 写明执行方式，只允许「独立子代理」「外部评审」「角色分离自审（降级）」三种。记录 MUST 包含评审者标识或调用记录、开始与结束时间、投喂文件清单、隔离方式、评审包 manifest SHA-256、报告 SHA-256 与 invocation 摘要。最终轮的 reviewerId MUST 未参与该作品前期评审；同一调用 MUST NOT 作为多个评审者；`split-final` 的两名评审者 MUST 互不读取对方报告。无法提供独立调用证据时 MUST 记为「未独立评审（证据不足）」，按降级处理。

external-review MUST 只作为补充意见，MUST NOT 作为独立完成途径或关闭适用独立项；独立完成继续要求可核验的independent-subagent。

#### Scenario: 同一调用冒充第二名终审

- **WHEN** 同一 invocation 被用于两个 reviewerId 的最终报告
- **THEN** 拒绝导入，不产生通过事件

#### Scenario: 只有角色标签

- **WHEN** 记录写「独立子代理」但没有投喂文件清单与隔离条件
- **THEN** 视为未完成，补做独立评审或改记降级自审

#### Scenario: 外部评审

- **WHEN** 用户或另一个独立会话按同一评审包完成评审
- **THEN** 可记为「外部评审」，但不得声称真实观众测试或外部导演评审

#### Scenario: 导入外部意见
- **WHEN** 外部评审报告合法且有具体观察
- **THEN** 保存补充意见，独立完成项仍等待合格子代理观察


### Requirement: 分门评审包必须绑定门与检查点

评审包 MUST 记录轮次、门和覆盖场景/检查点/窗口、证据类型、尺寸、摘要与被排除文件。同轮报告 MUST 能引用多个门的检查事件，完整校验后幂等登记，不要求重复报告。blind 包 MUST 排除设计、分镜、源码、旧结论与预期答案；consistency 包 MUST 只在 blind 观察落盘后提供，且只能给目标图与中性条件。两阶段可同一代理执行，一致性不得替代盲审。

manifest文档示例 MUST 从实际打包器的字段构建逻辑生成，文档同步检查 MUST 检测漂移，不手写另一套level/stage/displaySize字段。

#### Scenario: 精简审核的适用判断

- **WHEN** 核心轮同时观察目标图与动态风险
- **THEN** 分步提供净化证据，同一轮覆盖多个适用门，不能将目标条件提前泄露给动态盲看

#### Scenario: 场景评审包

- **WHEN** 生成 G4 场景单元评审包
- **THEN** manifest 记录门 `G4`、检查点 ID、场景窗口时间码、显示尺寸和证据摘要

#### Scenario: animatic 盲审包

- **WHEN** 生成 G3 animatic 盲审包
- **THEN** 包内只有 animatic 证据和中性问题，不含设计合同、分镜或制作理由

#### Scenario: 一致性审查读取合同

- **WHEN** 对合同与分镜做设计→实现一致性审查
- **THEN** 评审者可读取合同和分镜，但结论只能记录自洽性或结构问题，不能替代盲审美评审

#### Scenario: 打包字段改变
- **WHEN** 打包器manifest字段发生变化
- **THEN** 文档同步重新投影同一字段形状，--check在投影未更新时失败
