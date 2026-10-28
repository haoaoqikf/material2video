## 1. 事件解析与窗口校验

- [x] 1.1 在 `src/m2v/engine/lookdev.py` 新增 `resolve_event_selectors()`：从 `prepared.props.resolvedEvents` 解析 `sceneId:eventId` 或全片唯一的事件 ID；未知、歧义、空选择器与非法偏移立即失败；验证 `tests/test_cinematic_lookdev.py` 覆盖通过。
- [x] 1.2 计算 before/at/after/hold 四阶段帧，全部按所属幕 `durationInFrames` 校验；越界时报出事件、阶段、局部帧与合法范围，不裁剪；验证覆盖前后越界用例。
- [x] 1.3 事件簇警告与同帧去重：相邻事件间隔小于 `before+after` 时返回警告；同一帧只采一次并合并标签；验证覆盖重叠窗口用例。

## 2. 预览与清单

- [x] 2.1 扩展 `preview()` 接受显式标签与附加清单；标签数量必须等于取帧数量；事件模式产物写 `outputs/lookdev/event.png`，清单写 `events` 与 `eventWarnings`。
- [x] 2.2 标签使用 ASCII 的 `scene.event.bN/at/aN/hN`，复用既有 `contact_sheet()`；验证真实复利示例得到四格接触表与绑定准备指纹的清单。

## 3. CLI 接线与互斥

- [x] 3.1 `src/m2v/cli.py` 注册 `--event`（可重复）、`--before`、`--after`、`--hold`；`src/m2v/commands.py` 原样转发；验证 `tests/test_cinematic_commands.py` 覆盖解析与转发。
- [x] 3.2 事件模式与 `--sheet`/`--motion`/`--det`/`--stills` 互斥；`--before/--after/--hold` 只能与 `--event` 一起使用；事件模式必须同时声明前两个窗口；验证互斥用例通过。

## 4. 文档与验证

- [x] 4.1 更新 `.agents/skills/material2video/references/cinematic-video.md`、`code-scene-runtime.md`、`production-workflow.md`、`storyboard-schema.md` 与 `README.md`，说明事件模式、作者声明窗口、事件簇、预览定位与「不替代 G4」。
- [x] 4.2 运行 `uv run pytest tests/test_cinematic_lookdev.py tests/test_cinematic_commands.py tests/test_vibe_night_fold_layout.py tests/test_doc_examples.py -q` 与 `PYTHONUTF8=1 uv run pytest -m "not slow" -q`；在复利示例上端到端跑一次事件模式，核对产物、清单与标签。
- [ ] 4.3 同步 `openspec/specs/modular-video-production/spec.md` 主规格，把变更移入 `openspec/changes/archive/2026-10-28-add-event-evidence-preview/` 并提交归档。
