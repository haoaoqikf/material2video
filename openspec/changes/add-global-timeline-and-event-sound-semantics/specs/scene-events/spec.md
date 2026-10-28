## MODIFIED Requirements

### Requirement: 声画共用事件

同一幕内事件 SHALL 同时可供画面查询与音效 `eventId` 引用；事件帧、全片帧与音效起点 SHALL 全部来自 prepare 的同一次解析，不得由画面与声音各自换算。prepare 输出的 `outputs/events.json` SHALL 记录事件所属幕、幕内帧、全片帧与音效全局帧，供制作核对。

事件未声明、事件帧越界、同一幕重复 ID、`eventId` 引用未知事件或与 `segmentId`/`offsetMs` 混用 SHALL 失败。事件帧变化 SHALL 使准备指纹与音效起点同时变化。

#### Scenario: 画面与音效引用同一事件

- **WHEN** 画面查询 `hit` 事件，同时音效声明 `eventId: "hit"`
- **THEN** 两处使用同一幕内帧；音效起点等于该事件的全片帧加允许的 `offsetFrames`

#### Scenario: 修改一次时间

- **WHEN** 将接触事件推迟 15 帧并重新准备
- **THEN** 引用它的画面动作、计数、视觉强调与音效均使用推迟后的时刻

#### Scenario: 整幕移动

- **WHEN** 前幕时长变化导致本幕起点移动
- **THEN** 事件幕内帧保持，事件全片帧与音效共同移动

#### Scenario: 事件移动

- **WHEN** 作者把 `hit` 事件从第 15 帧改到第 30 帧并重新 prepare
- **THEN** `outputs/events.json`、画面事件帧与音效起点一起移动，旧准备记录失效

#### Scenario: 未知事件

- **WHEN** 音效引用未在当前幕声明的 `eventId`
- **THEN** 校验或 prepare 失败并指出事件 ID 与所属幕
