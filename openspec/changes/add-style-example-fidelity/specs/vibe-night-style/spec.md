## ADDED Requirements

### Requirement: 风格示例还原度验收

`styles/examples/vibe-night/<slug>/` 下的每个风格示例 SHALL 按[参考风格契约](../../../.agents/skills/material2video/references/reference-style.md)记录八项指标，作为**证据格式**而非通过阈值：

- SHALL 产出 `outputs/style-reference.md`，逐项列出参考值、实际值与差值；八项指标准确对应契约定义的主体尺度、空场率、线宽、光源、背景质感、机位与运动、剪辑节奏、文字；
- SHALL 提供与参考样片的并排基准图，参考侧取自已登记样片的采样帧，本片侧取同叙事位置的成片帧；
- SHALL 由独立子代理执行冷审（按[独立子代理评审](../../../.agents/skills/material2video/references/subagent-review.md)隔离投喂），冷审结论 MUST 回应「是否同一部片的视觉系统」，并逐条列出差异项与风险；
- `m2v lookdev` 的代表帧 SHALL 覆盖每一幕，且 `lookdev.json` 与接触表 MUST 出自同一次运行。

本 Requirement SHALL NOT 规定数值下限或上限，也 SHALL NOT 要求冷审结论为「同族」；缺任一项材料视为未完成，齐全即视为过程完备。参考样片与采样帧只可作并排基准，MUST NOT 进入成片、评审包以外的地方或风格包资产。

#### Scenario: 材料齐全

- **WHEN** 风格示例产出 `style-reference.md`、并排基准图、独立冷审记录，且 `lookdev` 覆盖每幕
- **THEN** 该示例的还原度验收视为过程完备，无论冷审结论为何

#### Scenario: 缺少冷审

- **WHEN** 示例只有八项指标与并排图，没有独立子代理冷审记录
- **THEN** 还原度验收未完成，不以作者解释或指标齐全替代独立观察

#### Scenario: 代表帧与清单不同源

- **WHEN** `lookdev.json` 记录的帧与接触表所用帧不是同一次运行产生
- **THEN** 证据不可复算，还原度验收未完成，须重跑 lookdev

#### Scenario: 不把示例当交付作品

- **WHEN** 示例通过还原度验收
- **THEN** 它仍只是风格示例，不因此获得核心样片、粗片或终审记录，也不改变其非交付作品的状态
