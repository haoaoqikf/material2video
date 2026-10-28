## Why

两个重制示例验证了相机、跨幕时间、事件音和对象连续等方法；制作时仍缺少可浏览的组件演示、复杂对象的正确分组合成、可回放模拟与通用数值曲线。声音结构和长片叙事方法也尚未形成清晰的制作支持。

## What Changes

- 为 Painter 增加离屏分组合成和通用数值关键帧求值，并提供开发用动态能力货架与可回放模拟范例。
- 扩充声音时间包络能力，支持音乐/音效的分段层级变化与明确静音窗口。
- 在 general 制作指导中补充长片叙事结构与章节递进方法。
- 更新相关契约、制作文档、示例和验证；不重做已完成的两个风格示例。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `react-code-scenes`：增加分组离屏绘制、数值关键帧及其开发预览能力。
- `article-sound-effects`：扩展音乐和音效的时间包络与静音窗口。
- `article-explainer`：增加长片叙事组织指导。

## Impact

影响 `web/src/code-scene/painter/`、开发预览入口、通用声音契约及混音、general 制作指导和对应 OpenSpec 规格。无新增第三方依赖；分镜字段仅在声音时间包络确需材料表达时作向后兼容扩展。
