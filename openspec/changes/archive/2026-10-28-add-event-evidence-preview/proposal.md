## Why

幕内事件已经能把画面动作、计数与音效对齐到同一帧，但取证仍要作者手填秒数。事件表知道关键变化发生在哪一帧，`lookdev` 的 `--sheet`/`--motion` 却不知道；检查点采样也只按 `sampleStep` 走，不知道事件密度。复利示例的 S1 检查点步长 15 帧，而 10 个落点事件实际最小间隔 2 帧，采样只落到其中 1 个事件帧，报告仍显示密度通过。

需要一条只读准备产物的预览入口：围绕事件取「发生前—关键帧—发生后—结果停留」，由作者声明窗口，工具负责准确取帧和标注；不改变检查点合同、不自动放行，也不新增随机访问。

## What Changes

- `m2v lookdev` 增 `--event sceneId:eventId`（可重复）、`--before N`、`--after N`、可选 `--hold N`；前后窗口用整数帧，必须显式声明，不套全片统一间隔。
- 事件从当前准备记录的 `resolvedEvents` 解析，绑定 `preparedFingerprint`；事件缺失、选择器歧义或窗口越出所属幕时在启动浏览器前失败。
- 围绕每个事件取 before、at、after、hold 四类帧；同一帧只采一次，标签合并保留来源；事件簇（相邻事件间隔小于 `before+after`）明确警告。
- 拼图标签使用 ASCII 的 `scene.event.bN/at/aN/hN`；清单记录事件的幕内帧、全片帧、各阶段偏移与标签。
- 事件模式与 `--sheet`/`--motion`/`--det`/默认静帧互斥；产物仍落 `outputs/lookdev/` 并由 `outputs/lookdev.json` 记录，不写检查点目录，不进准备指纹或缓存键。
- 事件模式是看图预览，不替代 G4 检查点证据；不在本轮增加自动检查点绑定、门禁判定或随机访问。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `modular-video-production`: 「制作与质检入口」的 `lookdev` 条款扩展为支持按幕内事件取证；原有静帧、样片、三种取点模式与「不生成全片、不成为导出门禁」的约束不变。

## Impact

影响 `src/m2v/engine/lookdev.py`（事件解析、四阶段取帧、标签与清单）、`src/m2v/cli.py` 与 `src/m2v/commands.py`（参数与转发）、`tests/test_cinematic_lookdev.py` 与 `tests/test_cinematic_commands.py`（解析、越界、事件簇、互斥与转发）、`README.md` 与制作参考文档（`cinematic-video.md`、`code-scene-runtime.md`、`production-workflow.md`）。

不修改分镜 schema、准备指纹、成片编码、审核轮次或任何门禁。事件取帧仍从所属幕第 0 帧连续推进，晚幕事件代价随帧号增长；本轮不引入随机访问。
