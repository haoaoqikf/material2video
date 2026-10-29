## Why

代码场景目前只能从第 0 帧顺序推进到目标帧：预览、取帧和正式采集都要重放前缀，长片后段返工成本高。最终 Remotion 渲染也默认单进程。外部参考项目按时间区间分进程渲染再无损拼接，说明对**纯时间场景**可以直接求任意帧并并行采集。本变更把这种能力做成显式 opt-in，同时保留现有有状态场景的顺序采集。

## What Changes

- 场景可在 `content.props.capture` 声明 `mode: "pure-time"`。pure 场景只能由 `elapsedSeconds/globalSeconds/props/events` 推导画面，不得使用计时器、随机源、CSS 动效、`useFrame`、ECharts 动画或自走媒体播放。
- 录制运行时新增绝对 `seek(ms)`；pure 模式支持 `startAt` / `seekToSubframe`，允许跳帧与倒序。每个采集块在挂载前注入 `captureStartFrame`，从块首时间开始，而不是先挂载在 0 再跳。
- 采集按 `blockFrames` 对齐分块；块可复用缓存，并可由独立 Python 子进程并行采集后 `ffmpeg -concat -c copy` 拼接。默认 `jobs=1`，上限 4。
- pure 场景必须通过双重验证：静态源码闸门 + 正序/倒序探针 PSNR ≥ 60 dB；相邻块边界见证帧跨进程比对。失败明确拒绝 pure 模式，不回退 sequential。
- `lookdev` 对 pure 场景直接 seek 到目标帧，`--det` 改为乱序验证；非 pure 场景保持顺序推进。
- 最终 Remotion 渲染新增可选 `--jobs N`：先校验 composition 元数据，再按帧区间分进程渲染、逐段验收、无损拼接，最后统一混音。默认 1，走现有单会话路径；目前仅 `general` 支持。
- 缓存键纳入采集实现与 pure contract；运行时 `jobs/blockFrames/verifyFrames` 不进入缓存键。

## Capabilities

### New Capabilities

无。不新增视频类型、命令或风格包；`render --jobs` 是现有命令的可选参数。

### Modified Capabilities

- `react-code-scenes`：新增 pure-time 采集契约、绝对 seek、块级缓存、分进程并行与纯性验证；默认顺序模式不变。
- `remotion-renderer`：新增可选 `--jobs` 分帧区间并行渲染，区分 Remotion `--concurrency` 与进程级 `--jobs`。
- `single-pass-delivery`：并行渲染仍是同一次全片生成，候选只在拼接与帧数验收通过后落盘。

## Impact

- 运行时：`web/src/code-scene/host.tsx`、`capture-clock.js`、`context.ts`。
- 采集：`src/m2v/types/general/code_scenes/config.py`、`capture.py`（块调度与拼接）、新增 `worker.py`（分块子进程入口）。
- 渲染：新增 `src/m2v/engine/remotion/segments.py`，接入 `src/m2v/types/general/explainer_render.py`。
- 预览：`src/m2v/engine/lookdev.py` 与中立 PSNR 模块。
- CLI：`src/m2v/cli.py`、`src/m2v/commands.py`、`src/m2v/types/general/adapter.py`；其他类型收到 `--jobs > 1` 明确拒绝。
- 未声明 `capture.mode: "pure-time"` 的作品配置、缓存键、采集路径与预览行为保持不变。
