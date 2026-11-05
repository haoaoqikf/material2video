# material-sourcing Specification

## Purpose
为 general 作品的外部素材提供可执行的检索、候选评估、许可判断与台账整理流程，并用只读命令把登记记录、场景引用与来源表放在一起核对；采用检查后未发现明确禁止即可使用的默认制作政策，保留离线渲染、技术一致性与既有审核职责。

## Requirements

### Requirement: 素材工作流参考页

`material2video` skill MUST 提供 `references/material-sourcing.md`，承载外部素材的操作流程：来源层级与检索词、候选评估、实际片段检查、许可与署名决策、台账修复、替换复核与停止条件。该页 MUST 从 `SKILL.md` 的条件参考与 `guidance-routes.json` 可达，MUST NOT 新增制作阶段、审核轮次、分镜字段或 CLI 门禁；载体选择与导入留证的权威口径仍由 `visual-material-selection.md` 和 `article-media-and-sound.md` 承担。

#### Scenario: 检索外部素材时按页执行

- **WHEN** 为 general 作品检索外部图片或视频
- **THEN** 能从主 Skill 与阅读路由找到该页，并按页内的来源层级、候选评估卡与许可决策执行，不需要新增阶段或门禁

#### Scenario: 与既有权威不冲突

- **WHEN** 检查新增参考页与既有素材参考页的分工
- **THEN** 载体选择仍指向 `visual-material-selection.md`，导入与来源字段仍指向 `article-media-and-sound.md`；新页只补操作步骤，不复述门禁、不另立许可标准

#### Scenario: 公司与产品优先检索官方来源
- **WHEN** 作品讲述具体公司、产品或生产过程
- **THEN** 先检查相关官网新闻中心、媒体素材、产品演示、投资者关系或官方账号，再按缺口扩展到行业、新闻、档案、开放库与图库；记录实际检索、未找到的缺口和回退理由，不强制固定次数或搜遍所有栏目

### Requirement: 素材台账报告

系统 MUST 提供 `m2v assets report --project <目录>`，只读核对：登记素材的文件存在性、路径位于 `assets/media/`、摘要与记录一致、许可/作者/来源是否为未知；场景源码中按字面量调用的素材 ID 是否已登记；登记素材是否被场景引用（直接 `useMediaAsset("id")`，或以引号字面量出现在包装组件 props 等场景源码中）；作品存在 `SOURCES.md` 时登记 ID 是否出现在来源表。MUST 输出人类可读摘要与 `outputs/assets-report.json`，并在存在错误时以非零退出码结束。错误 MUST 至少覆盖：引用未登记素材、文件缺失、摘要不符、路径越界、明确禁止当前用途、条件未满足或采用元数据无效。报告 MUST NOT 修改素材、来源记录或准备记录，MUST NOT 替代 `prepare` 与 `assets audit`。

#### Scenario: 场景引用未登记素材

- **WHEN** 场景调用 `useMediaAsset("x")` 但记录中没有 `x`
- **THEN** 报告把它列为错误、指出 ID 并返回非零退出码

#### Scenario: 登记素材许可未知

- **WHEN** 记录中任一素材的许可为未知
- **THEN** 报告把它列为警告并保留实际采用状态，不将其冒写为已获授权

#### Scenario: 台账完整

- **WHEN** 全部登记素材都被场景引用、文件与摘要一致、许可与来源齐全，且 ID 出现在 `SOURCES.md`
- **THEN** 报告通过，并在输出中声明它不是交付门禁、不替代 prepare 与 assets audit

#### Scenario: 动态引用

- **WHEN** 场景以变量调用 `useMediaAsset(id)` 而非字面量
- **THEN** 报告标记存在动态引用并给出警告，不据此宣称未引用的登记素材一定多余

#### Scenario: 明确禁止或条件未满足
- **WHEN** 任意登记素材的采用状态为 prohibited 或 conditional 且条件未满足
- **THEN** 报告指出素材并以错误结束，与 prepare 和 audit 使用相同判据

### Requirement: 候选接触表

系统 MUST 提供 `m2v assets contact-sheet`，接受 1～24 个本地候选文件：图片按顺序拼格；视频按显式时刻或均匀采样抽帧拼格。每格 MUST 带序号，并 MUST 写同名 JSON 索引记录格位与时刻或文件的对应关系。一次 MUST 最多接受一个视频输入，其余输入 MUST 为图片；MUST 只读输入文件，不导入、不改写候选。

#### Scenario: 视频候选完整过程检查

- **WHEN** 对一段候选视频给出建立、动作、结果附近的时刻并生成接触表
- **THEN** 输出带序号的接触表与同名 JSON 索引，格位可按索引对回时刻

#### Scenario: 多张图片候选

- **WHEN** 传入多张候选图片
- **THEN** 按传入顺序拼成一张表，JSON 索引记录每格对应文件

#### Scenario: 非法输入

- **WHEN** 传入两个视频、空输入、越界采样数或不可解码文件
- **THEN** 明确失败并说明原因，不生成半成品接触表

### Requirement: 制作期工具不进入离线渲染

`report` 与 `contact-sheet` MUST 只在制作期由助手显式运行，MUST NOT 被 `prepare`/`render` 调用，MUST NOT 联网，MUST NOT 改变准备指纹或渲染输入。

#### Scenario: 渲染保持离线

- **WHEN** 执行 `prepare` 或 `render`
- **THEN** 不调用这两条命令，也不把 `outputs/assets-report.json` 或接触表当作画面输入
