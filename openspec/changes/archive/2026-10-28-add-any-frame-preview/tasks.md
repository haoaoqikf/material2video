## 1. 取点与校验（纯函数）

- [x] 1.1 在 `src/m2v/engine/lookdev.py` 新增时刻换算与取点函数：秒→帧（按作品 fps）、均匀区间取帧、非法时刻预校验（负值、越界、NaN/inf、不落在任何 `compiledScenes` 窗口内）；验证 `uv run pytest tests/test_cinematic_lookdev.py -q` 覆盖四类非法输入并给出具体时刻。
- [x] 1.2 新增三种模式互斥校验与参数解析；验证同时声明 `--sheet`/`--motion`/`--stills` 时立即失败并说明互斥。

## 2. 采集与拼图

- [x] 2.1 实现 `--sheet` 与 `--motion` 的执行路径：复用 `native_stills()` + `still_props()` + `remotion.render_still()` + `contact_sheet()`，产物写 `outputs/lookdev/`，清单更新 `outputs/lookdev.json`；验证在 `videos/general/olbers-night` 上运行 `--sheet 2 8 15` 得到一张拼图且清单新增对应字段。
- [x] 2.2 拼图加时间与帧号标注（ffmpeg `drawtext`，仅 ASCII）；按帧数选择 `columns`；验证标注可读，缺字体时退回无标注并提示。

## 3. 一致性自检

- [x] 3.1 实现 `--det`：两次独立采集同一批时刻，比较前校验尺寸一致，用 ffmpeg `psnr` 统计逐帧比较，阈值 60 dB；验证不一致时刻与实测值写入清单，尺寸不一致时明确失败。
- [x] 3.2 验证判定阈值与既有口径一致：同一帧两次采集记为一致（`inf` 或 ≥60 dB）；不改动 `remotion-renderer` 已定的阈值。

## 4. CLI 接线与文档

- [x] 4.1 `src/m2v/cli.py` 注册三个新参数并转发到 `commands.py` 的 lookdev 分支；验证 `uv run pytest tests/test_cinematic_commands.py -q` 通过，非 general 作品仍明确失败。
- [x] 4.2 更新 `README.md`、`references/cinematic-video.md`、`references/code-scene-runtime.md`、`references/production-workflow.md`，说明三种模式、互斥关系、产物位置、代价与"预览不替代 G4 证据"；验证 README 命令示例可照抄执行。

## 5. 验证与交付

- [x] 5.1 运行 `uv run pytest tests/test_cinematic_commands.py tests/test_cinematic_lookdev.py tests/test_output_cleanup.py -x` 与 `uv run pytest -m "not slow"`；需要 Node 与浏览器的用例按 `-m slow` 单独跑通。
- [x] 5.2 在真实作品上端到端确认三种模式各跑一次，产物位置、清单字段与清理行为符合规格；检查暂存范围后提交实施。
- [x] 5.3 同步 `openspec/specs/modular-video-production/spec.md` 主规格，移入 `openspec/changes/archive/2026-10-28-add-any-frame-preview/` 并提交归档。
