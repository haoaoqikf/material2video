# 幕内统一事件

## Purpose

为通用作品提供唯一的幕内事件时间声明，使动画、计数、视觉强调与音效可以共同引用，并确保准备、局部采集和全片生成使用同一份确定性结果，减少改动节奏时的重复维护与错位。

## Requirements

### Requirement: 幕内事件声明与校验

general v8 SHALL 接受可选 events 数组，每幕最多 1024 项，每项只含非空 id 和非负整数 frame；同幕 ID SHALL 唯一，事件 SHALL 位于实际幕长的半开区间内。未知实际时长时 SHALL 在 prepare 确定时长后校验。

#### Scenario: 非法事件
- **WHEN** 声明重复 ID、非法帧或超出实际幕长的事件
- **THEN** 校验或准备明确失败，不截断事件或延长幕

### Requirement: 声画共用事件

准备 SHALL 将事件提供为场景内帧表与全片绝对帧，音效 SHALL 可通过 sceneId、eventId 和可选 offsetFrames 引用事件。eventId SHALL 与 segmentId、offsetMs 互斥；引用缺失与事件偏移后起点不在所属幕内 SHALL 失败。未引用事件的音效 SHALL 保留既有定位语义。

#### Scenario: 修改一次时间
- **WHEN** 将接触事件推迟 15 帧并重新准备
- **THEN** 引用它的画面动作、计数、视觉强调与音效均使用推迟后的时刻

#### Scenario: 整幕移动
- **WHEN** 前幕时长变化导致本幕起点移动
- **THEN** 事件幕内帧保持，事件全片帧与音效共同移动

### Requirement: 确定性查询与可追溯准备

SDK SHALL 提供明确拒绝缺失事件的帧查询及纯进度求值，不依赖跨帧状态。prepare SHALL 保存事件解析结果并输出绑定当前准备指纹的事件清单，含音效实际起点。事件变化 SHALL 进入场景录制配置和准备输入，使旧准备与相关画面缓存不再复用。

#### Scenario: 任意顺序采集
- **WHEN** 顺序、倒序或重复求值同一帧
- **THEN** 同一帧的事件状态和动画进度相同

#### Scenario: 重新准备
- **WHEN** 事件改变后重新 prepare
- **THEN** 新事件表、音效起点、准备指纹和相关场景配置共同变化，事件清单对应新的准备指纹
