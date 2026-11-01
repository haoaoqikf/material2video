## MODIFIED Requirements

### Requirement: 任务与阶段决定主要阅读入口

Skill SHALL 按视频类型和新制作、修订、评审、排查任务分流；general 三阶段 SHALL 各有唯一短主指南。条件参考 SHALL 具备明确触发条件，适用时必须读取；讲解片设计和核心试制 SHALL 优先强调四种按需讲解机制，不要求全部使用。

制作入口 SHALL 把两个项目级 skill 登记为条件参考与规则归属：`frontend-design` 负责视觉方向、字体、构图、层级、反模板判断与自我批评；`motion-design` 负责镜头运动、转场、入场退场、缓动和节奏。方案确定阶段 SHALL 在读形象与构图时接入视觉设计 skill；制作与迭代阶段 SHALL 在首次设计镜头运动时接入运动 skill；最终验收 SHALL 在盲看落盘后使用两者核对实际画面。两个 skill MUST NOT 改变阶段、门禁、审核人数、问题分级或证据有效性。

#### Scenario: 局部修订
- **WHEN** 用户要求修订已有作品
- **THEN** 从修订入口定位受影响阶段及专项，不重新默认读取全部制作文档

#### Scenario: 专用类型
- **WHEN** 类型是金融或自驾路线
- **THEN** 路由指向该类型专用契约，不套用 general 三阶段

#### Scenario: 画面审美判断
- **WHEN** 助手需要判断构图、色彩、字体、留白、视觉重心或画面是否模板化
- **THEN** 从入口或条件参考到达 `frontend-design`，先观察后判断

#### Scenario: 运动设计
- **WHEN** 助手需要设计或复核镜头运动、转场、入场退场与缓动
- **THEN** 从入口或条件参考到达 `motion-design`，按其帧驱动适配规则执行
