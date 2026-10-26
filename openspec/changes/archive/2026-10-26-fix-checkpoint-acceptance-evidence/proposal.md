## Why

检查点的通用报告不能证明视觉事件与设计兑现已覆盖；规则采样可能跳过短暂状态边界；等待上游被误记为证据过期。这三项影响验收可信度及返工成本。

## What Changes

- 新作品合同声明 acceptanceChecks，要求独立报告中有带证据的视觉事件与五维设计兑现记录；在制作品不追溯切换。
- 采样自动覆盖文字、状态和时间结构边界前后；可按状态时间窗断言对象数量与状态。
- 状态分列本门结果与未满足前置门，等待前置不再冒充过期。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `checkpoint-based-visual-acceptance`：完成凭据、关键边界采样及证据与前置状态分离。
- `production-status-ledger`：同步等待前置词汇、本门结果及完成条件，保留既有场景。

## Impact

修改 production 合同、采样、评审导入与状态计算及相关测试、制作参考和固定太阳系示例的独立演练。无渲染准备指纹变更，不修改在制复利作品或其他代理已有文件。不增加导出硬门禁。
