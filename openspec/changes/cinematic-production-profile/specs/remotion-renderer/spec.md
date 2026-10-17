## RENAMED Requirements

- FROM: `### Requirement: 成片编码与交付参数不变`
- TO: `### Requirement: 分档成片编码与交付参数`

## MODIFIED Requirements

### Requirement: 分档成片编码与交付参数
standard 档的成片编码参数 SHALL 与既有契约一致：画面 `yuv420p`（`tv` 范围、`bt709`）、宽高为偶数、帧率与尺寸取自分镜；有声导出 SHALL 使用 AAC-LC、44.1kHz、立体声、128k。standard MUST NOT 因本变更改变码流、帧数或播放器兼容性。

cinematic 档 SHALL 在 standard 兼容交付之外新增母版：ProRes 422 HQ 或 DNxHR HQX、10bit；交付 SHALL 提供 H.264 CRF 14–16（或 12–20 Mbps）兼容版，MAY 另提供 HEVC 10bit 版；音频母版 SHALL 使用 48kHz/24bit，交付 AAC 320kbps。母版与交付版 MUST 记录实际编码参数、帧数、时长、分辨率、帧率、响度与真峰值。渲染成功后系统 SHALL 完整解码一遍母版与交付版并核对帧数与分辨率，SHALL 读回码流参数并拒绝全范围像素格式的交付文件。交付文件落盘后 SHALL 交回目标目录的继承权限。

#### Scenario: 标准档码流不变
- **WHEN** 以 standard 渲染有声作品
- **THEN** 成片仍为 yuv420p(tv, bt709)、H.264、44.1kHz 立体声 AAC，帧数与分辨率与分镜一致

#### Scenario: 电影级母版与交付
- **WHEN** 以 cinematic 渲染成功
- **THEN** 同时产出 10bit 母版与 H.264 兼容交付，音频母版为 48kHz/24bit，交付为 320kbps；两者帧数与分辨率一致

#### Scenario: 全范围像素格式
- **WHEN** 产出的交付码流为全范围像素格式
- **THEN** 验收报错终止，SHALL NOT 交付「能解码但播放器打不开」的成片

#### Scenario: 帧数与分辨率
- **WHEN** 渲染成功
- **THEN** 解码复核得到的帧数与分辨率与分镜一致；母版与交付版均通过

#### Scenario: 响度与真峰值
- **WHEN** cinematic 母版导出
- **THEN** 量测报告显示母版约 −14 LUFS 且真峰值不超过 −1 dBTP；超出时降低增益重新合成，不改变时间轴

## ADDED Requirements

### Requirement: 电影级后期与运动模糊的确定性

cinematic 档的后期、运动模糊与 SSAA SHALL 由代码场景或共享 composition 在帧驱动下完成；系统 MUST NOT 依赖挂钟、随机数或未受控的异步状态。hero 镜头 MAY 使用 2× SSAA 与 2–4 子帧平均模拟 180° 快门；standard MUST 默认关闭这些选项。

系统 SHALL 在渲染前校验 profile 与依赖；缺少后期依赖、profile 非法或后期参数越界时 MUST 失败，不输出部分后期画面。渲染报告 SHALL 记录 profile、每个镜头的质量档、子帧数、SSAA 倍数与实际耗时。同帧重复渲染 SHALL 继续满足 PSNR ≥ 60dB 的画面等价判据。

#### Scenario: 后期确定性
- **WHEN** 同一 cinematic 帧连续渲染两次
- **THEN** 两次画面等价，PSNR ≥ 60dB；后期不因真实时间或随机源产生漂移

#### Scenario: 缺少后期依赖
- **WHEN** cinematic profile 启用但 postprocessing 依赖缺失或版本不符
- **THEN** 渲染前明确失败并指出依赖，不静默跳过后期

#### Scenario: 标准档无后期开销
- **WHEN** 以 standard 渲染
- **THEN** 不启用 SSAA、运动模糊或额外后期，渲染耗时与现有链路同量级
