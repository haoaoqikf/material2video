# 验证记录

## 基线（改动前，本机 Windows 11）

- `uv run pytest -m "not slow"`：1099 个用例，墙钟约 7 分钟；用例耗时合计 391 秒。
- `uv run pytest -m slow`：62 个用例，用例耗时合计 745 秒（另有无头浏览器与 Node 进程启动开销）。
- 合计 1161 个用例。

耗时最集中的非 slow 模块：`test_article_explainer` 70 秒、`test_render_session` 53 秒（其中单个 30 秒超时用例 32 秒）、`test_cinematic_storyboard` 33 秒、`test_sound_library` 29 秒。

## 改动后收集数量

验证时工作区同时存在另一并行会话的在途测试（约 17 个），下列总数包含它们；本变更自身的增量为删除 78 个、迁移 2 个。

| 命令 | 用例数 |
| --- | --- |
| `uv run pytest`（默认） | 688 |
| `uv run pytest -m media` | 355 |
| `uv run pytest -m slow` | 59 |
| `uv run pytest -m "not slow"` | 1043 |
| `uv run pytest --full` | 1102 |

默认层不再收集约 414 个媒体与 slow 用例。

## 运行结果

- 默认层：`uv run pytest`，688 个用例全部通过，墙钟 **117 秒**（改动前同机跑非 slow 约 7 分钟）。
- 触及文件：`uv run pytest --full tests/test_example_media.py tests/test_doc_examples.py tests/test_vibe_fable_style.py tests/test_vibe_night_style.py tests/test_render_session.py`，64 个用例通过。`render_session` 超时用例由约 32 秒降到约 2 秒，断言未变。
- 交付层：`uv run pytest -m "not slow"` 首次运行有 3 个文档同步失败与 1 个 `financial_render` 失败；前者因并行会话已改类型目录、README 生成区尚未同步，后者因慢速运行期间共享源码被并行改动导致准备指纹失效。并行会话同步后复跑这 4 个用例全部通过，说明不是本变更引入。
- slow 层：62 个用例全量运行时有 4 个失败（`test_general_silent_output` 3 个、`test_general_type` 1 个），原因同样是运行期间源码被并行改动。工作区稳定后单独复跑这 4 个用例全部通过。
- 新增的 `tests/test_example_hygiene.py`（版本控制卫生）单跑通过。

## 结论

分层、默认排除与显式覆盖均按预期工作；本变更触及的测试与默认层全部通过。并行会话造成的瞬时失败已复跑排除。
