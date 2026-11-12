## What Changes

- 新增 `content.props.capture.timebase`（`local`/`global`，默认 `local`）。声明 `global` 时，录制配置注入场景在全片时间轴上的 `timeline`，录制上下文提供 `globalFrame`/`globalSeconds`；未声明时配置逐字节不变。
- 声音变化使用现有能力表达：事件密度、`gainDb`、`fade` 与不同素材/合成变体；本变更不新增 pitch，不改混音契约。

## Capabilities

### New Capabilities

无。不新增视频类型、命令或风格包。

### Modified Capabilities

- `react-code-scenes`：新增 opt-in 全局时间注入与 `globalFrame`/`globalSeconds` 上下文。
- `scene-events`：明确同一语义事件被画面与音效共同引用，事件帧、全片帧与音效起点同源于 prepare。
- `article-sound-effects`：明确用事件密度、素材选择、增益与淡化表达语义变化，不要求新增音高参数。

## Impact

- 代码：`src/m2v/types/general/code_scenes/config.py`、`web/src/code-scene/context.ts`、`web/src/code-scene/host.tsx`。
- 文档：`code-scene-runtime.md`、`explainer-design.md`、`article-media-and-sound.md`、`storyboard-schema.md`。
- 未声明 `capture.timebase: "global"` 的既有作品配置、缓存键与行为保持不变。

通用代码场景目前只向作品提供幕内时间，连续行为要靠每幕手写全片起点；声音虽然已有幕内事件与 `eventId` 引用，但示例仍用帧偏移硬定位，没有形成作品内的声音语义约定。拟由一条全局时间状态轨迹驱动连续行为，各镜头只取景；声音与画面共用同一语义事件。本变更把这两项落成 opt-in 能力。

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
