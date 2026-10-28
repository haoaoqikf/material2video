## 1. 全局时间注入

- [x] 1.1 在 `code_scenes.scene_config` 读取并校验 `content.props.capture.timebase`（`local`/`global`，默认 local）；`global` 时注入 `timeline`，未声明时配置不变。验证：`uv run pytest tests/test_code_scenes.py -q`。
- [x] 1.2 `SceneContext` 增加 `globalFrame`/`globalSeconds`，`host.tsx` 按 `sceneStartFrame + 帧号` 计算并保持子帧换算。验证：`pnpm -C web test` 与浏览器慢测。
- [x] 1.3 更新 `tests/_helpers.py` 或相关夹具，确认真实构建/采集路径仍可运行。

## 2. pigeon 连续行为

- [x] 2.1 把 `birdAct(globalSeconds, chapterId)` 重写为 `act(globalSeconds)`，删除幕 ID 分支；六幕只保留镜头表、字幕与取景。验证：源码断言 + `m2v lookdev --sheet` 幕界帧。
- [x] 2.2 `storyboard.json` 移除每幕 `clock.startSeconds`，声明 `content.props.capture.timebase: "global"`。验证：`uv run m2v validate --project styles/examples/vibe-fable/pigeon`。
- [x] 2.3 更新示例 README 的时间线与“一个箱子，一台摄影机”说明。

## 3. 事件化声音语义

- [x] 3.1 各幕声明语义事件，`soundtrack.effects` 改用 `eventId`，删除硬编码 `offsetFrames`。验证：`uv run m2v prepare --project styles/examples/vibe-fable/pigeon` 后检查 `outputs/events.json`。
- [x] 3.2 新增 `SOUND.md` 声音语义表并链接到 README；如需要新变体，更新 `assets/sound-recipe.json` 并用 `m2v general sounds import` 重新生成。
- [x] 3.3 画面侧使用同一 `eventFrames`（如强调/计数），确保声画同源。

## 4. 文档与归档

- [x] 4.1 更新 `code-scene-runtime.md`、`explainer-design.md`、`article-media-and-sound.md`、`storyboard-schema.md`。
- [x] 4.2 运行 `uv run pytest -m "not slow"`、相关 slow 测试、`pnpm -C web test`、`sync_docs.py --check`，检查暂存并提交。
- [x] 4.3 任务全部完成后归档本变更，同步 `openspec/specs/` 并提交归档结果。
