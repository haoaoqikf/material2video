## MODIFIED Requirements

### Requirement: 所有分镜执行入口仅接受完整 v3 契约
系统 SHALL 只接受 version: 4、schemaVersion: 4、directingVersion: 2 的完整分镜，包含导演简报、视觉策略、Keynote 预设、全片 world 和非空 stages。标题保留历史规格名称，当前执行版本为 v4。所有未知或缺失版本 SHALL 失败；v1–v3 SHALL 提示按 v4 重新编排，无迁移命令、兼容开关或运行时回退。

#### Scenario: 旧版输入
- **WHEN** 任何执行入口读取 v1–v3
- **THEN** 返回明确重编排诊断，不执行预览、准备、评审或渲染

#### Scenario: 缺少世界声明
- **WHEN** v4 缺少 world 或 stages
- **THEN** 普通及严格校验均按字段失败

#### Scenario: 输入 v1 或 v2 分镜
- **WHEN** 任一分镜执行入口读取 v1/v2/v3 或缺失版本的分镜
- **THEN** 入口给出不支持 v4 之前分镜的明确错误，并且不预览、不评审、不准备媒体、不渲染

#### Scenario: 缺少导演策略
- **WHEN** v4 分镜缺少 directingBrief、visualDirection 或 keynote preset
- **THEN** 严格 schema 校验按字段定位拒绝该输入

### Requirement: 每幕明确声明画面、意图和镜头
v4 SHALL 在 world 声明唯一 renderer、全片对象与非空 camera.segments；每个 stage SHALL 提供唯一 id、正整数 durationInFrames 与完整 visualIntent。stage SHALL NOT 提供 renderer、sceneTree、camera 或 transition；系统 SHALL NOT 补默认画面。

#### Scenario: 阶段重声明画面
- **WHEN** stage 包含 renderer 或 transition
- **THEN** 校验拒绝并提示全片声明位置

#### Scenario: 缺少镜头
- **WHEN** world.camera.segments 为空
- **THEN** 校验失败，不使用默认镜头

#### Scenario: 缺 renderer 或镜头段
- **WHEN** v4 的 world 未声明 renderer 或 camera.segments
- **THEN** 校验失败并指出缺失字段，不采用默认 renderer 或默认镜头计划

#### Scenario: 缺少跨幕关系
- **WHEN** 有效 v4 分镜未声明旧 transition 但具备 world 与 stages
- **THEN** 不要求跨幕关系；阶段状态与镜头沿用全局时间轴

### Requirement: 口播与画面共用语义 beat 时间轴
有口播阶段 SHALL 使用 narrationSegments 和 beats，不接受字符串 narration。全局动作、状态与镜头 SHALL 使用 beatId 或 stageId 加 phase 绑定，禁止手写 startFrame。每个阶段 SHALL 保留至少 12 帧稳定阅读区，多目标动作继续使用 targets 与 stagger。

#### Scenario: 共同边界
- **WHEN** 媒体解析阶段口播
- **THEN** 字幕、动作、状态和镜头共用解析区间，阶段末保留稳定阅读时间

#### Scenario: 旧式动作
- **WHEN** 轨道使用 startFrame 或无有效绑定
- **THEN** 校验按字段拒绝

#### Scenario: 使用旧式口播或绝对帧动效
- **WHEN** 场景包含 narration 字符串、未绑定的 motion 或 startFrame
- **THEN** schema 拒绝场景，并指出应使用 narrationSegments、beats、phase/beatId 及分组错峰字段

#### Scenario: 镜头、动作和字幕使用共同时间轴
- **WHEN** 有口播的 beat 解析为确定帧区间
- **THEN** 镜头、动作和字幕的变化边界均引用该区间，并在末尾保留稳定阅读时间

## ADDED Requirements

### Requirement: 标准口播与声明时长校验
所有v4标准作品 SHALL 将各阶段 narrationSegments 按序拼接，按统一正文口径计数130～170字，并要求声明总帧数/fps为35～45秒（含边界）。校验 SHALL 分别报告字数、总时长及允许区间；纯静音阶段可存在，但不能豁免全片口播和时长标准。

#### Scenario: 字数独立失败
- **WHEN** 总时长40秒但口播171字
- **THEN** 校验失败并报告口播字数

#### Scenario: 时长边界
- **WHEN** 声明时长为35、45、低于35或超过45秒
- **THEN** 前两项通过，后两项失败，不将字数估计当作时长

#### Scenario: 无完整口播
- **WHEN** 全片没有任何口播
- **THEN** 标准作品校验失败，不以静音作品绕过150字标准
