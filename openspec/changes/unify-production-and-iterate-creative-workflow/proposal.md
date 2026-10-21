## Why

当前制作流程能保证知识解释与技术合格，但缺少在精制前淘汰平庸创意、反复试制和回退的实际约束。双档位把流程质量与特定三维表现绑定，需要合并并通过拥堵波重制验证。

## What Changes

- **BREAKING** 删除 productionProfile 与 --profile，统一 general 的制作、响度、资产审计与溯源契约，拒绝旧声明及参数。
- 新增不限固定轮数的方案、核心试制、整片预演及精制回退循环；整批候选可全部淘汰，每轮记录证据及下一轮变化。
- 取消重点镜头固定数量和8–12秒配额；表现方式、声音、超采样及后期按内容选择。
- 按新流程原位重制 traffic-jam-wave，保留旧版对照及完整替代复核证据。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `video-production-workflow`: 统一制作标准、循环选案与阶段回退。
- `article-explainer`: 移除档位及镜头配额，更新三个示例和拥堵波预算。
- `article-sound-effects`: 统一有声响度与按需声音设计。
- `article-media-assets`: 全部登记媒体许可阻断，尺寸按实际显示用途检查。
- `react-code-scenes`: 统一可选质量控制与缓存。
- `remotion-renderer`: 删除档位分支并保留统一交付与溯源。

## Impact

涉及 general 校验、CLI、准备缓存、录制、混音、QA、素材审计、测试及制作 Skill；同步 README 和三个固定示例。视频与检查媒体不入库，不新增审批或审美评分，不承诺播放量。
