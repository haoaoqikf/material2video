## Purpose

以通用 general 身份制作原文或主题驱动的 v8 全画布代码讲解，统一本地 React 代码场景的实时录制片段、真实旁白、字幕、素材留证与完整预演自动验收，使作品可重复准备和正式导出。

## Requirements

### Requirement: 通用类型使用 v8 自由代码场景
系统 MUST 以 general 接受 v8 storyboard.json，支持 article/topic 输入且只接受本地 code 场景；MUST 保留真实配音、烧录字幕、媒体导入留证、音效音床、完整候选自动验收及 600 秒限制。准备阶段 MUST 只编译真实配音、时间轴及源码输入，检查和正式生成 MUST 按所需区间录制标准化无声片段，复用有效区间并补齐缺口；最终合成只回放片段。完整成片 MUST 只生成一次，验收后交付同一文件。初始化 MUST 显式生成 1920×1080、60 fps 材料及可运行本地场景。系统 MUST 拒绝旧分镜、general-plan、六种旧模板、visual.theme 和完整片段嵌入，不提供迁移工具。

#### Scenario: 初始化与制作通用作品
- **WHEN** 初始化 general 作品
- **THEN** 生成有效横屏 v8 分镜及本地代码入口，可进入统一制作链路

#### Scenario: 拒绝旧通用材料
- **WHEN** 提交 v7、旧模板、主题字段或完整作品嵌入
- **THEN** 制作前明确拒绝并要求按 v8 重新编排

### Requirement: 电影级通用作品档位

系统 MUST 在 `project.json` 接受可选的 `productionProfile`，取值为 `standard` 或 `cinematic`，缺省为 `standard`；非法取值 MUST 在准备前失败。standard MUST 保持当前 prepare、完整候选自动验收、默认编码与不加用户确认的行为。cinematic MUST 启用电影级制作契约：镜头清单、look、后期、声音设计、资产质量与普通 MP4 交付；look-dev MUST NOT 引入人工确认门禁。

cinematic 作品 MUST 在 `content.props` 声明 `shots` 与 `look`，MUST 提供至少 3 个 hero 镜头，MUST 在 look-dev 阶段产出 3–5 张 4K 静帧与 20–30 秒有声样片，MUST 实际观看 hero 镜头与样片并把时间码、问题与复查写入作品 `outputs/visual-notes.md`；该记录 MUST NOT 阻断铺全片或导出。不能观看时 MUST 如实说明，MUST NOT 声称已达到电影级。

cinematic MUST 把 profile、shots、look、后期参数、声音配置与交付参数写入准备记录、预演和溯源；任一参数变化 MUST 使旧准备与完整候选过期。standard 作品不因本要求改变准备记录、缓存键、时间轴或编码。

#### Scenario: 标准档不受影响
- **WHEN** 作品未声明 `productionProfile`
- **THEN** 按 standard 执行现有链路，准备记录、完整候选、编码与成片行为与当前一致

#### Scenario: 电影级作品缺少镜头
- **WHEN** `productionProfile` 为 cinematic 但未声明 shots、hero 少于 3 个或缺少 look-dev 记录
- **THEN** 准备或导出前明确失败，指出缺失项，不静默降级为 standard

#### Scenario: 电影级参数变化
- **WHEN** 只改动 look、shot、后期或声音参数后重新准备
- **THEN** 旧准备与完整候选失效，要求重新准备并重新验收；代码片段缓存键同步变化

#### Scenario: 非法档位
- **WHEN** `productionProfile` 为未知值或非字符串
- **THEN** 准备前失败并列出允许取值
