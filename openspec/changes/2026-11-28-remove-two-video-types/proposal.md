## Why

收缩公开视频类型，集中维护图文动效、数据演化与三维空间的统一制作链路。

## What Changes

- **BREAKING** 移除原理隐喻 `principle-metaphor` 和纪实素材剪辑 `documentary-edit` 的类型身份、初始化材料、示例与展示入口。旧项目类型由目录校验直接拒绝。
- 三部独立示例继续覆盖数据演化和三维空间。图文动效继续支持初始化。
- 省略旁白后端时统一使用 edge-tts。保留显式选择 Kokoro、Qwen3-TTS 的能力。
- 同步当前规范、制作指引和待实施风格提案的适用范围。

## Capabilities

### New Capabilities

- `three-video-types` 接替统一类型、分镜与示例身份规范。

### Removed Capabilities

- `five-video-types` 整体移除。

### Modified Capabilities

- `modular-video-production` 收缩目录登记与统一制作入口。
- `standalone-video-projects` 收缩固定示例集合。
- `speech-synthesis-backends` 统一省略后端时的默认值。
- `assistant-voice-selection` 按当前支持类型应用已有选音契约。
- `article-media-assets`、`article-sound-effects`、`article-workspace`、`example-media-recovery`、`explainer-mechanism-review`、`keynote-design-system`、`material-sourcing`、`react-code-scenes`、`reference-media-acquisition`、`remotion-renderer`、`render-provenance`、`scene-events`、`scene-transitions`、`single-pass-delivery`、`solar-system-journey-video`、`subtitle-presentation`、`video-frame-rate`、`video-production-workflow` 同步当前类型范围。

## Impact

影响类型目录、独立运行时和模板、Web 配置、示例工程、展示站、制作指引与测试。旧归档和发布记录保留原文。
