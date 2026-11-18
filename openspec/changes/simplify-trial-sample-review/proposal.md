## Why

研究试制阶段需要快速看到完整动作，用户要求取消动态样片的独立评审，以抽帧和技术信号复核过程，并明确保留关键帧的独立盲审。

## What Changes

- 研究试制动态样片由总代理核对完整解码、动作连续性和适用信号，删除原生样片的过程送审、过程报告及交付门禁。
- **BREAKING** `sample review` 只受理关键帧，移除例外过程盲审选项。 `sample deliver` 移除 `--process-id`。
- 原生及正式关键帧保留独立盲审与同轮目标对照，正式关键片段沿现行独立审核策略。
- 旧试制动态评审证据保留为历史，旧失败退出当前必审范围。

## Capabilities

### Modified Capabilities

- `media-bound-production-review`：限制原生试制过程的评审入口。
- `native-design-samples`：删除动态样片的独立过程审核门禁。
- `independent-subagent-review`：区分试制关键帧与正式关键片段的独立审核。
- `video-production-workflow`：明确试制动态过程的总代理观察责任。
- `compound-interest-explainer-video`：同步复利示例的代表性试制要求。

## Impact

样品 CLI、评审入口及交付、历史问题的活动投影、实施指南与相关测试。当前复利样片会按新规则完成完整过程检查和关键帧评审。
