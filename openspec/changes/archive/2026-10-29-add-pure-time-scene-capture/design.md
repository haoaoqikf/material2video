## Context

v8 代码场景录制页安装受控时钟，按幕内时间逐帧推进；`advanceToFrame` 只接受连续帧，内部时钟禁止倒序。`_capture` 即使只取目标附近的帧，也要从第 0 帧推进到 `max(selected)`，未选帧仍执行完整 flush。Motion、GSAP、ECharts、CSS 动画和视频播放依赖这种顺序推进，因此不能把全部场景改成任意 seek。

## Decisions

### 1. 纯模式显式 opt-in

场景在 `content.props.capture` 声明：

```json
{"mode": "pure-time", "jobs": 1, "blockFrames": 30, "verifyFrames": 4}
```

- `mode` 默认 `sequential`；`pure-time` 隐含 `timebase: "global"`。
- `jobs` 为 1–4，`blockFrames` 默认等于 fps，`verifyFrames` 为 2–4。
- `jobs/blockFrames/verifyFrames` 是运行时参数，计算片段缓存键前从 props 副本中剥离；`captureStartFrame` 只注入录制页 HTML，也不进入键。
- `mode` 与 `sceneStartFrame` 进入缓存键；pure 使用独立 contract 字符串，旧片段不复用。

### 2. 绝对 seek 与块首挂载

`capture-clock.js` 新增 `seek(ms)`：直接把受控时钟设为绝对时刻，允许倒序；现有 `setTime` 仍只允许前进。`host.tsx` 在 pure 模式暴露 `seekToSubframe(frame, subframe, subframes)`，并在初始化时用 `captureStartFrame` 设置 `elapsedSeconds`。

块首挂载是必要约束：若先挂载在 0 再跳到块首，挂载期间创建的定时器会在跳跃时集中触发，污染纯场景状态。`bootstrap()` 在 pure 模式也从 `captureStartFrame` 起算。

### 3. 直接采集、块对齐与缓存

`_capture` 的 pure 分支只遍历选中帧（或目标区间），直接 seek；不再从 0 推进。目标区间按场景内 `blockFrames` 对齐：

- `materialize` 把请求窗口向外扩到块边界，设置 `mediaStartFrame=blockStart`、`mediaDurationFrames=blockEnd-blockStart`；compositon 的 `Sequence from` + `OffthreadVideo trimAfter` 已能回放扩展窗口。
- 缓存文件名仍为 `{sceneKey}-{first}-{last}.mp4`；块对齐让预演窗口生成的块能被后续全片渲染复用。
- receipt 记录 `first/last/sha256/contract/verified/probes/minPsnr`；pure 缓存只有 `verified=true` 才可复用。

### 4. 分进程并行

`materialize` 只在 pure 且 `jobs>1` 时并行：

- 父进程构建一次 `scene.js`，计算缓存键，按块切分缺口；
- 每个未命中块由独立 Python 子进程 `python -m m2v.types.general.code_scenes.worker <job.json>` 启动自己的 Chromium，采集、编码、写 receipt；
- 父进程用有限并发调度，失败时不发布最终拼接；已成功块保留，下次可复用；
- 每次每进程只开一个页面；Windows 默认建议 1–2，代码上限 4。

最终渲染的 `--jobs` 是另一层：先 `remotion.metadata()` 校验总帧数/尺寸/帧率，再按帧区间调用现有 `render_frames(concurrency=1)` 并发渲染；每段直接解码核对帧数（脚本回报的是 composition 全片帧数，不是段帧数），最后 `concat -c copy` 并复核总帧数。音频在拼接后统一 mux。

### 5. 纯性验证

- 静态闸门：扫描作品根与所选风格包内的源码；复用 `source_policy` 的时间/随机/计时器/CSS 动效规则，并额外拒绝 `useFrame`、ECharts 动画、`new Date`、`element.animate`、`video/audio.play()`。允许 `useState/useRef/useLayoutEffect` 用于资源加载或按帧绘制；运行时检查是权威。
- 动态检查：每段选 2–4 个探针帧，先正序、再倒序截图，逐帧 PSNR ≥ 60 dB；相邻块各留一个边界见证帧跨进程比对。失败抛 `M2VError` 并指出场景与帧号，不写 receipt、不发布缓存、不回退 sequential。

### 6. 兼容与回退

- 未声明 pure 的作品走原顺序路径，配置、缓存键、预览行为不变。
- `--jobs` 默认 1，走现有 `render_session` 单进程路径；`--jobs>1` 仅 general 接受。
- `--jobs` 不进入 delivery binding；改变 jobs 仍可复用同一候选，因为内容与编码参数不变。
- 若 `concat -c copy` 失败，明确报错，不静默重编码。

## Risks

- **伪纯场景**：静态扫描无法覆盖所有有状态写法；以正序/倒序探针和边界见证帧硬失败，宁可拒绝。
- **内存**：多 Chromium 在 Windows 抬高峰值内存；默认 1、上限 4，失败清理整棵进程树。
- **拼接兼容**：每段独立编码会在接缝多一个 IDR，视觉一致但码率略高；所有段与最终文件都做帧数/尺寸/帧率验收。
- **缓存失效**：pure contract 与 `sceneStartFrame` 改变会重录；这是一次性成本，换来后段可直接定位。
