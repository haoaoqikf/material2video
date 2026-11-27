## Why

旧修订流程会持久化候选和重置基线，包括重复媒体、记录和源码，旧清理目标也容许完整历史版本常驻。

## What Changes

- 所有作品的旧版本基线保留数量设为 0，小修和整体重做都直接更新当前工程。
- **BREAKING** 退役 `m2v baseline create|prune` 与状态中的旧基线投影。
- 清理本地作品中确认的旧基线和专属副本，归还仍需保留的独立评审原件，说明已不可复核的历史引用。
- 沿用当前交付替换和评审核验。仓库根目录的完整退役示例留存。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `remake-baseline-retention` 将旧基线保留量改为 0，规范存量清理边界。
- `media-bound-production-review` 保留独立评审原件和失败历史，处理已清理的旧媒体引用。
- `production-status-ledger` 移除旧基线状态，继续展示当前技术与视觉证据。
- `solar-system-journey-video` 采用统一的旧基线清理规则。

## Impact

更新主项目 CLI、制作规范、状态、示例历史记录及针对性测试。存量清理只涉及本机已核实的旧基线和专属副本。
