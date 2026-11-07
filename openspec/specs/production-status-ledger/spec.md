# production-status-ledger Specification

## Purpose

以当前制作周期、媒体摘要和来源依赖投影视觉评审、技术 QA、问题与基线状态，保留只读查询和证据过期诊断，避免将技术交付误报为制作完成。

## Requirements

### Requirement: 媒体评审状态只读投影
status MUST 只读展示当前周期试制、当前完整候选技术 QA、终审、问题与过期原因，不输出 G0–G6、扩展资格或自动推断创作阶段。无评审或失败 MUST 不阻断生成候选，也不得声称制作完成。

#### Scenario: 查询与渲染
- **WHEN** 执行本场景
- **THEN** 查询 MUST 不写盘；损坏历史阻止通过，技术就绪与视觉完成分别报告。
