## RENAMED Requirements

- FROM: `### Requirement: 七部现有示例全部独立`
- TO: `### Requirement: 五部随附示例全部独立`

## MODIFIED Requirements

### Requirement: 五部随附示例全部独立

系统 MUST 在 `examples/<type>/<slug>/` 保留 data-evolution/compound-interest、data-evolution/compound-connect、principle-metaphor/luck-on-stage、spatial-3d/solar-system-journey、documentary-edit/american-science-milestones 五部示例。每部 MUST 拥有独立工程与恢复说明，保持既有主题、场景身份、数学／事实口径、音轨要求及视听目标；MUST NOT 以空场景、静态占位、缩减内容或新增简化示例代替。每例 MUST 证明脱库构建与真实预演；全片导出链路 MUST 有各例完整技术验证，并对受影响代表画面与动态进行复核。图文动效 MUST 继续作为可初始化和制作的视频类型，但不要求附带示例。

#### Scenario: 独立示例矩阵

- **WHEN** 逐一复制五例到仓库外并恢复运行
- **THEN** 每例都能通过自己的入口预览与完整导出；三维异步、公式字体、真实媒体、事件音效、旁白和转场按实际采用范围验证，不借其他例通过代替。

#### Scenario: 示例集合与类型独立

- **WHEN** 枚举仓库分发示例并初始化图文动效作品
- **THEN** 示例目录和测试登记仅包含上述五部作品，图文动效初始化仍生成完整独立工程；文档不提供已删除作品的使用入口。
