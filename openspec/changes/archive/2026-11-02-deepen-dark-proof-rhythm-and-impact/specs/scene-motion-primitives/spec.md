## ADDED Requirements

### Requirement: 整屏粒子、环境微尘与节拍原语

系统 SHALL 在 `web/src/code-scene/` 提供以下纯数值原语，并从 `m2v/code-scene` 导出：

- `explosionField`：按 `progress`、显式 seed、原点、最终位移 `reach`、寿命、阻力、重力、深度范围、bokeh/streak/dust 比例求值分层粒子；返回位置、速度、年龄、尺寸、透明度、深度、模糊、角度、streak 与层名。
- `moteField`：按 `progress`、seed、画布尺寸、漂移与周期求值持续环境微尘。
- `impactEnvelope`：按 `progress` 返回闪光与环包络，端点为 0。
- `beatPhase` / `beatPulse`：按 `progress`、`durationSeconds`、BPM 与显式相位求值节拍相位与脉冲。

所有原语 MUST 只接受 0–1 `progress` 与显式参数，MUST NOT 读取帧号、挂钟、`Math.random`、上一帧状态或 DOM。相同参数与进度 MUST 产生相同输出；`explosionField` 与 `impactEnvelope` 的端点 MUST 透明或零值。`reach` MUST 表示最终最大位移，MUST NOT 因内部阻力把实际半径压缩到参数的固定小比例。粒子 MUST 按显式 seed 决定形态；改变 seed MUST 改变形态。

`beatPhase`/`beatPulse` MUST 不内置主题、颜色或事件时刻；BPM 与 duration 由调用方传入。`moteField` MUST 只做低速连续漂移，MUST NOT 用作随机闪烁或事件替代。

#### Scenario: 整屏爆炸端点与跳帧

- **WHEN** 以 `progress` 0、1 与 0.2 直接跳到 0.8 求值 `explosionField`
- **THEN** 端点全部透明，跳帧结果与逐帧求值一致

#### Scenario: 实际位移

- **WHEN** 调用方给出 `reach=1000` 与正常阻力
- **THEN** 外层粒子的最大位移接近 1000 px，而不是被阻力压到约 245 px

#### Scenario: 节拍参数

- **WHEN** 用同一 `progress`、duration 与 BPM 求值 `beatPulse` 两次
- **THEN** 结果一致；拍点附近为脉冲峰值，衰减窗口后为 0，不读帧号

#### Scenario: 状态式粒子库

- **WHEN** 以需要从 0 重放的状态式粒子引擎实现整屏冲击
- **THEN** 任意帧 seek 与纯时间采集无法满足，审查判定不符合本原语契约，须改为闭式求值
