## MODIFIED Requirements

### Requirement: 风格包统一作品级视觉语言

一个作品 SHALL 只启用一个主风格包；色彩、表面、线条、排版、动效曲线和转场配方 SHALL 从该风格包取值。风格包 SHALL 是导演简报的必填枚举，缺失或取未登记值时 SHALL 在校验阶段失败，SHALL NOT 回落到默认值继续渲染。

#### Scenario: 分镜声明风格包
- **WHEN** v3 分镜指定 `directingBrief.stylePack`
- **THEN** 预览和渲染按该风格包选择视觉令牌与动画语言

#### Scenario: 未声明风格包
- **WHEN** 分镜的 `directingBrief` 缺少 `stylePack`，或取值不在登记的枚举里
- **THEN** 校验失败并指出字段路径，不存在「用默认风格包继续渲染」的分支
