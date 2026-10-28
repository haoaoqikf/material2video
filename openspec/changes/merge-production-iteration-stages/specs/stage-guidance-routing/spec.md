## MODIFIED Requirements

### Requirement: 任务与阶段决定主要阅读入口

Skill SHALL 按视频类型和新制作、修订、评审、排查任务分流；general 三阶段 SHALL 各有唯一短主指南。条件参考 SHALL 具备明确触发条件，适用时必须读取；讲解片设计和核心试制 SHALL 优先强调四种按需讲解机制，不要求全部使用。

#### Scenario: 局部修订

- **WHEN** 用户要求修订已有作品
- **THEN** 从修订入口定位受影响阶段及专项，不重新默认读取全部制作文档

#### Scenario: 专用类型

- **WHEN** 类型是金融或住宅
- **THEN** 路由指向该类型专用契约，不套用 general 三阶段
