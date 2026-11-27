## MODIFIED Requirements

### Requirement: 素材工作流参考页

`material2video` skill MUST 提供 `references/material-sourcing.md`，承载外部素材的操作流程：来源层级与检索词、候选评估、实际片段检查、许可与署名决策、台账修复、替换复核与停止条件。该页 MUST 从 `SKILL.md` 的条件参考与 `guidance-routes.json` 可达，MUST NOT 新增制作阶段、审核轮次、分镜字段或 CLI 门禁；载体选择与导入留证的权威口径仍由 `visual-material-selection.md` 和 `article-media-and-sound.md` 承担。

#### Scenario: 检索外部素材时按页执行

- **WHEN** 为三类作品检索外部图片或视频
- **THEN** 能从主 Skill 与阅读路由找到该页，并按页内的来源层级、候选评估卡与许可决策执行，不需要新增阶段或门禁

#### Scenario: 与既有权威不冲突

- **WHEN** 检查新增参考页与既有素材参考页的分工
- **THEN** 载体选择仍指向 `visual-material-selection.md`，导入与来源字段仍指向 `article-media-and-sound.md`；新页只补操作步骤，不复述门禁、不另立许可标准

#### Scenario: 公司与产品优先检索官方来源
- **WHEN** 作品讲述具体公司、产品或生产过程
- **THEN** 先检查相关官网新闻中心、媒体素材、产品演示、投资者关系或官方账号，再按缺口扩展到行业、新闻、档案、开放库与图库；记录实际检索、未找到的缺口和回退理由，不强制固定次数或搜遍所有栏目
