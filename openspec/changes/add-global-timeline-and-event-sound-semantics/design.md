## Context

v8 代码场景在录制页按幕挂载，`useSceneContext().elapsedSeconds` 是幕内时间。跨幕连续行为目前只能由作者在每幕 `content.props.clock.startSeconds` 重复声明全片起点；一旦幕长变化，所有后续幕都要手工同步。pigeon 示例的 `birdAct(globalSeconds, chapterId)` 还按幕 ID 切换转向/啄食，导致同一动作在幕界跳变。

声音侧已有 `scenes[].events` 与 `soundtrack.effects[].eventId`，prepare 会解析幕内帧、全片帧与音效起点并输出 `outputs/events.json`。但示例仍用 `offsetFrames` 硬定位，声音语义只存在于作者脑中。

## Decisions

### 1. 全局时间 opt-in，不改变既有配置

在 `content.props.capture.timebase` 声明 `global` 时，`scene_config` 增加：

```json
"timeline": {
  "sceneStartFrame": 468,
  "sceneEndFrame": 576,
  "durationInFrames": 108
}
```

`SceneContext` 计算：

```ts
globalFrame = sceneStartFrame + elapsedSeconds * fps
globalSeconds = sceneStartFrame / fps + elapsedSeconds
```

未声明时 `scene_config` 不增加任何键，`globalSeconds === elapsedSeconds`。这样既有作品、准备指纹与片段缓存都不变；声明后的作品在前幕时长变化时正确失效并重新全局求值。

`sceneStartFrame` 进入片段缓存键：它改变全局时间输入，必须让旧片段失效。

### 2. 行为轨迹是作品内纯函数，镜头只取景

pigeon 示例保留六幕作为六个镜头（切镜仍是分镜选择），但把行为收敛为一个 `act(globalSeconds)`：

- 位置、朝向、啄食、点头、步态、转圈轨迹全部由全片时间窗口决定；
- 不接收 `chapterId`，不读取 `clock`；
- 每个场景只决定镜头表（`SHOT`）与字幕，箱子、食槽、计时器仍是同一房间坐标。

这不是新的分镜 DSL：行为轨迹留在作品 `scenes/` 内，现有 `props.shots`/幕结构不变。

### 3. 声音语义用现有事件，不新增混音字段

每个语义事件在所属幕声明 `events`，画面用 `config.eventFrames`/`createSceneEvents` 查询，音效用 `eventId` 引用；prepare 的 `scene_events.resolve` 继续作为唯一时间源。

示例的声音语义：

| 角色 | assetId | 表达 |
|---|---|---|
| 计时 | `tick` | 事件密度（每秒一次，临近喂食更密）与 `gainDb` |
| 食槽打开/接合 | `latch` | 单次机械声 |
| 食物到达 | `grain` | 单次落料声，第二次略强 |
| 转圈 | `swish` | 重复动作，按圈触发 |
| 揭示 | `chord` | 收束和弦 |

`intensity` 是合成配方的固定参数，不能逐事件改；需要不同质感时用不同 `seed`/`intensity` 预生成不同 `assetId`，现有 `m2v general sounds import` 已支持。

### 4. 不新增 pitch

现有素材区分、事件密度、`gainDb` 与 `fade` 足以覆盖计时、到达、接合、揭示四类语义。effect 级 pitch 会改动混音契约、缓存键与既有音效，本轮不做。若后续证明必须用音高，最小方案是给 `sound_synthesis.recipe` 增加可选半音参数（-12..12，缺省不写键），生成时缩放频率并保持时长；不改 `audio.Effect/mix`。

## Risks

- **全局时间失效范围**：只有 opt-in 场景受影响；`sceneStartFrame` 进入缓存键会让移动幕位置后重录该幕，这是正确代价。
- **示例纯性**：pigeon 仍走顺序采集（本变更不改采集模式）；后续 `add-pure-time-scene-capture` 再声明 pure-time。`useSceneContext().elapsedSeconds` 的既有语义不变。
- **声音与画面漂移**：事件帧与音效起点都由 prepare 解析；改事件后必须重新 `prepare`，`outputs/events.json` 是核对依据。
