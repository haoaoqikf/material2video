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

### Requirement: 统一制作契约

系统 MUST 对 general 使用唯一制作契约并拒绝 `productionProfile` 与 `--profile`，不保留双档位分支；`project.json` 中的旧字段（包括显式 `null`）与 CLI 旧参数 MUST 在准备前明确失败。所有作品 MUST 按内容决定镜头数量与时长、二维或三维、声音与后期，不设固定 hero 配额或 4K 静帧要求，但 MUST 保留镜头时间窗越界、重叠与 tier 合法性校验。

look-dev MUST 按片长与风险选择代表静帧张数、尺寸、样片长度与采样尺度，MUST NOT 引入人工确认门禁。准备记录、预演与视觉溯源 MUST 记录实际 shots、look、后期参数、声音配置与交付参数；任一参数变化 MUST 使旧准备与完整候选过期。未声明 shots/look 时 MUST 保持默认采集参数与画面行为，并因统一契约使旧片段缓存失效一次。

#### Scenario: 旧档位声明
- **WHEN** `project.json` 含 `productionProfile`（含 `null`）或 `prepare` 传入 `--profile`
- **THEN** 准备前明确拒绝，要求删除旧字段并重新 prepare

#### Scenario: 无固定镜头配额
- **WHEN** 作品按内容使用少于 3 个 hero，或 hero 短于 8 秒
- **THEN** 校验只检查时间窗、重叠与 tier 合法性，不因固定数量或时长拒绝

#### Scenario: 电影级参数变化
- **WHEN** 只改动 look、shot、后期或声音参数后重新准备
- **THEN** 旧准备与完整候选失效，要求重新准备并重新验收；代码片段缓存键同步变化

#### Scenario: 可选质量参数
- **WHEN** 作品未声明 shots/look 或 look.motion
- **THEN** 使用 1 倍、1 子帧采集且不自动添加后期；声明后按 1–2 倍与 1–4 子帧校验并进入缓存键
