# single-pass-delivery Specification

## Purpose
统一三种视频类型的候选生成、片段检查、验收重试与可靠交付，避免同一版本完整预演后再次完整编码，使真实检查的文件与最终交付保持一致。

## Requirements

### Requirement: 同版本全片只生成一次
系统 MUST 绑定输入、实现、参数、完整帧数与文件摘要复用候选。验收及交付失败 MUST 保留候选，重试 MUST NOT 重渲染，并发生成 MUST 拒绝。
#### Scenario: 重复执行
- **WHEN** 同版本存在有效候选
- **THEN** 再次 render 只验收和交付，不新增全片生成
#### Scenario: 损坏或过期
- **WHEN** 输入变化或候选摘要不符
- **THEN** 拒绝复用，允许重新生成；失败不覆盖旧交付

### Requirement: 片段检查按需生成
preview MUST 默认前十秒且严格短于全片，支持起止时间，显式完整范围 MUST 拒绝。general 准备 MUST 不录制全片，检查 MUST 只采集所需场景与帧，状态动画保持顺序推进。
#### Scenario: 中段样片
- **WHEN** 指定中段时间
- **THEN** 不录制无关场景，字幕与声音按原始时间轴对齐

### Requirement: 候选状态及评审
系统 MUST 报告准备、候选待验收、验收失败、可交付和已交付状态，可选评审 MUST 绑定当前候选摘要，不使用旧预演记录。
#### Scenario: 失败重试
- **WHEN** 候选验收失败
- **THEN** 状态含失败原因，保留候选与旧交付

### Requirement: 分段渲染仍是同一次全片生成

`--jobs > 1` 的内部分段 SHALL 被视为同一次全片生成：系统 SHALL 在全部段渲染、逐段验收、拼接与总帧数复核通过后，才把候选交给既有交付绑定。任一段失败 SHALL NOT 产生可复用候选，也 SHALL NOT 覆盖旧交付。`--jobs` SHALL NOT 进入候选绑定；同一版本以不同 jobs 再次渲染时 SHALL 复用已完成候选，而不是重新编码。

#### Scenario: 分段生成成功

- **WHEN** 同版本以 `--jobs 2` 完成一次全片分段渲染
- **THEN** 只产生一个候选，后续同版本 render 复用该候选，不因 jobs 变化重渲染

#### Scenario: 分段生成失败

- **WHEN** 任一段失败或拼接后帧数不符
- **THEN** 不登记候选、不覆盖旧交付，重试仍走同一次生成流程
