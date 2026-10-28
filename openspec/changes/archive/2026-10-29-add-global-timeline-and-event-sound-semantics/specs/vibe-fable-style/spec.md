## ADDED Requirements

### Requirement: pigeon 示例使用全局行为轨迹与声音语义表

`styles/examples/vibe-fable/pigeon/` SHALL 用一条不依赖幕 ID 的全局时间状态轨迹驱动鸽子的位置、朝向、啄食、步态与转圈；每一幕 SHALL 只决定镜头取景与字幕，MUST NOT 用幕 ID 分支改变同一时刻的行为。示例 SHALL 通过 `content.props.capture.timebase: "global"` 获取全片时间，MUST NOT 在每幕重复手写 `clock.startSeconds`。

示例 SHALL 在作品内提供可核对的 `SOUND.md`，登记计时、食槽打开/接合、食物到达、转圈与揭示各自的 `assetId`、参数与听觉作用；`storyboard.json` 的音效 SHALL 引用语义 `eventId`，MUST NOT 用与画面脱钩的硬编码 `offsetFrames` 作为主要定位。

#### Scenario: 幕界连续

- **WHEN** 在相邻两幕的边界前后取帧
- **THEN** 鸽子位置、朝向与啄食姿态来自同一 `act(globalSeconds)`，不因换幕跳到另一套动作

#### Scenario: 声音语义可核对

- **WHEN** 检查 `SOUND.md`、`storyboard.json` 的 `events`/`effects` 与 `outputs/events.json`
- **THEN** 每个声音角色都有登记的 `assetId` 与对应 `eventId`，事件帧与音效起点一致

#### Scenario: 未声明全局时间

- **WHEN** 示例幕缺少 `capture.timebase: "global"`
- **THEN** 校验或准备明确失败，不允许回退到手写起点而静默产生跳变
