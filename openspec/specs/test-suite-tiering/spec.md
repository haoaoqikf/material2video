# test-suite-tiering Specification

## Purpose

为测试建立按影响范围选择、按运行成本过滤的入口：日常只验证相关单元、契约及必要媒体或浏览器节点，CI 只运行默认快层；全仓完整回归仅由用户明确要求或人工正式发布触发。共享测试保护独特行为与关键失败边界，避免重复锁定文案、配置与作品内容。

## Requirements

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
- **WHEN** 开发者运行 `uv run pytest tests/types/scene_film/test_article_media.py`
- **THEN** 该文件内的 `media` 和 `slow` 用例仍被排除

#### Scenario: 明确节点与目录混用
- **WHEN** 开发者同时选择一个慢测节点和另一个测试目录
- **THEN** 只对该节点解除默认排除，目录内其他慢测仍被排除

#### Scenario: 显式选择层级
- **WHEN** 运行 `uv run pytest tests/types/scene_film/test_article_media.py -m media`
- **THEN** 只运行该文件中匹配表达式的媒体测试

#### Scenario: 全量运行
- **WHEN** 经允许运行 `uv run pytest --full`
- **THEN** 收集并运行全部用例

### Requirement: 标记语义

- `media` MUST 表示用例需要 ffmpeg 真实编解码（媒体生成、探测、音频混流或成片检查）。
- `slow` MUST 表示用例需要 Chromium、完整渲染或长时等待。
- 纯解析、校验、指纹与 mock 驱动的用例 MUST NOT 标记为 `media` 或 `slow`。
- 单个模块多数用例需要媒体时 MAY 使用模块级标记；混合模块 MUST 只标记实际需要媒体的用例。

#### Scenario: 混合模块
- **WHEN** 同一测试模块内既有纯解析用例，也有生成真实媒体的用例
- **THEN** 只有生成真实媒体的用例带 `media` 标记，纯解析用例留在默认层

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

### Requirement: 示例内容测试边界

仓库随附示例的内容 MUST 由各自作品的制作与验收流程维护；通用测试 MUST NOT 重复断言示例的固定帧数、时长、音效数量或逐镜内容。通用测试 MAY 保留示例媒体恢复、版本控制卫生、字体与场景打包契约等跨示例的产品行为。

#### Scenario: 修改示例内容
- **WHEN** 调整某个风格示例的分镜节奏或画面内容
- **THEN** 通用测试不因该内容变化而失败；示例自身按制作与验收流程检查

### Requirement: 测试保留与重复边界

测试 MUST 优先保护可观察行为和失败边界。固定文案、标题、配置数值的副本以及已移除文件不存在的断言 MUST NOT 作为通用回归要求。删除重复测试 MUST 记录剩余覆盖；媒体编解码或真实成片只为独特行为保留最小代表，不得为共享逻辑跨类型重复生成完整成片。

#### Scenario: 删除重复成片
- **WHEN** 共享缓存和混音行为已有针对性测试
- **THEN** 通用成片只保留无声、有声代表，将并行分段验证并入其中，保留关键流、帧数与交付保护
