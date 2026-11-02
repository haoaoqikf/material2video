## ADDED Requirements

### Requirement: 透明整屏效果层由代码场景 SDK 导出

`m2v/code-scene` SHALL 导出 `ScreenBurstLayer` 与 `explosionField`/`moteField`/`beatPhase`/`beatPulse`，使作品可以在不直接导入第三方包的情况下绘制整屏粒子冲击与节拍脉冲。

`ScreenBurstLayer` MUST 使用透明 Canvas，内部缓冲按 `__M2V_CODE_CONFIG__.captureScale` 分配；MUST 在 React layout effect 中按当前帧同步重绘；MUST NOT 使用 `requestAnimationFrame`、`useFrame`、计时器或逐帧累积状态。MUST 支持字幕安全区下方的 alpha 淡出，MUST NOT 遮挡共享字幕层。

粒子 sprite MAY 预渲染并缓存；sprite 只承担柔光/虚化观感，颜色、数量、事件时刻 MUST 由调用方传入。新增模块 MUST 进入 `implementation_inputs()` 与源码确定性闸门。

#### Scenario: 逐帧采集

- **WHEN** 同一帧在 lookdev 与正式渲染中分别采集
- **THEN** Canvas 粒子层按同一 `frame`、seed 与 captureScale 重绘，不依赖上一帧或真实时间

#### Scenario: 字幕安全区

- **WHEN** 整屏冲击发生在字幕窗口内
- **THEN** 粒子在字幕安全区上方开始淡出，字幕文字保持可见

#### Scenario: 直接使用状态式引擎

- **WHEN** 作品或风格组件直接引入 `requestAnimationFrame` 驱动的粒子引擎
- **THEN** 源码闸门或审查明确失败，须改为 SDK 的闭式效果层
