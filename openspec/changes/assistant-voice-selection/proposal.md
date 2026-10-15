## Why

重新导出目前会沿用默认音色或缓存，缺少面向内容的选音环节，且交付无法直接追溯实际音色。需要把制作助手的选择固化为可验证的作品属性。

## What Changes

- 制作助手先查询可用音色，按完整旁白选择并记录理由，然后自动继续制作。
- **BREAKING**：有自身旁白但没有明确音色的作品在 prepare 阶段失败；无旁白作品不受影响。
- 增加助手选择记录与旁白摘要绑定；实际合成参数、来源进入准备指纹和成片溯源。
- 更新共享工作流、三个固定示例，并为三个当前作品重新选音及成片。

## Capabilities

### New Capabilities
- `assistant-voice-selection`：助手选音、配音门禁、过期检测与实际参数溯源。

### Modified Capabilities
无。

## Impact

共享 TTS 层以及文章、general、素材剪辑的配音准备；Skill、配音契约、README、测试和固定示例。不增加外部模型服务或 TTS 后端。
