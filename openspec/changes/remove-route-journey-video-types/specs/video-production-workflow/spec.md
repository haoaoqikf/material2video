## MODIFIED Requirements

### Requirement: 类型专用指南必须接入项目级视觉与运动知识

内置类型的制作指南（`building-construction`、`financial-timeseries`、`vehicle-showcase`）在涉及画面与运动判断时 SHALL 链接 `.agents/skills/frontend-design/` 与 `.agents/skills/motion-design/` 及其视频适配，并按该类型的实际需要指向具体章节。

类型指南 MUST NOT 复述通用构图、字体、颜色、层级、时长、缓动或编排理论；它只记录该类型的材料口径、镜头与画面契约、证据与验收要求。链接 MUST NOT 改变该类型的画幅、帧率、时长、材料或审核契约。

#### Scenario: 类型内判断构图或缓动

- **WHEN** 制作助手在类型专用指南内需要判断构图、层级、入场或缓动
- **THEN** 由指南链接到对应项目级 skill，而不是在类型指南里再写一套通用规则
