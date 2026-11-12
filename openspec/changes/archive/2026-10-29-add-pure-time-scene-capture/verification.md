# 验证记录

## 功能验证

- `tests/test_code_scenes.py`：pure 场景直接 seek、块缓存复用、分块并行、静态闸门拒绝 `useFrame` 均通过。
- `tests/test_capture_clock.py`：全局时间、绝对 seek、倒序与子帧、既有顺序模式全部通过。
- `tests/test_general_silent_output.py::test_parallel_render_uses_segments_and_keeps_frame_count`：30 帧真实分段渲染通过，`renderJobs=2`，帧数一致。
- `tests/test_render_segments.py`：区间切分无缺口/重叠，非法 jobs 与空片被拒绝。
- `tests/test_lookdev_native.py`、`tests/test_source_policy.py`、`tests/test_scene_events.py`、`tests/test_vibe_fable_style.py` 通过。
- `PYTHONUTF8=1 uv run pytest -m "not slow"`、`pnpm -C web test`、`pnpm -C web typecheck`、`sync_docs.py --check` 通过。

## 基准（只读副本，位于 `work/bench/`，不进入版本控制）

| 作品 | 场景 | 顺序/单进程 | pure/多进程 | 备注 |
|---|---|---|---|---|
| `earth-night-lights` | 30 秒、1800 帧/60fps、1 幕；预览第 20–30 秒 | 281 s | 243 s | 两者最终渲染均为 600 帧；pure 不再推进前 1200 帧 |
| `labor-rights-ten-events` | 40 秒、2400 帧/60fps、12 幕；整片 | 原单进程报告 1387 s（render 737 s） | `--jobs 4` 287 s（render 153 s） | 基准副本的块缓存部分来自先前的纯窗口预览，数字用于量级对照，不作为严格 A/B |
| `labor-rights-ten-events` | 10 秒窗口预览 | jobs=1：312 s | jobs=4：256 s | 窗口不同，仅作并行采集的粗略对照 |

结论：后段窗口的收益来自“不再回放前缀 + 块缓存复用”；多进程最终渲染在 2400 帧长片上把渲染阶段从约 737 秒降到约 153 秒。短示例的绝对收益受布局量测与固定渲染开销影响，不能按帧数比例线性外推。

## 已知限制

- pure 模式只适合完全由时间/属性/事件推导的场景；`useFrame`、ECharts 动画、自走媒体与计时器会被静态或动态闸门拒绝。
- `--jobs` 目前仅 `general` 支持；其他类型收到大于 1 的值会在渲染前拒绝。
- 分段拼接依赖各段编码参数一致；`concat -c copy` 失败时明确报错，不静默重编码。
- 基准作品的缓存状态会影响绝对耗时；需要严格对照时应使用全新副本并清理 `outputs/code-cache`。

> 2026-11-12 内容清理：已删除用户指定作品的专属内容；本档案仅保留其余历史范围，不代表本轮重新验证。
