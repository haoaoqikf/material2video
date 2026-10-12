## Why

按历史跨度自动延长金融视频，导致同类作品时长不一致。用户要求所有金融视频统一为 60 秒，以便保持稳定、可比较的观看节奏。

## What Changes

- 所有新生成的金融 v8 计划默认总长统一为 60 秒，仍采用 1 秒开场、57 秒推进、2 秒静止终幕。
- 显式 `--duration-seconds` 设置仍有效；既有计划不自动修改。
- 使用统一入口重新生成 NVIDIA 60 秒视频，并经完整预演、评审和正式渲染替换旧成片。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `financial-timeseries-video`: 所有日期跨度的新金融 v8 计划统一默认 60 秒。

## Impact

- 影响金融默认时长选择、相关测试、README、金融 Skill 参考和 OpenSpec 规格。
- 更新忽略目录中的 NVIDIA 计划与成片；不修改其原始行情、日期范围及截止日。
