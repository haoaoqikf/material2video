## Why

三个字体文件约 20.8 MiB 以二进制形式进入 Git，仓库体积与 diff 噪音都偏大；字体的来源、子集参数、摘要与许可分散在 `web/`、`styles/` 和文档中，恢复与校验没有统一入口。示例媒体已经采用"配方 + 恢复 + 摘要校验"的模式，字体应当使用同一原则单独管理。

## What Changes

- 新建仓库根 `fonts/`：`registry.json`（来源、版本、摘要、目标、许可）、`fetch.py`（离线恢复与校验）、`licenses/`、`README.md`。
- 三个字体二进制移出 Git，由 `fonts/fetch.py` 恢复；`fonts/files/`、`fonts/.cache/`、web 与风格包内的字体副本加入忽略规则。
- `web/src/assets/fonts.json` 的源目录改为字体仓；`sync-fonts.mjs` 从字体仓复制并校验，缺失时明确失败并提示恢复命令。
- Python 字体检查、示例脚本与测试改用字体仓路径；缺失时给出可操作提示，不静默回退。
- 更新 AGENTS.md、README、字体与风格接入文档；新增字体仓规格，修改字体覆盖与风格注册规格。
- 不改变渲染语义、字幕层、视频类型、制作门或审核职责。

## Capabilities

### New Capabilities

- `font-assets`：字体二进制不入库，由独立字体仓按登记来源、摘要与许可恢复和校验。

### Modified Capabilities

- `font-coverage`：字体来源改由字体仓提供；缺失时明确失败并指向恢复入口。
- `style-registry`：风格包内字体缺失时提示恢复，不把它当作已就绪资产。

## Impact

- 仓库不再跟踪三个 TTF，预计减少约 20.8 MiB。
- 影响 `web/src/assets/fonts.json`、`web/scripts/sync-fonts.mjs`、`src/m2v/engine/contract_page.py`、`src/m2v/core/styles.py`、示例与证据脚本、字体相关测试与文档。
- 首次使用需执行 `uv run python fonts/fetch.py`；CI 需在构建前恢复或使用缓存。
- 许可文本仍入库，OFL 随字体分发要求不变。
