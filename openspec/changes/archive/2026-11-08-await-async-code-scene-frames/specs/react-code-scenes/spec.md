## ADDED Requirements

### Requirement: 受控帧等待已登记异步绘制

场景上下文 SHALL 提供waitForFrame(task)登记PromiseLike异步绘制工作。宿主 MUST 在初始就绪及每次帧或子帧提交完成前，等待已登记工作、链式新增工作与最终浏览器绘制屏障；等待 MUST NOT 推进作品时间。非法任务、登记任务拒绝、未在既有deadline内完成或同一宿主重叠提交 MUST 明确失败，MUST NOT 把旧画面作为新帧发布。未登记异步工作不获得完成或确定性保证；既有源码限制与pure-time正反序检查 MUST 保持。

#### Scenario: 异步Canvas完成后采集

- **WHEN** 场景按当前帧生成Bitmap并登记绘制Promise
- **THEN** 对应帧只在Bitmap绘制完成及paint后采集，顺序与pure-time任意定位得到对应状态

#### Scenario: 初始及启动工作

- **WHEN** 场景在初始ready前或start触发的effect中登记绘制
- **THEN** 初始就绪或首帧提交等待这些工作，不因多个ready调用提前放行

#### Scenario: 异步工作失败

- **WHEN** 已登记任务拒绝或长期不完成
- **THEN** 异常或既有超时使采集失败，不发布有效采集、缓存或准备

#### Scenario: 非法任务与重叠提交

- **WHEN** 调用传入非PromiseLike，或上一帧提交尚未完成就请求下一次提交
- **THEN** 宿主明确拒绝，不能清除正在执行的帧或静默采集旧画面

#### Scenario: 同步场景

- **WHEN** 场景未登记异步绘制任务
- **THEN** 继续按既有受控时间、帧序和绘制行为采集；实现源码摘要变化仍按既有规则使旧缓存失效
