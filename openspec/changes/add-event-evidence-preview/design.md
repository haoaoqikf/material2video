## Context

`prepare` 已把幕内事件解析为 `props.resolvedEvents`（含 `sceneId/id/frame/globalFrame`）并输出 `outputs/events.json`；场景通过 `createSceneEvents` 查询，音效可通过 `eventId` 定位。`lookdev` 已有 `--sheet`、`--motion`、`--det` 三种取点模式，底层 `native_stills()` 只从所属幕第 0 帧连续推进，在选定帧截图。运行时不支持随机访问。

取证现状是「事件表知道关键帧，作者仍要手换算秒数」。复利 S1 检查点 `sampleStep=15`、`minEventFrames=15`，但窗口内 10 个落点事件的实际最小间隔是 2 帧；`sample_frames()` 只按步长取帧，报告不会发现这个差距。

## Goals / Non-Goals

目标：让作者用事件 ID 而不是手填时刻取到「发生前—关键帧—发生后—结果停留」的证据；让工具准确解析、标注并校验窗口；保持预览工具属性。

非目标：不新增顶层 CLI 命令；不自动把检查点窗口绑定到事件；不改变 G4 采样、审核轮次或门禁；不实现随机访问；不新增事件全局表或跨幕事件依赖。

## Decisions

- **扩展 `lookdev` 而不是新建 `event` 命令**：`lookdev` 已是制作与质检的看图入口，新建命令会形成第二个权威来源，并重复 general 类型守卫与分发。事件模式与既有三种取点模式互斥。
- **从准备产物解析，不重新算时间**：使用 `prepared['props']['resolvedEvents']`；缺失时明确失败并提示重新 prepare。`preparedFingerprint` 写入清单，事件移动后旧清单自然失效。
- **选择器用 `sceneId:eventId`，唯一时才允许省略场景**：事件 ID 幕内唯一、跨幕可重名；歧义时列出出现过的幕并要求加前缀，不猜测。
- **偏移用帧，不用秒**：事件本身就是整数帧；`--before/--after` 必须显式声明，`--hold` 可选。避免把同一组间隔套到所有事件。
- **四阶段取帧**：`before = frame - before`、`at = frame`、`after = frame + after`、`hold = frame + after + hold`。`hold` 为 0 时不加停留帧；四阶段全部位于所属幕内，越界立即失败，不静默裁剪。
- **事件簇不隐藏**：同一幕选中的事件按帧排序，相邻间隔小于 `before+after` 时给出警告；同一帧被多个阶段命中时只采一次，标签按来源合并。
- **标签用 ASCII 的 `scene.event.bN/at/aN/hN`**：沿用 `contact_sheet()` 的 `drawtext` 约束，避免中文字体缺失导致整条拼图失败；完整信息在清单里。
- **预览不是证据**：产物只落 `outputs/lookdev/` 与 `outputs/lookdev.json`；不写 `outputs/production/checkpoints/`，不进准备指纹或缓存键，不关闭任何独立评审项。
- **不做自动检查点绑定**：检查点窗口是设计合同的一部分，自动跟随事件会改变验收语义；本轮只提供准确取帧，作者可据此写窗口。事件密度诊断留作后续独立变更。

## Risks / Trade-offs

- **事件簇窗口重叠**：单事件窗口会覆盖相邻事件；工具只警告，不自动扩大窗口。作者应一次查看整个簇。
- **标签较长**：`scene.event.bN` 在 960 宽拼图格中字号较小；完整信息以清单为准。
- **晚幕事件仍慢**：运行时只顺序推进，事件越靠后代价越高；本轮不改变采集模型。
- **事件表缺失**：旧准备记录没有 `resolvedEvents` 时明确失败，不退回手填时刻。
- **误读为正式证据**：文档与帮助文本必须明确「预览不替代 G4」，清单只记录预览来源。

## Migration Plan

纯新增参数，既有调用不受影响；旧准备记录没有事件表时只在事件模式失败，其他模式保持原行为。完成后同步 `modular-video-production` 主规格并归档。
