## ADDED Requirements

### Requirement: 可选全局时间与场景时间轴注入

代码场景 MAY 在 `content.props.capture` 声明 `timebase` 为 `local` 或 `global`（默认 `local`）。声明 `global` 时，录制配置 SHALL 注入 `timeline`，至少包含 `sceneStartFrame`、`sceneEndFrame` 与 `durationInFrames`；录制上下文 SHALL 提供 `globalFrame` 与 `globalSeconds`。`globalFrame` SHALL 等于 `sceneStartFrame + 幕内帧号`，子帧 SHALL 保留分数；`globalSeconds` SHALL 等于 `sceneStartFrame / fps + elapsedSeconds`。

未声明 `global` 时，录制配置 SHALL 逐字节保持既有形状，`globalSeconds` SHALL 等于 `elapsedSeconds`。既有片段缓存键 SHALL NOT 因本能力改变；声明 `global` 后，`sceneStartFrame` SHALL 进入缓存键，使前幕时长变化时正确失效。

#### Scenario: 声明全局时间

- **WHEN** 一幕声明 `capture.timebase: "global"` 且位于全片第 468 帧
- **THEN** 录制上下文在该幕第 0 帧报告 `globalFrame = 468`，第 n 帧报告 `globalFrame = 468 + n`，子帧保留小数

#### Scenario: 未声明全局时间

- **WHEN** 幕没有声明 `capture.timebase: "global"`
- **THEN** 录制配置与既有版本一致，`globalSeconds === elapsedSeconds`，旧片段缓存可继续复用

#### Scenario: 前幕时长变化

- **WHEN** 使用全局时间的幕因前幕时长变化而移动到新的全片起点
- **THEN** 该幕片段缓存失效并重新录制，全局状态按新起点求值
