## 1. 全局时间注入

- [x] 1.1 在 `code_scenes.scene_config` 读取并校验 `content.props.capture.timebase`（`local`/`global`，默认 local）；`global` 时注入 `timeline`，未声明时配置不变。验证：`uv run pytest tests/test_code_scenes.py -q`。
- [x] 1.2 `SceneContext` 增加 `globalFrame`/`globalSeconds`，`host.tsx` 按 `sceneStartFrame + 帧号` 计算并保持子帧换算。验证：`pnpm -C web test` 与浏览器慢测。
- [x] 1.3 更新 `tests/_helpers.py` 或相关夹具，确认真实构建/采集路径仍可运行。

## 4. 文档与归档

- [x] 4.1 更新 `code-scene-runtime.md`、`explainer-design.md`、`article-media-and-sound.md`、`storyboard-schema.md`。
- [x] 4.2 运行 `uv run pytest -m "not slow"`、相关 slow 测试、`pnpm -C web test`、`sync_docs.py --check`，检查暂存并提交。
- [x] 4.3 任务全部完成后归档本变更，同步 `openspec/specs/` 并提交归档结果。

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
