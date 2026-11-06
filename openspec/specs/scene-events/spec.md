# 幕内统一事件

## Purpose

为通用作品提供唯一的幕内事件时间声明，使动画、计数、视觉强调与音效可以共同引用，并确保准备、局部采集和全片生成使用同一份确定性结果，减少改动节奏时的重复维护与错位。

## Requirements

### Requirement: 幕内事件声明与校验

五类统一分镜 v9 SHALL 接受可选 events 数组，每幕最多 1024 项，每项只含非空 id 和非负整数 frame；同幕 ID SHALL 唯一，事件 SHALL 位于实际幕长的半开区间内。未知实际时长时 SHALL 在 prepare 确定时长后校验。

#### Scenario: 非法事件
- **WHEN** 声明重复 ID、非法帧或超出实际幕长的事件
- **THEN** 校验或准备明确失败，不截断事件或延长幕

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

### Requirement: 确定性查询与可追溯准备

SDK SHALL 提供明确拒绝缺失事件的帧查询及纯进度求值，不依赖跨帧状态。prepare SHALL 保存事件解析结果并输出绑定当前准备指纹的事件清单，含音效实际起点。事件变化 SHALL 进入场景录制配置和准备输入，使旧准备与相关画面缓存不再复用。

#### Scenario: 任意顺序采集
- **WHEN** 顺序、倒序或重复求值同一帧
- **THEN** 同一帧的事件状态和动画进度相同

#### Scenario: 重新准备
- **WHEN** 事件改变后重新 prepare
- **THEN** 新事件表、音效起点、准备指纹和相关场景配置共同变化，事件清单对应新的准备指纹
