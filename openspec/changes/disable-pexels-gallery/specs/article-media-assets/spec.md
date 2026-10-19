## MODIFIED Requirements

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
