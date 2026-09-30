## MODIFIED Requirements

### Requirement: 视觉策略必须包含情绪与母题

作品级导演简报 SHALL 包含情绪曲线与风格包；视频级视觉策略
（`visualDirection`）SHALL 包含视觉母题、构图倾向、密度、节奏与规避项，
并要求逐幕意图引用或推进其中至少一项。

#### Scenario: 全片视觉母题缺失
- **WHEN** 多幕作品没有任何可追踪的视觉母题引用
- **THEN** 严格检查报告母题缺失，不把颜色一致视为母题成立

#### Scenario: 情绪曲线与风格包缺失
- **WHEN** 分镜的 `directingBrief` 缺少 `emotionalArc` 或 `stylePack`
- **THEN** 校验失败并指出字段路径，预览与渲染均不开始
