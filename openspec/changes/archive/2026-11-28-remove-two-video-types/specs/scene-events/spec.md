## MODIFIED Requirements

### Requirement: 幕内事件声明与校验

三类统一分镜 v9 SHALL 接受可选 events 数组，每幕最多 1024 项，每项只含非空 id 和非负整数 frame；同幕 ID SHALL 唯一，事件 SHALL 位于实际幕长的半开区间内。未知实际时长时 SHALL 在 prepare 确定时长后校验。

#### Scenario: 非法事件
- **WHEN** 声明重复 ID、非法帧或超出实际幕长的事件
- **THEN** 校验或准备明确失败，不截断事件或延长幕
