## 1. 删除旧运行时

- [x] 1.1 删除 `engine/qa.py`、`qa_inspection.py`、`rhythm_measure.py`、`subtitle_backing.py`、`design_tokens.py`，确认 `git grep` 在主项目内无残留导入
- [x] 1.2 删除 `engine/remotion/`、`render_pipeline.py`、`bundle_cache.py`、`contract_page.py`、`perf.py`，确认 `git grep` 无残留导入
- [x] 1.3 删除 `types/scene_film/explainer_prepare.py`、`explainer_render.py`、`reading_pace.py`，确认 `commands.py`/`explainer.py` 仍可导入
- [x] 1.4 删除 `core/fonts.py`、`core/example_media.py`、`core/source_policy.py`，并从 `pyproject.toml` 移除 `fonttools`；`uv sync --frozen` 与 `import m2v.cli` 通过

## 2. 收敛保留模块

- [x] 2.1 删除 `code_scenes/capture.py` 与 `worker.py`，`code_scenes/config.py` 只保留校验与录制声明，更新 `__init__.py`；`m2v validate` 相关测试通过
- [x] 2.2 `core/assets.py` 只保留 `REPOSITORY_ROOT`/`BUNDLE_DIR`；`python -c "import m2v.cli"` 通过

## 3. 测试迁移

- [x] 3.1 删除只验证被删模块内部实现的测试（`test_design_tokens`、渲染导出重复、实现指纹等），`pytest --collect-only` 无收集错误
- [x] 3.2 字体、示例媒体、代码场景采集测试改为导入 `film_runtime` 模板实现；`tests/common/test_font_*`、`tests/works/examples/test_example_media.py` 通过
- [x] 3.3 准备／渲染测试的导入与 monkeypatch 目标改为 `film_runtime`；`tests/common`、`tests/types`、`tests/standalone`、`tests/works` 默认标记集全部通过

## 4. 文档与依赖

- [x] 4.1 更新 `ARCHITECTURE.md`、`README.md`，不再声称主项目保留旧准备／渲染模块
- [x] 4.2 更新 `openspec/config.yaml` 与 `code-scene-runtime.md` 的实现位置说明；`sync_docs.py --check` 通过

## 5. 验证与提交

- [x] 5.1 运行受影响测试（common/types/standalone/works 默认标记集）与 `m2v types` 冒烟，全部通过；浏览器慢测中 `test_visual_tools` 通过，`test_capture_clock` 的 video seek 断言受本机 Chromium 取整影响
- [x] 5.2 检查暂存内容无二进制与缓存，提交实现与文档
- [ ] 5.3 规格校验与归档：`openspec validate` 通过后归档变更，提交归档结果
