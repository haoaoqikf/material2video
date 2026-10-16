# article-media-assets Specification

## Purpose
为统一文章及主题视频提供跨网站媒体导入、来源记录与离线制作契约，使助手全网检索得到的图片视频可以被校验、重复剪辑并追溯到实际本地文件。

## Requirements

### Requirement: 公开媒体导入

系统 MUST 提供 article assets import，接受媒体直链或已下载文件，不要求指定图库。MUST 临时下载、限制大小和超时、探测真实类型尺寸及时长后采用；未知署名和许可 MUST 明确记录为未知，来源页面及实际媒体地址 MUST 保留。

#### Scenario: 导入图片和视频
- **WHEN** 输入媒体直链或本地文件
- **THEN** 媒体被导入作品目录并记录实测信息及摘要；网页、失效链接或错误媒体明确失败

### Requirement: 素材一致性

系统 MUST 在 prepare 校验已导入素材摘要和实测尺寸；默认新媒体幕按画布比例校验，允许逐幕显式放宽。渲染 MUST 仅使用本地素材；素材或分镜变化 MUST 使旧准备失效。

#### Scenario: 文件被替换
- **WHEN** 导入素材被外部修改
- **THEN** 准备被拒绝，要求重新导入

### Requirement: 文章统一素材入口

系统 MUST 删除 stock-montage 独立类型及其旧制作入口；素材作品 MUST 使用 v6 general，不提供旧作品兼容与迁移工具。系统 MUST 将 Pexels、Pixabay 作为文章可选图库来源，且图库检索 MUST 只是候选来源之一：没有候选不算失败，助手也可以改用其他公开媒体直链。

#### Scenario: 旧类型请求
- **WHEN** 请求新建或制作 stock-montage
- **THEN** 系统拒绝未知类型，不进入旧制作链

#### Scenario: 图库作为可选来源
- **WHEN** 文章分镜的媒体幕需要素材
- **THEN** 系统可按 provider 名称用 Pexels 或 Pixabay 检索候选，也可以直接导入其他公开媒体直链；两条路径都经同一导入留证边界进入作品
