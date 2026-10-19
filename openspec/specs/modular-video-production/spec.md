## Purpose

建立面向多种专用及通用视频的作品与制作契约，使用户通过统一入口准备、预演、评审和导出，并能够显式迁移已有作品且复核内容与渲染依据。

## Requirements

### Requirement: 统一作品及制作入口
系统 MUST 支持 project.json v1 和 m2v types/init/validate/prepare/preview/review-template/review/status/render/migrate/relocate；`m2v init` MUST 将作品初始化到 `videos/<type>/<slug>/`；作品相对材料以作品根解析，类型材料独立。退出码 MUST 区分成功0、执行或门禁失败1、材料或参数错误2。

#### Scenario: 材料归属与未知类型
- **WHEN** 在不同工作目录操作作品或传入未知类型/版本
- **THEN** 已知作品归属稳定，未知类型或版本在渲染前失败

#### Scenario: 按类型初始化作品
- **WHEN** 在工作区根对某个已登记类型执行 `m2v init --type general --project <slug>`
- **THEN** 作品和初始化材料创建在 `videos/general/<slug>/`

#### Scenario: 仓库自带示例走统一入口
- **WHEN** 用统一入口对仓库 `examples/<slug>/` 下的示例作品执行 prepare、preview 或 render
- **THEN** 媒体、预演与成片写入 `videos/examples/<slug>/outputs/`，
  不写进受版本控制的 `examples/<slug>/` 目录

### Requirement: 准备及评审版本绑定
系统 MUST 在准备后记录输入、资产、源码与准备指纹。render MUST 只读当前准备产物，缺少或过期时要求重新 prepare。正式导出 MUST 不依赖预演，生成一次并验证当前完整候选的准备指纹、文件摘要、完整帧数及媒体技术参数，并执行类型自动门禁；MUST NOT 要求人工画面评审。人工评审工具 SHALL 保留为可选工具，status MUST 标识 required=false，未填写时标识 optional；主动 review 时 MUST 验证当前结论、完整非空依据及候选摘要绑定。

具有专用评审要求的视频类型 MUST 可通过注册接口生成类型评审模板；统一 `review-template` MUST 同时创建通用评审记录和类型专用评审材料，主动执行统一 `review` MUST 验证两者；正式 `render` MUST 只验证自动门禁。

#### Scenario: 材料变化
- **WHEN** 准备或评审后修改数据、源码、字体、声音或候选
- **THEN** 对应记录失效，正式导出阻断

#### Scenario: 类型专用评审
- **WHEN** 金融或文章作品使用统一评审入口
- **THEN** 有人工评审工具的类型可按需生成模板，主动评审在依据缺失或过期时失败，正式导出不受人工记录影响；金融继续只做自动验收

#### Scenario: 自动预演门禁
- **WHEN** 当前准备有效且没有预演
- **THEN** 旧完整预演门禁不再生效，允许生成候选，验收后交付同一文件，不重复编码

### Requirement: 共用渲染及可靠输出
系统 MUST 使用完整缓存键且命中不跳门禁，元数据核验与渲染使用同一浏览器会话；候选生成后 MUST 持久化并绑定摘要，验收失败保留并禁止重试时重渲染；候选通过帧数、尺寸、帧率、音轨验收及输入复核后才替换目标。所有类型 MUST 输出溯源与性能记录。正式成片成功替换并生成旁车后，统一入口 MUST 清理当前作品 `outputs/` 中旧成片及其旁车、预演与已知检查和调试产物；MUST 保留本次成片、其字幕/溯源/性能旁车、准备和评审 JSON、可供重渲使用的准备媒体及当前候选与交付记录。清理不得越出当前作品 `outputs/`，不得清理共享构建缓存。general 当前 visual-notes、其引用的当前检查证据及返工前后对照 MUST 保留在作品忽略的输出目录中，作为已知检查产物清理的例外；历史无引用大体积检查产物仍按原规则清理。渲染或验收失败 MUST NOT 触发清理；清理遇到文件错误时 MUST 保留有效新成片、报告失败和遗留路径，且不得声称全部清理完成。

