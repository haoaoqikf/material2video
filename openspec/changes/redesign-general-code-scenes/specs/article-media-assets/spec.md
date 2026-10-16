## MODIFIED Requirements

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

#### Scenario: 图库作为可选来源
- **WHEN** 图库没有候选但存在可用公开直链
- **THEN** 允许统一导入留证后供代码场景使用

#### Scenario: 旧类型请求
- **WHEN** 请求 stock-montage 或 v7 素材作品
- **THEN** 拒绝并要求 v8 general 重新制作
