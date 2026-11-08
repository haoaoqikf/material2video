## MODIFIED Requirements

### Requirement: 字体仓与登记表

每个作品 MUST 持有其实际使用字体的登记、许可与恢复入口，构建和渲染 MUST 只解析作品本地目标；主项目可保留参考登记但不得成为作品运行输入。示例字体二进制继续忽略，缺失或摘要不符明确失败。


每个采用字体的作品 SHALL 提供 `fonts/registry.json`，每项 SHALL 声明字体 id、文件名、来源、版本、字节数、SHA-256、许可文件路径与恢复目标；字体二进制 SHALL NOT 被 Git 跟踪，许可文本 SHALL 被跟踪。登记项 SHALL NOT 复用同一 id，摘要 SHALL 为 64 位十六进制字符串。

#### Scenario: 二进制移出版本控制

- **WHEN** 检查 Git 跟踪的字体文件
- **THEN** 没有任何 `.ttf/.otf/.woff2` 被跟踪，`fonts/registry.json` 与 `fonts/licenses/` 中的许可文本存在

#### Scenario: 摘要漂移

- **WHEN** 恢复源文件或目标副本的 SHA-256 与登记不符
- **THEN** 恢复失败并指出该字体与期望摘要，不覆盖已有文件

### Requirement: 离线恢复与校验

每个作品 MUST 持有其实际使用字体的登记、许可与恢复入口，构建和渲染 MUST 只解析作品本地目标；主项目可保留参考登记但不得成为作品运行输入。示例字体二进制继续忽略，缺失或摘要不符明确失败。


每个采用字体的作品 SHALL 提供 `fonts/fetch.py`，支持只校验、离线恢复与显式下载；默认行为 SHALL NOT 联网。缺失字体时命令 SHALL 返回非零并逐项说明该把文件放到哪里；全部就绪时 SHALL 输出可核对的来源与目标。

#### Scenario: 字体缺失

- **WHEN** 登记字体不在缓存、字体仓或原目标位置
- **THEN** `fetch.py --check` 返回非零并列出缺失项与恢复方式

#### Scenario: 离线恢复

- **WHEN** 字体已在 `M2V_FONT_CACHE` 或 `fonts/.cache/`
- **THEN** 恢复脚本校验摘要后复制到 `fonts/files` 与 targets，不访问网络

### Requirement: 字体来源可恢复

每个作品 MUST 持有其实际使用字体的登记、许可与恢复入口，构建和渲染 MUST 只解析作品本地目标；主项目可保留参考登记但不得成为作品运行输入。示例字体二进制继续忽略，缺失或摘要不符明确失败。


画面注册的字体 SHALL 由字体仓恢复，字体清单的源目录 SHALL 指向字体仓；字体缺失时缺字检查 SHALL 失败并提示恢复入口，SHALL NOT 把缺失当作"无字体可查"的通过状态。

#### Scenario: 字体仓已恢复
- **WHEN** `fonts/fetch.py` 成功完成
- **THEN** 缺字检查读取字体仓中的实际字体并给出既有覆盖结论

#### Scenario: 字体仓未恢复
- **WHEN** 字体清单指向的源文件不存在
- **THEN** 检查失败并提示运行 `uv run python fonts/fetch.py`

### Requirement: 数学字体受控恢复

每个作品 MUST 持有其实际使用字体的登记、许可与恢复入口，构建和渲染 MUST 只解析作品本地目标；主项目可保留参考登记但不得成为作品运行输入。示例字体二进制继续忽略，缺失或摘要不符明确失败。


KaTeX 实际使用的 WOFF2 字体 MUST 登记版本、摘要、字节数、许可与恢复目标，并复用现有恢复和校验机制。依赖包已安装的字体文件 MAY 作为登记候选来源；字体二进制 MUST NOT 入库，缺失或摘要失配 MUST 阻止相关公式构建/准备，不允许系统字体静默回退。

#### Scenario: 安装依赖后恢复
- **WHEN** 已安装固定版本 KaTeX 并执行字体恢复
- **THEN** 校验源字体并恢复登记目标，公式无需在线字体

### Requirement: 缺字提示可操作
字体缺失导致缺字检查、准备或 web 构建失败时，错误信息 SHALL 指出运行 作品本地字体恢复命令，SHALL NOT 静默回退到系统字体或跳过检查。

#### Scenario: 构建前字体缺失

- **WHEN** 作品实际注册的本地源字体不存在
- **THEN** 作品本地构建命令 失败并提示恢复命令

#### Scenario: 场景字体缺失

- **WHEN** 注册字体尚未恢复
- **THEN** `validate`、`prepare` 或构建明确失败并提示恢复
