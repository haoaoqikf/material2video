# article-media-assets Specification

## Purpose
为统一文章及主题视频提供跨网站媒体导入、来源记录与离线制作契约，使助手全网检索得到的图片视频可以被校验、重复剪辑并追溯到实际本地文件。

## Requirements

### Requirement: 公开媒体导入

系统 MUST 提供 article assets import，接受媒体直链或已下载文件，不要求指定图库。MUST 临时下载、限制大小和超时、探测真实类型尺寸及时长后采用；未知署名和许可 MUST 明确记录为未知，来源页面及实际媒体地址 MUST 保留。采用后的素材 MUST 在落盘后交回所在目录的继承权限，与成片一样可以直接打开。

#### Scenario: 导入图片和视频
- **WHEN** 输入媒体直链或本地文件
- **THEN** 媒体被导入作品目录并记录实测信息及摘要；网页、失效链接或错误媒体明确失败

#### Scenario: 导入素材可直接打开
- **WHEN** 素材从导入临时目录搬到作品素材目录
- **THEN** 素材继承所在目录权限，无需人工修复即可打开

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

### Requirement: 电影级资产质量与许可审计

系统 MUST 提供资产质量审计，按镜头计算屏幕像素与纹理像素的比例，并检查 hero 资产的最低分辨率、normal/roughness/emissive 等辅助贴图、土星环等径向纹理的实际径向分辨率、色彩空间、alpha 与登记许可。审计结果 MUST 写入作品 `outputs/` 下的单独报告并绑定准备指纹；技术审计 MUST NOT 修改或重新编码原始素材。

cinematic 作品的 hero 资产 MUST 满足：颜色贴图 ≥ 4K（或屏幕像素/纹素比达到项目阈值）、岩质天体具备 normal map、气态行星具备可选的 flow/normal、土星环径向纹理 ≥ 4K×512、素材色彩空间与材质设置一致。hero 资产许可未知或为「未知」时 MUST 阻断；standard 资产许可未知时 MAY 保留现有「未知」记录并继续，但 MUST NOT 在片尾虚构署名。

系统 MUST 提供 `m2v assets audit --project <目录>`；命令 MUST 只读素材与导入记录，输出可定位到素材 ID 与镜头的报告，失败退出码与现有校验一致。素材、镜头或 look 变化 MUST 使审计报告过期。

#### Scenario: Hero 贴图不足
- **WHEN** cinematic 作品的地球 hero 使用 2K 颜色贴图且屏幕占比超过阈值
- **THEN** 审计报告标为不合格并阻断 cinematic 导出，指出素材 ID 与镜头

#### Scenario: 许可未知
- **WHEN** hero 纹理的许可记录为“未知”
- **THEN** cinematic 导出被阻断，要求补充来源与许可；standard 作品保留记录但不虚构署名

#### Scenario: 辅助贴图缺失
- **WHEN** 岩质 hero 天体只有颜色贴图，没有 normal map
- **THEN** 审计报告标为缺口并给出建议，不静默把颜色图当凹凸使用

#### Scenario: 标准档不增加门禁
- **WHEN** standard 作品未运行资产审计
- **THEN** 现有准备、预演与导出行为不变
