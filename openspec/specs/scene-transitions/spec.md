# scene-transitions Specification

## Purpose

为通用视频提供可重复求值的镜头间转场，使硬切、淡化、滑动、擦除和圆形揭示共享统一名称及帧数语义，在现有录制片段、旁白与字幕时间轴之上复用成熟合成组件，而不要求作品手写镜头切换。

## Requirements

### Requirement: 统一场景转场

general MUST 支持 cut、fade、crossfade、slide-left、slide-right、wipe-left、wipe-right、iris、clock-wipe。名称与方向 MUST 由跨 Python/Web 单一登记来源定义，首幕 MUST cut，未知名称 MUST 拒绝。非 cut 转场使用现有 transitionFrames 重叠窗口，不得新增帧或挪动旁白/字幕；正式回放、静帧和局部预演 MUST 使用一致的进度与偏移语义。

本地播放器的媒体服务 MUST 支持单段字节 Range，不得要求为正确定位视频而开启 CORS；默认跨域策略保持关闭。

转场实现或登记变化 MUST 使结构试验与全片证据过期，MUST NOT 仅因此使无关的独立场景源采集证据过期。

#### Scenario: 多幕重叠
- **WHEN** 两幕通过 N 帧转场连接
- **THEN** 合成总帧数为两幕帧数之和减 N，字幕仍按原全局窗口出现

#### Scenario: 单帧与局部范围
- **WHEN** 转场为 1 帧或仅回放包含转场的局部窗口
- **THEN** 无除零、帧数漂移或媒体起点偏移错误

#### Scenario: 本地媒体定位
- **WHEN** 同源播放器请求局部视频字节区间
- **THEN** 返回有效的 206 范围，不因默认未启用 CORS 而退回整文件响应