#### Scenario: 元数据不符或输出失败
- **WHEN** composition 元数据不符或渲染期间材料变化
- **THEN** 阻断或丢弃临时产物，不覆盖原有效成片

#### Scenario: 正式渲染成功后清理旧产物
- **WHEN** 任一视频类型的正式渲染通过验收并写好成片旁车
- **THEN** 只保留本次成片和必要旁车、准备及评审记录、准备媒体；清理当前作品输出目录内旧视频、预演与已知检查/调试产物

#### Scenario: 渲染失败不清理
- **WHEN** 正式渲染或成片验收失败
- **THEN** 不执行旧产物清理，已有有效成片及其他产物保持不变

#### Scenario: 清理遇到文件错误
- **WHEN** 新成片已验收，但一个或多个旧产物无法删除
- **THEN** 保留新成片并报告清理失败及未删除路径，不影响新成片交付状态

#### Scenario: 保留当前视觉复核证据
- **WHEN** general 渲染成功后清理旧产物
- **THEN** 当前复核记录及其引用的检查依据和前后对照仍可访问，内容与媒体不加入 Git

### Requirement: 逐作品路径迁移

系统 MUST 支持对已有统一契约作品逐个执行 `m2v relocate --project videos/<slug>`，按 `project.json` 中已登记的类型将其移入 `videos/<type>/<slug>/`。迁移 MUST 在移动前创建包含完整旧目录的备份，并保持源材料、项目描述和整个 `outputs/` 的相对路径。目标已有同路径文件时 MUST 保留目标、将冲突源文件留在旧目录并报告；其他文件继续移动。迁移 MUST 可重跑以继续处理冲突，且不得覆盖目标文件。仓库外内容根 SHALL 可通过 `--content-root` 或 `M2V_CONTENT_ROOT` 指定。

#### Scenario: 迁移统一契约作品路径
- **WHEN** 用户对 `videos/<slug>/` 下的作品执行路径迁移
- **THEN** 作品移动至 `videos/<project.type>/<slug>/`，完整备份旧目录，并保留其全部产物

#### Scenario: 目标文件冲突及重试
- **WHEN** 目标目录已有同路径文件，且用户处理后重试旧目录
- **THEN** 目标版本始终不被覆盖，未冲突文件完成迁移，冲突源文件得到报告并在旧目录保留直至可迁移

### Requirement: 显式迁移
系统 MUST 校验并完整备份旧作品后迁移，拒绝重复迁移覆盖、未知材料、文章v1-v3；材料格式迁移使用 `migrate --from`，与路径迁移 `relocate` 分开。保留历史成片，旧准备和评审不能授权新正式导出。旧制作脚本 MUST 下线。

#### Scenario: 迁移旧作品
- **WHEN** 用户迁移文章v4或当前金融作品
- **THEN** 备份原作品并创建类型描述，要求重新准备、预演及评审

### Requirement: 类型的单一登记来源
系统 MUST 在唯一一份类型目录中登记每个视频类型的身份与材料入口：名称、一句话说明、作品初始化所需材料（材料名、默认文件名）与初始化模板内容。统一入口的类型清单、说明文案与初始化材料 MUST 从该目录派生，禁止在作品契约或命令行入口中另行维护类型白名单、材料映射或初始化模板。

新增视频类型 MUST NOT 需要修改统一入口的命令分发或作品契约的白名单；行为实现与目录登记是该类型仅有的两处落点。

#### Scenario: 新增类型只登记一次
- **WHEN** 为一个新视频类型实现行为并只在类型目录登记其身份与材料入口
- **THEN** `m2v types` 列出该类型及其目录说明，`m2v init --type <新类型>` 按目录声明生成材料文件，且统一入口的类型分发与作品契约白名单无需改动

#### Scenario: 未登记的类型被拒绝
- **WHEN** 一个已注册的视频类型在类型目录中没有登记项
- **THEN** 使用该类型的操作在渲染前失败，报错指出类型目录缺少登记项并说明查询可用类型的方式；`m2v types` 仍能列出全部已注册类型，不因缺少登记项而中断

