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

系统 MUST 对全部登记媒体检查文件、原生尺寸、色彩空间、alpha与许可，许可未知 MUST 阻断准备与审计。报告 MUST 绑定准备指纹并明确清晰度仅记录原生尺寸、实际屏幕用途尚需人工复核，不声称自动计算屏幕纹素比。二维、程序化和三维 MUST 按实际用途检查，不强制固定4K或normal/roughness/emissive齐全度。审计 MUST 不改动原素材，入口为 m2v assets audit；素材、镜头或look变化使旧报告失效。

#### Scenario: Hero 贴图不足
- **WHEN** 重点镜头使用低于4K的已登记素材
- **THEN** 记录原生尺寸和实际用途复核提示，不仅凭尺寸阻断；若画面实查模糊则返工

#### Scenario: 许可未知
- **WHEN** 任意登记素材许可未知，包括非重点镜头素材
- **THEN** 准备与审计失败并指出素材ID，不通过旧普通档绕过

#### Scenario: 辅助贴图缺失
- **WHEN** 二维、程序化或三维素材没有辅助贴图
- **THEN** 不因贴图配额拒绝，按实际表现需要决定是否补充

#### Scenario: 标准档不增加门禁
- **WHEN** general 未显式运行素材审计命令
- **THEN** prepare仍检查全部登记媒体许可，不能绕过；人工审美记录不增加CLI门禁
