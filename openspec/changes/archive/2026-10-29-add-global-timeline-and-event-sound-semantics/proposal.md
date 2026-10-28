## Why

通用代码场景目前只向作品提供幕内时间，连续行为要靠每幕手写全片起点；声音虽然已有幕内事件与 `eventId` 引用，但示例仍用帧偏移硬定位，没有形成作品内的声音语义约定。外部参考项目 `pigeon_B` 的做法说明：先写一条全局时间状态轨迹，各镜头只取景；声音与画面共用同一语义事件。本变更把这两项落成 opt-in 能力，并重做 `vibe-fable` 的 pigeon 示例。

## What Changes

- 新增 `content.props.capture.timebase`（`local`/`global`，默认 `local`）。声明 `global` 时，录制配置注入场景在全片时间轴上的 `timeline`，录制上下文提供 `globalFrame`/`globalSeconds`；未声明时配置逐字节不变。
- pigeon 示例把 `birdAct(globalSeconds, chapterId)` 改为不依赖幕 ID 的 `act(globalSeconds)`，六幕只保留镜头取景；移除手写的 `content.props.clock.startSeconds`。
- pigeon 示例把声音改为幕内语义事件：计时、食槽打开、食物到达、转圈、揭示各自声明事件，`soundtrack.effects` 用 `eventId` 引用；新增作品内 `SOUND.md` 声音语义表。
- 声音变化使用现有能力表达：事件密度、`gainDb`、`fade` 与不同素材/合成变体；本变更不新增 pitch，不改混音契约。
- 同步制作参考文档、示例 README 与相关规格；pigeon 示例仍为风格示例，不进入 `examples/` 固定名额。

## Capabilities

### New Capabilities

无。不新增视频类型、命令或风格包。

### Modified Capabilities

- `react-code-scenes`：新增 opt-in 全局时间注入与 `globalFrame`/`globalSeconds` 上下文。
- `scene-events`：明确同一语义事件被画面与音效共同引用，事件帧、全片帧与音效起点同源于 prepare。
- `article-sound-effects`：明确用事件密度、素材选择、增益与淡化表达语义变化，不要求新增音高参数。
- `vibe-fable-style`：pigeon 示例必须使用不依赖幕 ID 的全局行为轨迹，并提供可核对的声音语义表。

## Impact

- 代码：`src/m2v/types/general/code_scenes/config.py`、`web/src/code-scene/context.ts`、`web/src/code-scene/host.tsx`。
- 示例：`styles/examples/vibe-fable/pigeon/` 的 `scenes/pigeon.tsx`、`storyboard.json`、`README.md`，新增 `SOUND.md`。
- 文档：`code-scene-runtime.md`、`explainer-design.md`、`article-media-and-sound.md`、`storyboard-schema.md`。
- 未声明 `capture.timebase: "global"` 的既有作品配置、缓存键与行为保持不变。
