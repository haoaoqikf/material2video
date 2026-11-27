## MODIFIED Requirements

### Requirement: 片段检查按需生成
preview MUST 默认前十秒且严格短于全片，支持起止时间，显式完整范围 MUST 拒绝。三类作品准备 MUST 不录制全片，检查 MUST 只采集所需场景与帧，状态动画保持顺序推进。
#### Scenario: 中段样片
- **WHEN** 指定中段时间
- **THEN** 不录制无关场景，字幕与声音按原始时间轴对齐
