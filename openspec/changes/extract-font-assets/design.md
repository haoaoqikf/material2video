## Context

字体目前有三处来源：`web/src/assets/fonts/` 的全局字体、`styles/vibe-night/assets/` 的风格包字体，以及 `web/public/fonts/` 的构建副本。`web/src/assets/fonts.json` 是 web 注册清单，`sync-fonts.mjs` 在构建前复制，`contract_page.font_files()` 用同一清单做缺字检查。三个原始 TTF 被 Git 跟踪，共约 20.8 MiB。

示例媒体已经使用 `examples/*/assets/recipe.json` + `fetch.py` + 摘要校验的模式；字体沿用同一原则，但需要额外处理 web 构建、Python 检查与风格包包内路径三个消费方。

## Goals / Non-Goals

**Goals:**

- 字体二进制不再进入 Git，许可文本仍入库。
- 字体来源、版本、摘要、目标路径与子集参数集中在一个 `fonts/registry.json`。
- 一条命令离线恢复并校验；缺失时所有入口给出同一句可操作提示。
- 不改风格包"资产必须在包内"的契约，不改渲染语义。

**Non-Goals:**

- 不实现字体子集的自动重建；本轮恢复预生成子集，重建登记为后续。
- 不改共享字幕层、视频类型、制作门、审核轮次或导出门禁。
- 不把示例媒体、图片等其他二进制的规则并入本变更。

## Decisions

### 1. 独立字体仓与登记表

新建 `fonts/`，`registry.json` 每项包含：

`id`、`file`、`family`、`weight`、`usage`、`source`、`version`、`bytes`、`sha256`、`license`、`targets`、可选 `download` 与 `subset`。

`targets` 允许同一二进制落到 `fonts/files` 之外的位置（当前只有风格包），从而避免修改 style-pack 的包内路径限制。`sha256` 是恢复与后续校验的唯一依据；摘要漂移直接失败。

### 2. 离线优先的恢复脚本

`fonts/fetch.py` 只使用标准库：

- `--check`：逐项校验 `fonts/files` 与 targets，缺失或摘要不符返回非零；
- 默认：从 `M2V_FONT_CACHE`、`fonts/.cache/`、`fonts/files`、原目标位置依次找源，校验后复制；
- `--download`：仅当登记项有 `download` 时联网获取，否则明确说明需手动放入缓存；
- 任何情况下都不覆盖摘要不同的已有文件。

不把下载做成默认行为，保持"渲染与准备不取外网"的约束。`--rebuild` 不在本轮实现，登记表保留 `subset` 描述，README 写明后续能力。

### 3. Web 清单与同步

`web/src/assets/fonts.json` 继续承担"画面注册了哪些字体"的语义清单，`sourceDirFromWeb` 改为 `../fonts/files`，新增 `licenseDirFromWeb: "../fonts/licenses"`。`sync-fonts.mjs` 从字体仓复制到 `web/public/fonts/`：

- 源文件缺失 → 失败并提示 `uv run python fonts/fetch.py`；
- 复制后按 registry 摘要复核；
- 许可证从 `fonts/licenses/` 复制，仍随构建产物分发。

### 4. Python 与风格包接入

- `contract_page.font_files()` 路径随清单变化；缺失错误追加恢复提示。
- `styles.load_style()` 在包内字体缺失时提示恢复，而不是只报"文件不存在"。
- 风格包字体仍由 `fonts/fetch.py` 复制到 `styles/vibe-night/assets/`；包内 `*.ttf` 被 Git 忽略，许可文本保留。
- 构建输入指纹继续通过 `contract_page.font_files()` 包含字体；字体摘要变化会自然使准备与缓存失效。

### 5. 测试策略

- 新增字体仓测试：清单字段、摘要、目标、许可存在，`--check` 在缺失时失败。
- 字体覆盖与子集测试在字体缺失时 `skip` 并提示恢复；另设用例证明缺失时 `prepare` 明确失败，不会静默回退。
- 修改现有的"公共字体必须保留在版本控制中"断言：改为字体二进制不得被跟踪、registry 与许可必须被跟踪。

### 6. 文档与协作约定

AGENTS.md 的"公共字体及许可仍入库"改为"字体二进制不入库，由字体仓恢复；许可文本入库"。README 快速开始增加恢复命令；design-tokens、style-pack 与字体接入文档同步来源路径。

## Risks / Trade-offs

- [fresh clone 不能直接构建] → 失败信息给出恢复命令，README 与 CI 都加恢复步骤。
- [上游字体版本漂移] → 固定 version 与 sha256，拒绝漂移，不做静默替换。
- [缓存缺失时无法联网] → `--download` 仅对登记了下载地址的项生效；其余明确要求手动放入缓存。
- [风格包在字体未恢复时无法注册] → 这是"包必须完整"的预期行为；错误信息指向恢复脚本，不放宽校验。
- [示例脚本硬编码旧路径] → 迁移时一并改为字体仓路径，并纳入回归测试。

## Migration Plan

1. 建立 `fonts/` 与 registry，记录三个字体的摘要、来源与许可。
2. 把本地 TTF 移入 `fonts/files/`，用 `git rm --cached` 停止跟踪，加入忽略规则。
3. 更新 web 清单、同步脚本、Python 错误提示、示例脚本与测试。
4. 删除本地产物后执行 `fonts/fetch.py`，验证从缓存恢复且摘要一致。
5. 跑构建、字体测试、风格包构建测试与全量非 slow 回归；提交并归档。
