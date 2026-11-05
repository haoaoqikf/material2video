# article-media-assets Specification

## Purpose
为统一文章及主题视频提供跨网站媒体导入、来源记录与离线制作契约，使助手全网检索得到的图片视频可以被校验、重复剪辑并追溯到实际本地文件。

## Requirements

### Requirement: 公开媒体导入

系统 MUST 提供 `m2v general assets import`，接受媒体直链或已下载文件，不要求指定图库。MUST 临时下载、限制大小和超时、探测真实类型尺寸及时长后采用；未知署名和许可 MUST 明确记录为未知，来源页面及实际媒体地址 MUST 保留。清单和记录 MUST 支持 sourceType、publisher、description、usableSegment 与 usage；usage MUST 区分 explicit-allowed、no-explicit-restriction、conditional、prohibited、not-checked，保留依据页、检查日期与说明，conditional MUST 声明条件是否满足。无 usage 时 MUST 显示未核实提示，不推断已授权。可用片段 MUST 在实际视频时长内，且仅作制作参考、当前不渲染。采用后的素材 MUST 在落盘后交回所在目录的继承权限，与成片一样可以直接打开。

#### Scenario: 导入图片和视频
- **WHEN** 输入媒体直链或本地文件
- **THEN** 媒体被导入作品目录并记录实测信息及摘要；网页、失效链接或错误媒体明确失败

#### Scenario: 导入素材可直接打开
- **WHEN** 素材从导入临时目录搬到作品素材目录
- **THEN** 素材继承所在目录权限，无需人工修复即可打开

#### Scenario: 官网素材采用依据
- **WHEN** 导入未知许可但已检查未发现明确禁止的公司官网素材
- **THEN** 保留原始未知许可、官方发布主体、检查依据和日期，不将采用政策写成已授权

#### Scenario: 元数据非法
- **WHEN** 声明无效使用状态、缺少已检查状态的依据日期或越界可用片段
- **THEN** 导入失败且不发布该批文件或记录

### Requirement: 素材一致性

系统 MUST 在 prepare 校验登记素材摘要、真实类型、实测尺寸及时长；代码场景素材 MUST 不强制匹配横竖屏画幅，也不要求逐幕 aspectRatio 豁免。制作 MUST 只使用本地已导入素材，媒体及登记映射变化 MUST 使旧准备失效。

#### Scenario: 文件被替换
- **WHEN** 导入素材被外部修改
- **THEN** 准备拒绝，要求重新导入

#### Scenario: 不同比例
- **WHEN** 横屏或竖屏代码场景使用有效的不同比例素材
- **THEN** 校验通过，由作品代码决定 fit 和裁切

### Requirement: 文章统一素材入口

素材作品 MUST 使用 v8 general 代码场景；系统 MUST 拒绝 stock-montage 和旧分镜，不提供迁移工具。Pixabay MUST 作为唯一启用且默认的图库来源；Pexels MUST 固定停用，显式指定时 MUST 提示已停用并引导使用 Pixabay，配置 Pexels 密钥 MUST NOT 自动重新启用，没有候选不算制作失败；其他公开媒体直链 MUST 可经相同导入留证入口采用。

#### Scenario: 旧类型请求
- **WHEN** 请求 stock-montage 或 v7 素材作品
- **THEN** 拒绝并要求 v8 general 重新制作

#### Scenario: 图库作为可选来源
- **WHEN** 图库没有候选但存在可用公开直链
- **THEN** 允许统一导入留证后供代码场景使用

#### Scenario: 默认与显式图库选择
- **WHEN** 未指定图库或显式指定 pixabay
- **THEN** 使用 Pixabay，缺少凭据时提示 M2V_PIXABAY_API_KEY，不回退其他图库

#### Scenario: Pexels 固定停用
- **WHEN** 显式指定 pexels，无论是否设置其密钥
- **THEN** 不发出图库请求，提示已停用并引导使用 Pixabay

#### Scenario: 图库方向为偏好
- **WHEN** 图库返回不同横竖方向的有效候选
- **THEN** 保留全部方向，按作品方向稳定优先排序，不按方向过滤；候选输出媒体地址、来源类型、发布主体及默认未核实状态，不自动下载或声称已获授权

### Requirement: 电影级资产质量与许可审计

