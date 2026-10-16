## Why

现有六模板不能表达复杂动画、3D 和动态图表。作品需要能运行本地 React 组件，并让验收与导出复用同一录制结果。

## What Changes

- **BREAKING** 通用分镜升级 v7，拒绝旧材料，不提供迁移。
- 新增 code 模板、可信作品 TSX 入口、JSON 参数和场景上下文。
- 补齐 Motion、Three.js、R3F、Drei、GSAP、ECharts；浏览器实时录制后交给现有合成链路。
- 录制缓存绑定源码、资源、参数、时间窗和实现，保留离线与完整预演门禁。

## Capabilities

### New Capabilities
- `react-code-scenes`: 本地 React 场景录制、缓存和错误边界。

### Modified Capabilities
- `article-explainer`: 通用分镜 v7，新增代码模板。
- `general-video-composition`: 通用类型改接受 v7 分镜并支持代码场景录制。
- `remotion-renderer`: 明确代码场景入口不进入 composition，导出只回放录制片段。

## Impact

影响 general 校验、准备、预演、web 依赖、三个固定示例及制作文档；金融和住宅契约不变。
