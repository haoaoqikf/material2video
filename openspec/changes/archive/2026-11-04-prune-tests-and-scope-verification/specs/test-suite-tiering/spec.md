## MODIFIED Requirements

### Requirement: 分层测试入口

测试 MUST 按运行成本分层，并允许明确选择高成本用例。

- 默认执行 `uv run pytest` MUST 只收集未标记 `media` 或 `slow` 的纯单元与契约用例。
- `uv run pytest --full` MUST 收集全部选定范围的用例；使用范围受全量规则约束。
- 显式传入 `-m <表达式>` 时 MUST 完全按该表达式收集，不再应用默认排除。
- 显式指定文件或目录时 MUST 仍应用默认排除；指定 `file.py::test_name` 节点时 MUST 仅对匹配的明确节点解除默认排除，不得连带放开同次命令中的其他文件或目录。
- 未声明的标记 MUST 使收集失败（`--strict-markers`）。

#### Scenario: 日常默认运行
- **WHEN** 开发者不传任何参数运行 `uv run pytest`
- **THEN** 只运行默认快层，不启动真实媒体编解码、浏览器或真实渲染

#### Scenario: 显式指定文件
- **WHEN** 开发者运行 `uv run pytest tests/types/general/test_article_media.py`
- **THEN** 该文件内的 `media` 和 `slow` 用例仍被排除

#### Scenario: 明确节点与目录混用
- **WHEN** 开发者同时选择一个慢测节点和另一个测试目录
- **THEN** 只对该节点解除默认排除，目录内其他慢测仍被排除

#### Scenario: 显式选择层级
- **WHEN** 运行 `uv run pytest tests/types/general/test_article_media.py -m media`
- **THEN** 只运行该文件中匹配表达式的媒体测试

#### Scenario: 全量运行
- **WHEN** 经允许运行 `uv run pytest --full`
- **THEN** 收集并运行全部用例

### Requirement: CI 与交付层级

- 日常交付 MUST 只运行直接受影响的用例与必要的直接调用方测试；媒体与浏览器变更 MUST 补充相关节点，不得因此执行全仓同类别测试。
- CI 推送与拉取请求 MUST 只运行默认快层，不依赖浏览器或真实媒体编解码；正式发布验证 MUST 由人工显式触发。
- 全仓完整回归（包括 `--full`、宽泛标记或按目录分组覆盖全集）MUST 仅在用户明确要求或人工触发正式发布验证时运行。
- 跨模块改动、重构、普通提交、文档同步与 OpenSpec 归档 MUST NOT 自动触发全量回归。
- 同一代码状态下已通过的集合 MUST NOT 无理由重复执行；失败后 MUST 优先重跑失败项及必要关联测试。

#### Scenario: 局部媒体修改
- **WHEN** 修改一个媒体模块
- **THEN** 运行相关快测和媒体节点，不运行全仓 `-m "not slow"` 或全仓 `-m slow`

#### Scenario: 重构与归档
- **WHEN** 完成跨模块重构或 OpenSpec 归档，用户未要求全量且不是正式发布验证
- **THEN** 按影响范围验证，不以分组测试方式覆盖全集

#### Scenario: CI 执行
- **WHEN** 推送或提交拉取请求
- **THEN** CI 运行默认快层；只有人工选择正式发布验证才运行全量

## ADDED Requirements

### Requirement: 测试保留与重复边界

测试 MUST 优先保护可观察行为和失败边界。固定文案、标题、配置数值的副本以及已移除文件不存在的断言 MUST NOT 作为通用回归要求。删除重复测试 MUST 记录剩余覆盖；媒体编解码或真实成片只为独特行为保留最小代表，不得为共享逻辑跨类型重复生成完整成片。

#### Scenario: 删除重复成片
- **WHEN** 共享缓存和混音行为已有针对性测试
- **THEN** 通用成片只保留无声、有声代表，将并行分段验证并入其中，保留关键流、帧数与交付保护
