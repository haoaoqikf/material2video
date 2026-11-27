## MODIFIED Requirements

### Requirement: 三类视频身份

系统 MUST 仅登记 `text-motion`、`data-evolution`、`spatial-3d` 三类。三类决定制作指导、默认目录和按 `type-default-style` 定义的默认风格。类型列表、初始化与作品校验 MUST 使用同一目录。类型与材料路由保持单层，MUST NOT 提供类别、风格子类型、风格目录层或风格包注册表。每个工程 MUST 独立拥有执行能力。默认路径 MUST 为 `videos/<type>/<slug>/`，有效独立工程移动后 MUST 能从任意目录执行。

#### Scenario: 初始化三类作品
- **WHEN** 分别使用三个有效类型初始化作品
- **THEN** 每个作品位于对应类型目录，拥有 v4 作品描述、v9 分镜、本地场景入口及本类型固化的风格规范。

#### Scenario: 旧身份被拒绝
- **WHEN** 初始化输入旧类型名、未登记类型或旧类别路径，或执行时输入旧契约工程
- **THEN** 在准备或渲染前明确失败，不选择兼容类型。

### Requirement: 统一分镜与成片

三类 MUST 使用 `project.json` v4、`storyboard.json` v9、相同的场景时间轴、准备、预演、渲染、声音及制作证据机制。每幕由本地代码场景绘制，完整成片由单一 composition 合成。每个工程 MUST 独立拥有执行能力。旧作品描述、旧分镜和旧准备记录 MUST 明确拒绝，不自动迁移。

#### Scenario: 三类贯通
- **WHEN** 三类各有有效分镜和场景
- **THEN** 均可校验、准备、预演并按同一成片契约导出。

#### Scenario: 旧材料
- **WHEN** 作品、分镜或准备记录使用旧版本或专用类型旧材料入口
- **THEN** 报出应重新编排的具体契约，不生成可导出的候选。

### Requirement: 独立示例目录

仓库 MUST 在 `examples/<type>/<slug>/` 保存现有三个可运行示例。每例 MUST 随工程提供生效风格规范、本地场景和执行入口。素材恢复与输出继续服从来源摘要校验及 Git 忽略规则。

#### Scenario: 示例运行
- **WHEN** 逐一对三个示例执行校验、准备和短预演
- **THEN** 本地风格可核验，作品材料和输出均留在自身目录，无风格包依赖。
