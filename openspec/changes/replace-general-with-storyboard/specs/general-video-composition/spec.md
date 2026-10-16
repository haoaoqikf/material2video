## REMOVED Requirements

### Requirement: 通用场景及时间轴
**Reason**: 旧通用编排及作品代码场景已删除。
**Migration**: 不提供兼容或迁移工具；按 general v6 storyboard 重新编排。

### Requirement: 声音字幕及基础转场
**Reason**: 旧通用编排及作品代码场景已删除。
**Migration**: 不提供兼容或迁移工具；按 general v6 storyboard 重新编排。

### Requirement: 通用片受控音床
**Reason**: 旧通用编排及作品代码场景已删除。
**Migration**: 不提供兼容或迁移工具；按 general v6 storyboard 重新编排。

### Requirement: 通用成片音轨交付规格
**Reason**: 旧通用编排及作品代码场景已删除。
**Migration**: 不提供兼容或迁移工具；按 general v6 storyboard 重新编排。

### Requirement: 代码与嵌入类型门禁
**Reason**: 旧通用编排及作品代码场景已删除。
**Migration**: 不提供兼容或迁移工具；按 general v6 storyboard 重新编排。

## ADDED Requirements

### Requirement: 通用类型使用 v6 混合媒体讲解
系统 MUST 以 general 类型接受 v6 storyboard.json，支持文章或主题输入及观点、对比、步骤、因果图、图片、视频六种模板，保留真实配音、同步烧录字幕、媒体导入留证、音效音床、完整预演自动验收及最长 600 秒限制。系统 MUST 拒绝旧 general-plan 编排和代码场景，不提供旧类型兼容。

#### Scenario: 初始化与制作通用作品
- **WHEN** 用户初始化 general 并提供有效 v6 材料
- **THEN** 系统生成 storyboard.json 模板，并使用既有讲解准备、预演、渲染与验收链路

#### Scenario: 拒绝旧通用材料
- **WHEN** 作品声明旧 plan 材料或在分镜中声明代码场景
- **THEN** 系统在准备或渲染前明确拒绝，不加载作品代码或嵌入其他作品