#### Scenario: 未知类型在渲染前失败
- **WHEN** 作品描述声明了未注册的类型
- **THEN** 系统在渲染前以「未知视频类型」失败并指向 `m2v types`，退出码为执行或门禁失败（1）

### Requirement: 初始化材料立即可用
`m2v init` 为已登记类型生成的材料文件 MUST 是该类型自身契约接受的形式，MUST NOT 出现材料内容被外层文件键或其它包装层级包裹的结构偏差。初始化得到的作品在补齐占位内容之前，校验结果 MUST NOT 包含由结构包裹引起的错误。

#### Scenario: 初始化产物的顶层结构
- **WHEN** 对任一已登记类型执行 `m2v init`
- **THEN** 每个生成的材料文件顶层结构与该类型契约一致，不出现被文件名键包裹的内容（文章类型的 `storyboard.json` 顶层即 v4 分镜字段）

#### Scenario: 初始化后校验不报结构错误
- **WHEN** 对 `m2v init` 得到的作品执行该类型的材料校验
- **THEN** 校验结果不包含结构包裹导致的错误（文章类型不再报出「不支持 v4 之前分镜」），只可能报出占位内容待填写的问题

### Requirement: 文档中的类型清单由类型目录生成
README、Skill 与项目规划中描述视频类型的清单 MUST 由类型目录生成，不得手工维护。仓库 MUST 提供一致性校验，使生成产物与磁盘内容不一致时校验失败，并指出需要重新生成的文档。

生成 MUST 是幂等的：类型目录未变化时重新生成不产生任何差异。

#### Scenario: 文档与类型目录漂移
- **WHEN** 类型目录新增类型或修改某个类型的文档文案，而对应文档未重新生成
- **THEN** 一致性校验失败，并指出需要重新生成的文档

#### Scenario: 幂等重新生成
- **WHEN** 类型目录与文档当前一致时重新运行生成
- **THEN** 文档内容逐字节不变

### Requirement: 三类型统一制作入口
系统 MUST 仅注册 financial-timeseries、housing-timeseries 和 general，通用类型中文名为“通用”，以 storyboard 材料制作 v8 讲解；辅助操作 MUST 使用 m2v general。旧 article-narrative 类型与 m2v article 命令 MUST 被拒绝，作品标准位置 MUST 为 videos/general/<slug>。

#### Scenario: 查询与初始化类型
- **WHEN** 用户查询类型或初始化通用作品
- **THEN** 类型列表仅返回三类，通用模板与目录采用 general 身份

#### Scenario: 旧入口被拒绝
- **WHEN** 用户指定 article-narrative 类型或执行 m2v article
- **THEN** 系统报告无效类型或命令，不提供兼容分发

### Requirement: 交付产物的访问权限

从临时目录搬到最终位置的产物 MUST 在落盘后交回所在目录的继承权限，使以标准权限运行的打包应用（媒体播放器、照片）无需人工修复即可打开；范围包括成片、溯源记录、混音音轨、录制片段、导入素材与缓存条目。搬运与权限修复 MUST 是同一个动作，系统 MUST NOT 存在只搬运不修复的交付路径。修复后 MUST 复核目标本身；仍缺少标准权限进程可用的授权时 MUST 报告目标与所在目录，指出「父目录本身是收紧的」这一根因。非 Windows 平台 MUST 无行为差异。

#### Scenario: 标准权限播放器打开成片
- **WHEN** 成片从渲染临时目录搬到作品目录
- **THEN** 文件继承所在目录权限并含面向普通用户的授权条目，双击即可播放

#### Scenario: 收紧的父目录
- **WHEN** 交付目标所在目录本身只授权给 SYSTEM、Administrators 与 OWNER RIGHTS
- **THEN** 日志报告目标与所在目录，而不是静默交付一个打不开的文件

#### Scenario: 录制片段与导入素材
- **WHEN** 代码录制片段或导入素材从临时目录落地
- **THEN** 与成片同等修复，无需人工处理即可打开

### Requirement: 电影级制作与质检入口

