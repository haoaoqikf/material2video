## ADDED Requirements

### Requirement: 电影级通用作品档位

系统 MUST 在 `project.json` 接受可选的 `productionProfile`，取值为 `standard` 或 `cinematic`，缺省为 `standard`；非法取值 MUST 在准备前失败。standard MUST 保持当前 prepare、完整预演自动验收、默认编码与不加用户确认的行为。cinematic MUST 启用电影级制作契约：镜头清单、look、后期、声音设计、资产质量、普通 MP4 交付与用户确认。

cinematic 作品 MUST 在 `content.props` 声明 `shots` 与 `look`，MUST 提供至少 3 个 hero 镜头，MUST 在 look-dev 阶段产出 3–5 张 4K 静帧与 20–30 秒有声样片，MUST 在铺全片前取得用户确认，MUST 实际观看 hero 镜头与样片并把时间码、问题与复查写入作品 `outputs/visual-notes.md`。不能观看时 MUST 如实说明，MUST NOT 声称已达到电影级。

cinematic MUST 把 profile、shots、look、后期参数、声音配置与交付参数写入准备记录、预演和溯源；任一参数变化 MUST 使旧准备与完整预演过期。standard 作品不因本要求改变准备记录、缓存键、时间轴或编码。

#### Scenario: 标准档不受影响
- **WHEN** 作品未声明 `productionProfile`
- **THEN** 按 standard 执行现有链路，准备记录、完整预演、编码与成片行为与当前一致

#### Scenario: 电影级作品缺少镜头
- **WHEN** `productionProfile` 为 cinematic 但未声明 shots、hero 少于 3 个或缺少 look-dev 记录
- **THEN** 准备或导出前明确失败，指出缺失项，不静默降级为 standard

#### Scenario: 电影级参数变化
- **WHEN** 只改动 look、shot、后期或声音参数后重新准备
- **THEN** 旧准备与完整预演失效，要求重新准备并重新验收；代码片段缓存键同步变化

#### Scenario: 非法档位
- **WHEN** `productionProfile` 为未知值或非字符串
- **THEN** 准备前失败并列出允许取值
