## Why

独立工程改造后，作品的准备、采集、渲染与技术检查都由作品自己的运行时执行；主项目里仍保留一整套同源的旧准备／渲染实现。从 `m2v.cli` 出发，这些模块已没有任何生产调用方，只会与模板副本产生漂移，并让主项目看起来仍负责渲染。现在把这些实现完整下线，测试改为直接验证模板运行时。

## What Changes

- **BREAKING**：删除主项目 `engine/` 下的旧渲染链路：`qa`、`qa_inspection`、`rhythm_measure`、`remotion/`、`render_pipeline`、`bundle_cache`、`contract_page`、`perf`、`design_tokens`、`subtitle_backing`。
- **BREAKING**：删除 `types/scene_film/` 的旧准备／渲染实现：`explainer_prepare`、`explainer_render`、`reading_pace`。
- **BREAKING**：删除 `code_scenes/capture.py` 与 `code_scenes/worker.py`，`code_scenes/config.py` 只保留分镜校验所需的入口与录制声明校验。
- **BREAKING**：删除 `core/fonts.py` 与 `core/example_media.py`；`core/assets.py` 只保留仓库根与 skill bundle 定位。
- 测试改为导入 `templates/standalone/runtime/python/film_runtime/` 下的同名实现；只验证被删主项目内部细节的测试随实现删除。
- 同步更新 `ARCHITECTURE.md`、`README.md` 与相关 Skill 参考文档中“主项目保留旧 Python 准备／渲染模块”的表述。
- 删除仅服务旧实现的运行时依赖（`fonttools`）。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

无。该变更是纯实现清理：命令、材料契约、渲染契约与作品行为不变，OpenSpec 主规格无需修改，按项目约定在变更元数据中启用 `skip_specs`。

## Impact

- 代码：`src/m2v/engine/`、`src/m2v/types/scene_film/`、`src/m2v/core/`。
- 测试：约 20 个直接验证旧实现的测试文件被删除或改为导入模板运行时。
- 依赖：主项目不再需要 `fonttools`。
- 文档：`ARCHITECTURE.md`、`README.md`、`.agents/skills/material2video/references/code-scene-runtime.md`。
- 不涉及作品目录、模板运行时、示例与对外命令。
