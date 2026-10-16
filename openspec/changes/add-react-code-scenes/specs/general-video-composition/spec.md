## RENAMED Requirements
- FROM: `通用类型使用 v6 混合媒体讲解`
- TO: `通用类型使用 v7 混合媒体讲解`

## MODIFIED Requirements

### Requirement: 通用类型使用 v7 混合媒体讲解
系统 MUST 以 general 类型接受 v7 storyboard.json，支持文章或主题输入及观点、对比、步骤、因果图、图片、视频六种受控模板与本地 React `code` 场景，保留真实配音、同步烧录字幕、媒体导入留证、音效音床、完整预演自动验收及最长 600 秒限制。代码场景 MUST 在准备阶段实时录制为标准化无声片段并绑定源码、资源、参数、时间窗、依赖与实现摘要；完整预演与正式导出 MUST 复用同一片段，MUST NOT 在导出执行作品代码。系统 MUST 拒绝旧 general-plan 编排与完整片段嵌入，不提供旧类型兼容。

#### Scenario: 初始化与制作通用作品
- **WHEN** 用户初始化 general 并提供有效 v7 材料
- **THEN** 系统生成 storyboard.json 模板，并使用既有讲解准备、预演、渲染与验收链路

#### Scenario: 拒绝旧通用材料
- **WHEN** 作品声明旧 plan 材料或引用完整片段嵌入
- **THEN** 系统在准备或渲染前明确拒绝，不加载其他作品
