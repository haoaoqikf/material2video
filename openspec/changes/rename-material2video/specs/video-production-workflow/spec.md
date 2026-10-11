## MODIFIED Requirements

### Requirement: 文章作为独立视频类型
文章制作 MUST 通过 m2v 的 article-narrative 类型执行，保留 v4、字数与时长、输入审查、关键幕、全片有声及连续性门禁；这些约束 MUST 不作为其他视频类型的全局规则。

#### Scenario: 保留文章制作闭环
- **WHEN** 通过统一入口制作文章或在通用片中嵌入文章
- **THEN** 文章仍执行既有制作规则，其他场景与整片不被文章字数时长限制
