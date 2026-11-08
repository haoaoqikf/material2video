# five-video-types Specification

## Purpose

统一视频作品的公开身份、材料入口和制作流程，使不同画面来源都能从同一分镜链路生成视频，同时明确拒绝旧版本。

## Requirements

### Requirement: 五类视频身份

五类仅决定制作指导和默认目录；每个工程 MUST 独立拥有执行能力，不以主项目统一运行时作为运行前提。旧project v2和旧准备记录 MUST 明确拒绝，不提供转换入口。

系统 MUST 仅登记 `text-motion`、`data-evolution`、`principle-metaphor`、`spatial-3d`、`documentary-edit` 五类；`m2v types`、初始化与作品校验 MUST 使用同一清单，不提供类别或风格层。初始化默认路径 MUST 为 `videos/<type>/<slug>/`，有效独立工程移动后 MUST 允许从任意目录执行。

#### Scenario: 初始化五类作品
- **WHEN** 分别使用五个有效类型初始化作品
- **THEN** 每个作品位于对应类型目录，含有效的 v3 独立作品描述、v9 分镜和本地场景入口

#### Scenario: 旧身份被拒绝
- **WHEN** 初始化输入旧类型名、未登记类型或旧类别路径，或执行时输入旧契约工程
- **THEN** 在准备或渲染前明确失败，不选择兼容类型

### Requirement: 统一分镜与成片

五类仅决定制作指导和默认目录；每个工程 MUST 独立拥有执行能力，不以主项目统一运行时作为运行前提。旧project v2和旧准备记录 MUST 明确拒绝，不提供转换入口。

五类 MUST 使用 `project.json` v3、`storyboard.json` v9、相同的场景时间轴、准备、预演、渲染、声音及制作证据机制；每幕由本地代码场景绘制，完整成片由单一 composition 合成。旧作品描述、旧分镜和旧准备记录 MUST 明确拒绝，不自动迁移。

#### Scenario: 五类贯通
- **WHEN** 五类各有有效分镜和场景
- **THEN** 均可校验、准备、预演并按同一成片契约导出

#### Scenario: 旧材料
- **WHEN** 作品、分镜或准备记录使用旧版本或专用类型旧材料入口
- **THEN** 报出应重新编排的具体契约，不生成可导出的候选

### Requirement: 独立示例目录

五类仅决定制作指导和默认目录；每个工程 MUST 独立拥有执行能力，不以主项目统一运行时作为运行前提。旧project v2和旧准备记录 MUST 明确拒绝，不提供转换入口。

仓库 MUST 在 `examples/<type>/<slug>/` 保存七个可运行示例；示例素材恢复与输出仍遵守来源摘要校验及 Git 忽略规则。

#### Scenario: 示例运行
- **WHEN** 逐一对七个示例执行校验、准备和短预演
- **THEN** 不依赖风格包，所有作品材料和输出均留在自身目录
