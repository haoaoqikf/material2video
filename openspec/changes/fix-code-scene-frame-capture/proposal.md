## Why

太阳系成片虽为 60 fps，实时浏览器录制却丢失动画状态，编码补帧造成停顿后跳动。需要让采集速度与动画时间解耦。

## What Changes

- **BREAKING**：删除实时 screencast 录制，改为受控时钟顺序逐帧采集，不提供旧录制回退。
- 同步 React、动画库、三维画布、CSS 动画与本地视频；准确校验采集和编码帧数。
- 失效旧缓存，验证三个示例并重新交付太阳系视频及旁车。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `react-code-scenes`：固定时间逐帧录制、复用与失败约束。

## Impact

涉及代码场景宿主、录制与编码、浏览器回归、示例及制作契约；不改变旁白、镜头和公开 CLI。
