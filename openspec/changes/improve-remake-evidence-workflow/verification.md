# 验证与交付审查

## 验证

- `uv run pytest -p no:cacheprovider --basetemp .cache/pytest-remake-evidence tests/test_doc_examples.py tests/test_examples_strict.py tests/test_five_life_choices_example.py tests/test_output_cleanup.py`：60 passed。
- `uv run python -m py_compile tests/test_doc_examples.py`：通过。
- `uv run python .agents/skills/material2video/scripts/sync_docs.py --check`：通过。
- `openspec validate improve-remake-evidence-workflow --strict`：通过。
- 15个新增文档链接及锚点、三个分镜 JSON、`git diff --check`：通过。
- 已核对未改生产代码、场景、分镜 JSON 和既有示例行为断言。

## 审查

- 关键发现：约束核验、阶段重入、基线保留、动态证据与相对改善已连通。读取实际清理实现后，明确 general 仅保护 visual-notes 的直接文件链接，备份目录和间接索引不自动保护子文件；要求 render 前登记、之后核验。
- 逻辑影响：只改变后续制作助手的操作与报告契约；局部修复不重跑无关选案，结构重制仍验证粗样和全片。待验证是描述，不新增问题状态；delivered 仍仅是技术交付状态。
- 性能影响：未改生产代码或依赖，无新增渲染、I/O或内存开销。测试复用现有文档断言风格。
- 可维护性：重制入口集中在制作流程，动态证据集中在视觉复核，改善比较集中在独立评审；其他入口引用，沿用唯一问题表和两项完成口径。
- 剩余风险：文档测试不能保证助手执行质量或最终审美改善。本轮未复制实际基线、未制作粗样、未重渲染，也不关闭旧视频问题；须在后续明确启动重制时实际取证。
- 代码质量评分：95/100，范围为新增文档契约测试。无生产逻辑或性能风险；扣分在于文本断言只防规范遗漏，不能验证真实观看效果。
