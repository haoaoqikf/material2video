## MODIFIED Requirements

### Requirement: 风格示例必须可校验并与包分离

仓库 SHALL 在目录 `styles/<style-id>/examples/<slug>/` 为每个正式风格提供规范示例：`doc-archive/american-science-milestones`、`count-ledger/compound-interest` 与 `deep-journey/solar-system-journey`。示例 SHALL 声明其演示的 `style.id` 并通过 v8 契约校验；其旁白与文字模式 SHALL 与所属风格契约一致：`vibe-night` / `vibe-fable` 无旁白并使用屏幕字幕，`doc-archive` / `count-ledger` 无旁白且文字画在场景内，`deep-journey` 保留旁白与共享字幕。风格发现 SHALL 只读取 styles 的直接子目录，SHALL NOT 把示例目录当作风格包。示例 SHALL NOT 改变其他风格的示例集合，也 SHALL NOT 改变任何风格包的指纹。

#### Scenario: 示例不被当作风格包

- **WHEN** 运行 `m2v styles` 或 `m2v styles --json`
- **THEN** 返回五个风格包，各风格的 `examples/` 及其子目录不出现在清单中

#### Scenario: 示例改动不使作品准备失效

- **WHEN** 修改某个风格示例的文件
- **THEN** 使用该风格的作品准备指纹不变，只有该示例自身的准备需要重做

#### Scenario: 示例可校验

- **WHEN** 对 `styles/<style-id>/examples/<slug>/` 下的五个示例运行 `m2v validate`
- **THEN** 校验通过；示例按其风格声明的旁白与文字模式通过校验
### Requirement: 风格示例还原度验收

`styles/vibe-fable/examples/<slug>/` 下的每个风格示例 SHALL 按[参考风格契约](../../../../../.agents/skills/material2video/references/reference-style.md)记录八项指标，作为**证据格式**而非通过阈值：

- SHALL 产出 `outputs/style-reference.md`，逐项列出参考值、实际值与差值；八项指标准确对应契约定义的主体尺度、空场率、线宽、光源、背景质感、机位与运动、剪辑节奏、文字；
- SHALL 提供与参考样片的并排基准图，参考侧取自已登记样片的采样帧，本片侧取同叙事位置的成片帧；
- SHALL 由独立子代理执行冷审（按[独立子代理评审](../../../../../.agents/skills/material2video/references/subagent-review.md)隔离投喂），冷审结论 MUST 回应「是否同一部片的视觉系统」，并逐条列出差异项与风险；
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

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
