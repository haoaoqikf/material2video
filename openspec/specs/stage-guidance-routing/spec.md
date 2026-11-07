# stage-guidance-routing Specification

## Purpose

为五类视频提供研究与创意试制、正式设计、制作与验收三个渐进阅读入口，使助手按当前问题读取唯一权威指导，减少重复规则、阶段交接和无信息增量的记录。

## Requirements

### Requirement: 三阶段唯一阅读入口
阅读路由 MUST 使用 research/design/production 三个唯一主指南；创作总纲保持必读，详细研究与隔离评审按需展开；重复阶段指南及跳转页 MUST 删除，活动链接和 JSON 示例 MUST 有效。

#### Scenario: 读取当前阶段
- **WHEN** 执行本场景
- **THEN** 入口 MUST 指向对应阶段，不要求递归阅读所有参考。
