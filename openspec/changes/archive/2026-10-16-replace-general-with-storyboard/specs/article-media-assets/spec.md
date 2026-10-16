
## MODIFIED Requirements

### Requirement: 文章统一素材入口

系统 MUST 删除 stock-montage 独立类型及其旧制作入口；素材作品 MUST 使用 v6 general，不提供旧作品兼容与迁移工具。系统 MUST 将 Pexels、Pixabay 作为文章可选图库来源，且图库检索 MUST 只是候选来源之一：没有候选不算失败，助手也可以改用其他公开媒体直链。

#### Scenario: 旧类型请求
- **WHEN** 请求新建或制作 stock-montage
- **THEN** 系统拒绝未知类型，不进入旧制作链

#### Scenario: 图库作为可选来源
- **WHEN** 文章分镜的媒体幕需要素材
- **THEN** 系统可按 provider 名称用 Pexels 或 Pixabay 检索候选，也可以直接导入其他公开媒体直链；两条路径都经同一导入留证边界进入作品
