## Why

现有七级制作门与声明式画面合同要求过早编排全片，增加试制与后期记录负担。资源应优先用于研究、创意比较和实际视觉验证。

## What Changes

- 三阶段改为研究与创意试制、正式设计、制作与验收，后两阶段仅保留完整设计与预演、制作迭代和验收交付。
- **BREAKING** 删除 G0–G6、检查点合同与声明式画面量测，统一独立试制评审和终审接口；旧报告明确拒绝，不迁移。
- 保留技术 QA、事实许可、隔离评审、摘要和范围绑定、问题闭环、基线与渲染候选复用。
- 同步制作指南、阅读路由、七部示例与权威规格。

## Capabilities

### New Capabilities
- `media-bound-production-review`: 不依赖全片合同的媒体绑定评审、问题与状态。

### Modified Capabilities
- `video-production-workflow`: 三阶段及创意试制优先。
- `stage-guidance-routing`: research/design/production 阅读入口。
- `checkpoint-based-visual-acceptance`: 移除全部检查点门能力。
- `production-status-ledger`: 替换门台账为当前周期的媒体评审状态。
- `independent-subagent-review`: 替换检查点绑定，保留独立观察、终审资格与失败闭环。

- `modular-video-production`: 统一新评审接口与技术导出边界。
- `single-pass-delivery`: 全片预演与评审复用缓存，不额外编码全片。
- `us-top10-market-cap-silent-video`: 交付完成条件引用新媒体评审契约。
- `visual-expression-inspiration`: 创意总纲及研究试制循环。

- `react-code-scenes`: 删除隐藏量测代理，保留实际绘制与确定性能力。

## Impact

涉及 production、CLI、文档生成器、共享画面探针及测试；不改变五类、project v2、分镜 v9和渲染契约，不增加依赖。
