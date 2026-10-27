## 1. 字体仓与登记

- [x] 1.1 创建 `fonts/registry.json`、`fonts/fetch.py`、`fonts/README.md` 与 `fonts/licenses/`；登记三个字体的 id、来源、版本、字节数、sha256、许可与 targets；验证清单可被 `fetch.py --check` 读取。
- [x] 1.2 实现 `fetch.py` 的 `--check`、离线恢复与 `--download` 分支；验证缺失时返回非零并逐项说明，摘要不符时拒绝且不覆盖已有文件。
- [x] 1.3 把三个 TTF 移入 `fonts/files/`，`git rm --cached` 停止跟踪；更新 `.gitignore`；验证 `git ls-files` 不再包含字体二进制，许可文本仍被跟踪。

## 2. 构建与运行接入

- [x] 2.1 修改 `web/src/assets/fonts.json` 与 `web/scripts/sync-fonts.mjs`：源目录改为字体仓，许可目录独立，缺失时提示恢复命令；验证 `pnpm -C web build` 在字体就绪时通过、缺失时明确失败。
- [x] 2.2 修改 `contract_page.font_files()` 与 `styles.load_style()` 的缺失错误，追加 `uv run python fonts/fetch.py` 提示；验证缺字体时错误可操作、恢复后正常。
- [x] 2.3 更新示例、证据脚本与测试中的字体路径；验证 `test_font_coverage`、`test_font_subsetting`、`test_examples_strict` 在新路径下通过或按约定跳过。

## 3. 测试与文档

- [x] 3.1 新增 `tests/test_font_registry.py`：清单字段、摘要、目标与许可；`--check` 缺失时失败；恢复后通过。
- [x] 3.2 修改 `tests/test_examples_strict.py`：字体二进制不得被跟踪，registry 与许可必须被跟踪；增加"字体缺失时 prepare 明确失败"的用例。
- [x] 3.3 更新 AGENTS.md、README、design-tokens、style-pack 与字体覆盖相关文档；验证相对链接、命令与许可说明一致。

## 4. 恢复验证与交付

- [x] 4.1 删除 `web/public/fonts/` 与风格包字体副本后执行 `fonts/fetch.py`，验证从 `fonts/files` 恢复、摘要一致、`--check` 通过；`fonts/files` 本身来自外部缓存，首次获取说明见 `fonts/README.md`。
- [x] 4.2 运行 `pnpm -C web build`、字体与风格包测试、全量非 slow 回归；验证渲染语义、共享字幕层与三个固定示例不回归。
- [x] 4.3 检查暂存范围，确认只提交字体仓、代码、测试与文档，不含字体二进制、缓存或作品产物；提交并记录 commit。
- [x] 4.4 同步 `font-assets`、`font-coverage`、`style-registry` 主规格并归档；提交归档结果。
