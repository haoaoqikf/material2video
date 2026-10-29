## ADDED Requirements

### Requirement: 可选纯时间采集

代码场景 MAY 在 `content.props.capture` 声明 `mode: "pure-time"`。pure 场景 MUST 只由 `elapsedSeconds`、`globalSeconds`、`props` 与 `eventFrames` 推导画面，MUST NOT 依赖计时器、随机源、CSS 动效、`useFrame`、ECharts 动画或自走媒体播放。`pure-time` SHALL 隐含 `timebase: "global"`。`jobs` SHALL 为 1–4，`blockFrames` SHALL 默认等于 fps，`verifyFrames` SHALL 为 2–4。

pure 模式 SHALL 支持绝对 seek：允许跳帧与倒序，并 SHALL 在挂载前把块首帧写入录制页，使页面从块首时间开始。片段 SHALL 按 `blockFrames` 对齐并可按块并行采集；块可复用缓存。未声明 pure 的场景 MUST 保持既有顺序采集、配置与缓存键。

pure 场景 MUST 通过静态源码闸门与动态探针：探针帧正序与倒序截图 PSNR ≥ 60 dB，相邻块边界见证帧一致。任一失败 SHALL 明确拒绝 pure 模式并指出场景与帧号，MUST NOT 静默回退顺序采集或发布未验证片段。

#### Scenario: 直接取任意帧

- **WHEN** pure 场景请求第 1200–1500 帧窗口
- **THEN** 采集直接从第 1200 帧开始，不推进第 0–1199 帧；帧内容与顺序采集的同一帧等价

#### Scenario: 未声明 pure

- **WHEN** 场景没有声明 `capture.mode: "pure-time"`
- **THEN** 仍按连续帧顺序采集，配置与片段缓存键保持既有形状

#### Scenario: 伪纯场景

- **WHEN** pure 场景使用计时器、随机源或自走动画，导致倒序探针与正序结果不一致
- **THEN** 采集失败并指出场景与帧号，不写 receipt、不发布缓存

#### Scenario: 分块并行

- **WHEN** pure 场景声明 `jobs: 2` 并请求完整区间
- **THEN** 各块独立采集后无损拼接，总帧数、尺寸、帧率与单进程结果一致

#### Scenario: 块级复用

- **WHEN** 先预览某窗口、再渲染全片
- **THEN** 已对齐的块被复用，只采集缺口；预演窗口按块起点回放，不出现错位
