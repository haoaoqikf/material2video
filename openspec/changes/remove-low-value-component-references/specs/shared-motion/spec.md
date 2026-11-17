## ADDED Requirements

### Requirement: 时间轴与章节轨

本能力作为可选动效参考和模板提供，MUST NOT 要求所有作品采用或安装主项目SDK。作品只对实际采用的组件承担下列行为约束；未采用的参考不得成为运行依赖，失去消费者的通用包装可删除。

系统 SHALL 在采用时本地提供 `Timeline` 与 `ChapterTrack`。事件显隐和当前章节 MUST 只由数值与显式 `progress` 决定。标签密集时组件 MUST NOT 自动避让或截断，由调用方负责。

#### Scenario: 时间轴与章节展示
- **WHEN** 时间轴或章节轨以显式进度求值
- **THEN** 时间轴只显示已到达的事件，章节轨按该进度高亮当前章节

## MODIFIED Requirements

### Requirement: 共享动效组件以进度为唯一时间输入

本能力作为可选动效参考和模板提供，MUST NOT 要求所有作品采用或安装主项目SDK。作品只对实际采用的组件承担下列行为约束；未采用的参考不得成为运行依赖，失去消费者的通用包装可删除。

系统 SHALL 在采用时本地提供共享 L1 组件：`FadeIn`、`SlideIn`、`ZoomIn`、`Blur`、`Glow`、`DrawLine`；以及 L2 组件：`RollingNumber`、`MarkerHighlight`、`BarGrowth`、`Callout`。

每个组件 MUST 只接受 `progress`（0–1）、显式 `easing`、几何与样式参数作为动画输入，MUST NOT 读取挂钟时间、帧号、上一帧状态、计时器、rAF、CSS 动画或 Remotion context。相同 `progress` 与相同参数 MUST 产生相同输出。随机性 MUST 只来自显式 `seed`，未提供时 MUST 使用固定默认种子。

#### Scenario: 同一进度重复求值
- **WHEN** 同一组件以相同参数和 `progress` 求值两次
- **THEN** 两次输出一致，不受调用时刻、调用顺序或录制模式影响

#### Scenario: pure-time 场景使用
- **WHEN** 一个声明 `capture.mode: "pure-time"` 的场景使用动效参考实现
- **THEN** 正序、倒序与并行块采集得到同一帧一致的结果，不因时间源失败

#### Scenario: 显式种子
- **WHEN** `MarkerHighlight` 以相同 `seed` 和 `progress` 重录
- **THEN** 草图几何一致，不使用隐式随机源

## REMOVED Requirements

### Requirement: 结构与波形组件
**Reason** 象形图与波形参考退役，时间轴与章节轨的现有行为收录于同名要求。
**Migration** 独立作品的本地副本可继续使用。
