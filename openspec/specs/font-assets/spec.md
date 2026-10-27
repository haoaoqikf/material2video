# 字体资产 Specification

## Purpose

把字体二进制从版本控制中移出，集中登记来源、摘要、许可与恢复目标，使 fresh clone、构建与渲染都能通过同一入口恢复并校验，同时保持许可文本随仓库分发。

## Requirements

### Requirement: 字体仓与登记表

仓库 SHALL 提供 `fonts/registry.json`，每项 SHALL 声明字体 id、文件名、来源、版本、字节数、SHA-256、许可文件路径与恢复目标；字体二进制 SHALL NOT 被 Git 跟踪，许可文本 SHALL 被跟踪。登记项 SHALL NOT 复用同一 id，摘要 SHALL 为 64 位十六进制字符串。

#### Scenario: 二进制移出版本控制

- **WHEN** 检查 Git 跟踪的字体文件
- **THEN** 没有任何 `.ttf/.otf/.woff2` 被跟踪，`fonts/registry.json` 与 `fonts/licenses/` 中的许可文本存在

#### Scenario: 摘要漂移

- **WHEN** 恢复源文件或目标副本的 SHA-256 与登记不符
- **THEN** 恢复失败并指出该字体与期望摘要，不覆盖已有文件

### Requirement: 离线恢复与校验

仓库 SHALL 提供 `fonts/fetch.py`，支持只校验、离线恢复与显式下载；默认行为 SHALL NOT 联网。缺失字体时命令 SHALL 返回非零并逐项说明该把文件放到哪里；全部就绪时 SHALL 输出可核对的来源与目标。

#### Scenario: 字体缺失

- **WHEN** 登记字体不在缓存、字体仓或原目标位置
- **THEN** `fetch.py --check` 返回非零并列出缺失项与恢复方式

#### Scenario: 离线恢复

- **WHEN** 字体已在 `M2V_FONT_CACHE` 或 `fonts/.cache/`
- **THEN** 恢复脚本校验摘要后复制到 `fonts/files` 与 targets，不访问网络

### Requirement: 缺字提示可操作

字体缺失导致缺字检查、风格包加载或 web 构建失败时，错误信息 SHALL 指出运行 `uv run python fonts/fetch.py`，SHALL NOT 静默回退到系统字体或跳过检查。

#### Scenario: 构建前字体缺失

- **WHEN** `web/public/fonts` 的源字体不存在
- **THEN** `pnpm -C web build` 失败并提示恢复命令

#### Scenario: 风格包字体缺失

- **WHEN** 已选风格的包内字体尚未恢复
- **THEN** `validate`、`prepare` 或 `m2v styles` 明确失败并提示恢复
