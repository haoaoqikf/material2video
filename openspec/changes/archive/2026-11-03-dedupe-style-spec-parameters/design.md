## Context

三个参数重的风格规格与 GUIDE 重复维护同一组色值、字号、分区与组件清单。GUIDE 是安装后实际阅读和修改的入口，`tokens.json` 是运行时取值来源；规格应只回答“必须满足什么”，不复制参数表。

## 决策

1. **参数权威**：`tokens.json` 管取值，`GUIDE.md` 管用法与组件参数；规格只保留语义、确定性、只读性、不自动换肤和可验证场景。
2. **保留可测试阈值**：`dark-proof` 的硬切次数、8/16 帧转场、8% 推近等条件仍留在规格与场景中，因为它们直接决定验收；只删除重复的色值与组件清单。
3. **其余三个风格不改**：`doc-archive`、`count-ledger`、`deep-journey` 的规格以示例和内容边界为主，参数重复较少，本轮不动。
4. **不复制 GUIDE 正文**：规格中的引用只指向 GUIDE 的章节与小节，不复制表格。

## 风险与边界

- 规格删除具体色值后，读者需要打开 GUIDE 才能核对取值；这是渐进披露的预期结果，避免三处漂移。
- 不改变组件公开名称、props、确定性或验收条件。
- 不处理 `styles/README.md` 的版本矩阵；它由 `style.json` 与测试守护。

## 验证

1. `openspec validate dedupe-style-spec-parameters --strict` 通过。
2. 归档后 `openspec validate --specs --strict` 通过。
3. `uv run m2v styles --json` 仍返回六个包，版本与指纹不变。
4. `uv run pytest -q` 默认层通过。
5. 三个风格示例的 `validate` 仍通过（素材已恢复时）。
