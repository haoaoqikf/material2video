## ADDED Requirements

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