系统 MUST 对全部登记媒体检查文件、原生尺寸、色彩空间、alpha与许可，许可未知或未核实 MUST 提示而不单独阻断；明确禁止当前用途或条件未满足 MUST 阻断准备与审计；非法采用元数据 MUST 明确失败。报告 MUST 绑定准备指纹并明确清晰度仅记录原生尺寸、实际屏幕用途尚需人工复核，不声称自动计算屏幕纹素比。二维、程序化和三维 MUST 按实际用途检查，不强制固定4K或normal/roughness/emissive齐全度。审计 MUST 不改动原素材，入口为 m2v assets audit；素材、镜头或look变化使旧报告失效。`m2v assets report` 与 `m2v assets contact-sheet` MAY 作为制作期台账与候选检查入口，但 MUST NOT 替代审计或 prepare 的许可、摘要与一致性阻断，也不得写入审计报告或准备指纹。

#### Scenario: Hero 贴图不足
- **WHEN** 重点镜头使用低于4K的已登记素材
- **THEN** 记录原生尺寸和实际用途复核提示，不仅凭尺寸阻断；若画面实查模糊则返工

#### Scenario: 许可未知
- **WHEN** 任意登记素材许可未知，包括非重点镜头素材
- **THEN** 准备与审计给出许可未知和适用的未核实提示，不据此单独失败；明确禁止或条件未满足时仍失败

#### Scenario: 辅助贴图缺失
- **WHEN** 二维、程序化或三维素材没有辅助贴图
- **THEN** 不因贴图配额拒绝，按实际表现需要决定是否补充

#### Scenario: 标准档不增加门禁
- **WHEN** general 未显式运行素材审计命令
- **THEN** prepare 仍检查全部登记媒体的采用状态和技术一致性；人工审美记录不增加CLI门禁

#### Scenario: 台账工具不替代审计
- **WHEN** 只运行了 `m2v assets report` 或 `m2v assets contact-sheet`
- **THEN** 不产生 `outputs/asset-audit.json`，不改变准备指纹，也不能据此声称许可审计或 prepare 已通过

#### Scenario: 明确限制覆盖全部素材
- **WHEN** 任意登记素材声明 prohibited 或 conditional 且条件未满足
- **THEN** 准备与审计失败并指出素材 ID，未引用素材也不豁免

### Requirement: 按表达目的选择载体并优先外部视频

制作助手 MUST 按场景的证据、识别、机制、关系或情绪任务选择外部素材、代码或混合载体。选择外部素材时 MUST 优先检索合适的视频，无合适视频再使用图片；静态原件本身为表达对象时 MAY 直接使用图片。适合界面交互、数据变化或机制解释的场景 MAY 直接代码合成，无需先检索外部视频。合适的外部素材 MUST 支持具体表达，并满足来源许可、画质、时长与实际构图要求，不得为视频优先采用无关动态或冒充真实事件。

选择依据 MUST 简记于现有 DESIGN.md「表达载体」与「载体来源与理由」；视频检索后回退图片 MUST 简记原因，不得虚构检索。既有制作评审 MUST 检查载体是否支撑表达、图片替代是否合理、代码是否呈现必要过程，不设视频占比、检索次数或新增 CLI 门禁。

#### Scenario: 优先采用合适的视频
- **WHEN** 场景需要外部素材且能取得内容相关、关键动作可见、质量与许可满足的视频
- **THEN** 优先使用该视频，而非以方便获取的图片替代

#### Scenario: 无合适视频时使用图片
- **WHEN** 已检索视频但内容、动作、画质、时长、构图或许可不满足表达需要
- **THEN** 可使用合适图片，在现有载体记录中简记回退原因；图片运动不得被当作真实动作证据

#### Scenario: 静态原件直接入选
- **WHEN** 场景表达对象是照片、文献、海报等静态原件
- **THEN** 可直接使用对应图片，无需为满足视频优先而先检索视频

#### Scenario: 搜索交互用代码合成
- **WHEN** 场景通过谷歌搜索行为表达对象识别或操作过程
- **THEN** 可直接代码呈现搜索框、输入、点击与结果反馈；涉及具体真实结果或历史界面时必须有相应真实材料依据，示意不得冒充证据

#### Scenario: 真实锚点配合机制解释
- **WHEN** 场景同时需要真实感与不可见机制的解释
- **THEN** 可组合真实素材与代码动画，明确真实与示意的边界，沿用现有导入留证和评审契约
