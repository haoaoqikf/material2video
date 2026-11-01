# test-suite-tiering Specification

## Purpose

为测试建立按运行成本分层的入口：默认只跑纯单元与契约用例，真实媒体与浏览器渲染显式运行；CI 覆盖默认层与媒体层。示例内容不再由通用测试重复断言。

## Requirements

### Requirement: 分层测试入口

测试 MUST 按运行成本分层，并允许显式覆盖默认范围。

- 默认执行 `uv run pytest` MUST 只收集未标记 `media` 或 `slow` 的纯单元与契约用例。
- `uv run pytest --full` MUST 收集全部用例。
- 显式传入 `-m <表达式>` 时 MUST 完全按该表达式收集，不再应用默认排除。
- 显式指定存在的测试文件、目录或节点路径时 MUST 按指定范围收集，不再应用默认排除。
- 未声明的标记 MUST 使收集失败（`--strict-markers`），避免拼写错误静默改变分层。

#### Scenario: 日常默认运行
- **WHEN** 开发者不传任何参数运行 `uv run pytest`
- **THEN** 只运行纯单元与契约用例，不启动 ffmpeg、浏览器或真实渲染

#### Scenario: 显式指定文件
- **WHEN** 运行 `uv run pytest tests/types/general/test_article_media.py`
- **THEN** 运行该文件内的全部用例，包括其中的 `media` 用例

#### Scenario: 显式选择层级
- **WHEN** 运行 `uv run pytest -m "not slow"`
- **THEN** 运行默认层与 `media` 层，不运行 `slow` 层

#### Scenario: 全量运行
- **WHEN** 运行 `uv run pytest --full`
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

- CI MUST 运行 `-m "not slow"`，覆盖默认层与媒体层，MUST NOT 依赖浏览器或真实渲染。
- 涉及媒体、音频或 CLI 准备链路的改动 MUST 在交付前运行默认层与 `media` 层。
- 涉及浏览器、真实渲染或长时等待的改动 MUST 运行对应 `slow` 用例；发布前或大范围重构 MUST 运行 `--full`。

#### Scenario: CI 执行
- **WHEN** 推送或提交拉取请求
- **THEN** CI 运行默认层和媒体层，超时上限内不执行浏览器与真实渲染用例

### Requirement: 示例内容测试边界

仓库风格示例的内容 MUST 由各自作品的制作与验收流程维护；通用测试 MUST NOT 重复断言示例的固定帧数、时长、音效数量或逐镜内容。通用测试 MAY 保留示例媒体恢复、版本控制卫生、字体与风格包契约等跨示例的产品行为。

#### Scenario: 修改示例内容
- **WHEN** 调整某个风格示例的分镜节奏或画面内容
- **THEN** 通用测试不因该内容变化而失败；示例自身按制作与验收流程检查
