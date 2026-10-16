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

素材作品 MUST 使用 v8 general 代码场景；系统 MUST 拒绝 stock-montage 和旧分镜，不提供迁移工具。Pexels、Pixabay MUST 作为可选图库来源，没有候选不算制作失败；其他公开媒体直链 MUST 可经相同导入留证入口采用。

#### Scenario: 旧类型请求
- **WHEN** 请求 stock-montage 或 v7 素材作品
- **THEN** 拒绝并要求 v8 general 重新制作

#### Scenario: 图库作为可选来源
- **WHEN** 图库没有候选但存在可用公开直链
- **THEN** 允许统一导入留证后供代码场景使用
