## Why

实际通用视频的独立核心评审发现，横屏 1920px 缩至手机 393px 后，当前共享字幕 40px 只剩约 8px，无法满足该作品的可读性要求。直接改画幅清单会改变所有作品，因此需要作品级的窄范围字号配置。

## What Changes

- general 作品可在 `project.json.output.subtitle` 仅声明 `fontSize`，接受 24 至 56 的整数。
- 未配置仍严格采用现有画幅清单的默认字幕样式；其他类型声明该字段明确失败。
- 准备阶段统一解析字号并写入 `props.subtitle` 与 `inputs.subtitle`，预演、正式合成、浏览器字幕量测和 QA 共用该结果；更改配置使旧准备过期。
- 同步配置校验、定向测试、README 和制作参考文档，以文档 JSON 例与测试夹具演示 52px，不增加风格示例。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `article-explainer`：扩充作品级字幕字号契约及准备、渲染与量测的一致性。

## Impact

涉及作品描述校验、general 准备、字幕布局量测、现有 `SubtitleStyle` 消费者的验证及相关文档。复用现有画幅和合成实现，不引入依赖，不改变安全区、颜色、行高、字幕开关或其他类型默认值。
