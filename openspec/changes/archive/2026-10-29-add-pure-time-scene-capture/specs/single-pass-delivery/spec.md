## ADDED Requirements

### Requirement: 分段渲染仍是同一次全片生成

`--jobs > 1` 的内部分段 SHALL 被视为同一次全片生成：系统 SHALL 在全部段渲染、逐段验收、拼接与总帧数复核通过后，才把候选交给既有交付绑定。任一段失败 SHALL NOT 产生可复用候选，也 SHALL NOT 覆盖旧交付。`--jobs` SHALL NOT 进入候选绑定；同一版本以不同 jobs 再次渲染时 SHALL 复用已完成候选，而不是重新编码。

#### Scenario: 分段生成成功

- **WHEN** 同版本以 `--jobs 2` 完成一次全片分段渲染
- **THEN** 只产生一个候选，后续同版本 render 复用该候选，不因 jobs 变化重渲染

#### Scenario: 分段生成失败

- **WHEN** 任一段失败或拼接后帧数不符
- **THEN** 不登记候选、不覆盖旧交付，重试仍走同一次生成流程
