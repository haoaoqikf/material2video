# 验证记录：风格示例还原度

- 变更：`add-style-example-fidelity`
- 日期：2026-10-28
- 保留范围：共享相机原语与通用回归。

## 一、技术验证

| 项 | 命令 | 结果 |
|---|---|---|
| 相机原语单测 | `pnpm -C web test` | 8 文件 / 126 项通过，含新增 `camera.test.ts` 12 项 |
| 绘制层确定性闸门 | `uv run pytest tests/test_canvas_painter.py` | 通过（`camera.ts` 自动进入实现指纹与源码扫描） |
| 风格包契约 | `uv run pytest tests/test_vibe_night_style.py tests/test_vibe_fable_style.py` | 通过 |

已知的既有失败（与本次改动无关，在本变更前即存在，已在干净工作区复核）：

- `tests/test_lookdev_native.py::test_native_crossfade_and_subtitle_composite`：
  `lookdev.native_stills` 读 `prepared["fps"]`，而该测试的 `prepared` 未提供 `fps`。
- `tests/test_code_scenes.py::test_recorded_clip_has_no_audio_stream` 偶发
  `PermissionError`（Windows 临时目录竞争），单独运行通过。
- 全量 `uv run pytest` 在本机默认编码下于收集阶段抛出 `UnicodeDecodeError`，
  使用 `PYTHONUTF8=1` 可绕过；单独运行各文件均通过。

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