系统 MUST 在统一入口新增电影级制作与质检命令：`m2v lookdev --project <目录>`、`m2v qa --project <目录>`、`m2v assets audit --project <目录>`。cinematic 的正式导出沿用现有 `m2v render`，不新增母版命令。命令 MUST 沿用现有作品路径、内容根、退出码与产物归属规则；standard 的现有命令与行为 MUST NOT 改变。

- `lookdev` MUST 只渲染关键静帧与代表片段，MUST NOT 生成完整成片；输出位于作品 `outputs/lookdev/`，包含 3–5 张从当前源码原生采集的 4K 静帧、接触表与 20–30 秒有声样片。帧序列、量测与自动音频信号检查的结论写入作品 `outputs/visual-notes.md`，作为检查与返工依据，MUST NOT 成为导出门禁；MUST NOT 要求播放样片或连续收听声音。
- `qa` MUST 输出 `outputs/qa.json` 与接触表，覆盖冻结/重复帧、banding、aliasing、字幕对比度、响度/真峰值、音轨时长差与 claims 时间窗覆盖，并提供全片采样清单、交界/异常加密帧、黑帧/突变及交付音轨削波/静音候选，并明确区分技术判定、测量提示和需查看采样图像的项目与自动信号检查的覆盖限制；MUST NOT 将技术通过表述为视觉质量通过；技术失败 MUST 以退出码 1 结束，报告 MUST 可定位到镜头/时间戳。
- `assets audit` MUST 只读素材与导入记录，输出 `outputs/asset-audit.json`；hero 资产不合格时 MUST 以退出码 1 结束。
- 正式导出 MUST 沿用 `m2v render`，交付普通 H.264 MP4；系统 MUST NOT 提供 `m2v master` 或 ProRes/DNxHR 母版入口。成片旁车 MUST 记录 profile、交付摘要、音频参数与 QA 指纹。
- standard 与 cinematic 的所有制作阶段均取消用户确认：`m2v render` MUST NOT 因缺少帧序列/量测复核记录、确认文件或 look-dev 产物而阻断。standard MUST 同样无需人工确认。

所有新命令 MUST 遵守离线、素材留证、准备指纹与交付权限规则；缺少准备记录、profile 非法或依赖缺失时 MUST 在渲染前失败，不产出部分产物。

#### Scenario: look-dev 只出样片
- **WHEN** 对 cinematic 作品运行 `m2v lookdev`
- **THEN** 只生成关键静帧、接触表与 20–30 秒有声样片，不生成全片，不覆盖正式成片

#### Scenario: QA 失败定位
- **WHEN** 某镜头出现冻结帧或响度超限
- **THEN** `m2v qa` 以退出码 1 结束，报告指出镜头/时间戳与实测值

#### Scenario: look-dev 之后直接导出
- **WHEN** 跑完 `m2v lookdev` 且作品未记录任何确认或替代复核结论
- **THEN** `m2v render` 正常交付，不因缺少确认而阻断；`lookdev` 产物仍可供观看与返工定位

#### Scenario: 标准命令不变
- **WHEN** 使用现有 validate/prepare/preview/render 处理 standard 作品
- **THEN** 参数、默认输出、退出码与成片行为保持不变

#### Scenario: 原生 4K 关键帧
- **WHEN** 运行 lookdev 生成静帧，作品包含显式低 DPR 的 WebGL 画布或多个代码幕
- **THEN** 从当前源码连续推进至各幕选定帧，以 2 倍像素绘制画布，PNG 合成原有字幕与转场；不放大 1080p 缓存视频冒充原生细节，像素不足时明确失败；有声样片流程不变

#### Scenario: 测量项不能冒充通过
- **WHEN** QA 只计算了 banding 或 aliasing 相关数值
- **THEN** 报告标识为测量提示，不据此自动宣称画面无缺陷，也不将测量项当作技术失败

#### Scenario: 导出与完成分离
- **WHEN** render 成功但缺少当前有效的最终替代检查记录
- **THEN** CLI 仍可输出视频，助手报告尚未完成帧序列与自动音频复核，不要求用户确认，不宣称制作完成
