# frontend-design Specification

## Purpose

把官方 `frontend-design` 作为项目级视觉设计知识来源：固定上游版本，保留原文，用视频适配层规定观察顺序、题材依据、反默认边界和不适用 Web 规则。它提供设计与复核词汇，不新增门禁、评分或审核轮次。

## Requirements

### Requirement: 视觉设计知识必须以项目级 skill 提供

项目 SHALL 在 `.agents/skills/frontend-design/` 提供官方视觉设计知识 skill，固定上游仓库 `anthropics/skills` 的 `skills/frontend-design/` 与提交，并在仓库内保存 Apache 2.0 许可证与 `UPSTREAM.md`。上游 `SKILL.md` 正文 SHALL 原样保留、不翻译；项目差异 SHALL 记录在 `UPSTREAM.md`。

`SKILL.md` frontmatter 的 `description` SHALL 指向画面设计、视觉方向、字体排版、构图与反模板判断的视频语境；文件顶部 SHALL 指向中文 `ADAPTATION.md`。`ADAPTATION.md` SHALL 写明视频语境映射、观察—对照—批评的执行方式，以及不适用的 Web/UI 规则。

#### Scenario: 上游内容可追溯
- **WHEN** 维护者检查视觉设计 skill
- **THEN** 能从 `UPSTREAM.md` 找到官方仓库、固定提交、访问日期、Apache 2.0 许可证和本地改动清单

#### Scenario: Web 规则不误用
- **WHEN** 制作助手读取视觉设计 skill
- **THEN** 能从 `ADAPTATION.md` 区分视觉方向、字体、构图、层级等适用内容，以及响应式断点、CTA、表单、CSS 选择器、键盘焦点等不适用内容

### Requirement: 视觉判断必须从题材出发并先观察后建议

制作助手在方案确定、逐场设计、静帧复核和 G6 终审中调用视觉设计 skill 时，MUST 先说明作品的题材、受众和要观众理解或感受到什么，再记录实际看到的焦点、层次、留白、明度和主体关系，最后给出修改建议。MUST NOT 以“高级”“干净”“有冲击力”或替换 token、调整像素代替设计判断。

视频语境下，上游的 hero 与 first screen SHALL 映射为开场首 3–5 秒的有序帧，不能只用单张静帧；responsive/mobile SHALL 映射为作品声明画幅与手机观看尺寸，不是网页断点。

#### Scenario: 静帧复核
- **WHEN** 助手复核一张关键画面
- **THEN** 先描述题材依据、第一眼落点、主体是否只属于本题材、灰度层级、留白作用与可裁剪内容，再提出具体修改动作

#### Scenario: 开场复核
- **WHEN** 复核开场
- **THEN** 按首 3–5 秒有序帧检查主体、焦点和层次变化，不以单帧替代

### Requirement: 反默认清单是起点，不是项目否决清单

视觉设计 skill 的反默认清单 SHALL 作为审慎起点，用于发现通用的生成式默认；MUST NOT 被表述为形式否决条件。风格包、作品设计目标、用户明确要求和题材需要 MAY 使用被点名的形式，采用时记录理由。项目既有的实际表达判断、问题分级、证据有效性和独立评审隔离 SHALL 优先。

#### Scenario: 风格需要使用被点名的形式
- **WHEN** 作品风格包或题材需要渐变、发光、细线或其他上游默认清单中的形式
- **THEN** 不以形式标签直接否决，而是按实际画面、表达目标和完整窗口判断

### Requirement: 视觉设计知识不新增门禁

视觉设计 skill SHALL 是设计方法与观察词汇，MUST NOT 新增 CLI 命令、机器审美阈值、评分或审核人数。它 MUST NOT 替代项目既有的实际表达判断、问题分级、证据有效性和独立评审隔离。

#### Scenario: 评审者加载知识
- **WHEN** 独立评审者使用视觉设计 skill
- **THEN** 仍须先盲看落盘、再对照中性条件，不读取 `DESIGN.md` 或作者理由，且不因知识加载而改变评审轮次

### Requirement: 项目指导不得复述视觉设计知识

项目文档 MUST NOT 维护与 `frontend-design` 重复的通用视觉理论、七段式视觉模板或十项审美自检。项目文档 SHALL 只记录：

- 本项目的叙事、事件、导演与讲解方法；
- 视觉决策的记录位置（`DESIGN.md` 五块）与有意例外；
- 证据、问题分级、审核与完成条件。

通用视觉判断 SHALL 链接到本 skill 及其 `ADAPTATION.md`。项目文档可以说明“为什么本片选择某个例外”，但 MUST NOT 把 skill 的方法改写成另一套项目规则。

#### Scenario: 项目文档需要视觉判断
- **WHEN** 流程、阶段或评审文档需要描述构图、字体、颜色或反模板判断
- **THEN** 使用链接与项目验收条件，不复制 skill 的理论段落

#### Scenario: 记录有意例外
- **WHEN** 作品采用 skill 反默认清单中列出的形式
- **THEN** 在 `DESIGN.md` 记录理由与表达作用，不以形式标签直接否决
